"""LLM provider abstraction with model routing.

Providers: OpenAI, Anthropic, Ollama (local). A mock provider is used when no keys
are configured so every feature still works end-to-end (clearly labelled).
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from app.config import get_settings

settings = get_settings()

# Task to model mapping
TASK_MODEL_MAP = {
    "extraction": ("ollama", "llama3.1:8b"),
    "classification": ("ollama", "llama3.1:8b"),
    "reasoning": ("ollama", "llama3.1:70b"),
    "research": ("ollama", "llama3.1:70b"),
    "translation": ("ollama", "llama3.1:8b"),
    "drafting": ("ollama", "llama3.1:70b"),
    "summarization": ("ollama", "llama3.1:8b"),
    "chat": ("ollama", "llama3.1:70b"),
}

# Fallback cloud models
CLOUD_FALLBACK_MAP = {
    "extraction": ("openai", "gpt-4o-mini"),
    "classification": ("openai", "gpt-4o-mini"),
    "reasoning": ("anthropic", "claude-sonnet-4-20250514"),
    "research": ("anthropic", "claude-sonnet-4-20250514"),
    "translation": ("openai", "gpt-4o-mini"),
    "drafting": ("anthropic", "claude-sonnet-4-20250514"),
    "summarization": ("openai", "gpt-4o-mini"),
    "chat": ("anthropic", "claude-sonnet-4-20250514"),
}


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class LLMRequest:
    system: str
    prompt: str
    task: str = "reasoning"
    model: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.2
    json_mode: bool = False


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    async def list_models(self) -> list[str]:
        """List available models. Override in subclasses."""
        return []


class GroqProvider(BaseLLMProvider):
    name = "groq"
    BASE_URL = settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY or settings.STT_API_KEY)

    def _get_api_key(self) -> str:
        return settings.GROQ_API_KEY or settings.STT_API_KEY or ""

    async def list_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "llama-guard-3-8b",
        ]

    def _resolve_model(self, request: LLMRequest) -> str:
        if request.model:
            m = request.model.lower()
            if "70b" in m or "llama-3.3" in m or "versatile" in m:
                return "llama-3.3-70b-versatile"
            if "8b" in m or "instant" in m:
                return "llama-3.1-8b-instant"
            if "mixtral" in m:
                return "mixtral-8x7b-32768"
            return request.model

        if request.task in ("extraction", "classification", "summarization", "translation"):
            return "llama-3.1-8b-instant"
        return settings.GROQ_MODEL or "llama-3.3-70b-versatile"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = self._resolve_model(request)
        start = time.monotonic()
        base_url = (settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        usage = data.get("usage", {})
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            estimated_cost_usd=0.0,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        model = self._resolve_model(request)
        base_url = (settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue


class NvidiaProvider(BaseLLMProvider):
    name = "nvidia"
    BASE_URL = settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1"

    def is_configured(self) -> bool:
        return bool(settings.NVIDIA_API_KEY)

    async def list_models(self) -> list[str]:
        return [
            "meta/llama-3.3-70b-instruct",
            "deepseek-ai/deepseek-r1",
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mixtral-8x22b-instruct-v0.1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model
        if not model:
            if request.task in ("reasoning", "research"):
                model = "deepseek-ai/deepseek-r1"
            else:
                model = settings.NVIDIA_MODEL or "meta/llama-3.3-70b-instruct"

        start = time.monotonic()
        base_url = (settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        usage = data.get("usage", {})
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            estimated_cost_usd=0.0,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        model = request.model
        if not model:
            if request.task in ("reasoning", "research"):
                model = "deepseek-ai/deepseek-r1"
            else:
                model = settings.NVIDIA_MODEL or "meta/llama-3.3-70b-instruct"

        base_url = (settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1").rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue


class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    BASE_URL = "https://api.openai.com/v1"

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or TASK_MODEL_MAP.get(request.task, ("openai", settings.DEFAULT_MODEL))[1]
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": request.system},
                        {"role": "user", "content": request.prompt},
                    ],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    **({"response_format": {"type": "json_object"}} if request.json_mode else {}),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage", {})
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider=self.name,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        model = request.model or TASK_MODEL_MAP.get(request.task, ("openai", settings.DEFAULT_MODEL))[1]
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": request.system},
                        {"role": "user", "content": request.prompt},
                    ],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True,
                    **({"response_format": {"type": "json_object"}} if request.json_mode else {}),
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"
    BASE_URL = "https://api.anthropic.com/v1"

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or "claude-sonnet-4-20250514"
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.BASE_URL}/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "system": request.system,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage", {})
        return LLMResponse(
            content="".join(block.get("text", "") for block in data.get("content", [])),
            provider=self.name,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        model = request.model or "claude-sonnet-4-20250514"
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "system": request.system,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                            event_type = data.get("type", "")
                            if event_type == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def is_configured(self) -> bool:
        return bool(settings.OLLAMA_BASE_URL)

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        if not self.is_configured():
            return []
        base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def _check_model_available(self, model: str) -> bool:
        """Check if a model is available locally."""
        models = await self.list_models()
        return model in models or any(m.startswith(model.split(":")[0]) for m in models)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Use task-specific model if no model specified
        if not request.model:
            _, task_model = TASK_MODEL_MAP.get(request.task, ("ollama", "llama3.1:8b"))
            model = task_model
        else:
            model = request.model

        # Verify model is available, fallback to default if not
        if not await self._check_model_available(model):
            # Try to find a suitable fallback
            available = await self.list_models()
            if available:
                # Prefer larger models for reasoning/research, smaller for extraction
                if request.task in ("reasoning", "research", "drafting", "chat"):
                    model = next((m for m in available if "70b" in m or "72b" in m), available[0])
                else:
                    model = next((m for m in available if "8b" in m or "7b" in m), available[0])
            else:
                model = "llama3.1:8b"

        start = time.monotonic()
        base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": request.system},
                            {"role": "user", "content": request.prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "num_ctx": 32768,  # 32k context window
                        },
                        **({"format": "json"} if request.json_mode else {}),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            content = data.get("message", {}).get("content", "")
            return LLMResponse(
                content=content,
                provider=self.name,
                model=model,
                latency_ms=int((time.monotonic() - start) * 1000),
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                estimated_cost_usd=0.0,
            )
        except httpx.ConnectError as e:
            return LLMResponse(
                content=f'{{"error": "ollama_unavailable", "message": "Cannot connect to Ollama at {base_url}. Is Ollama running?"}}' if request.json_mode else f"Cannot connect to Ollama at {base_url}. Is Ollama running?",
                provider=self.name,
                model=model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        except httpx.TimeoutException as e:
            return LLMResponse(
                content=f'{{"error": "ollama_timeout", "message": "Ollama request timed out after 180s"}}' if request.json_mode else "Ollama request timed out. Try a smaller model or simpler query.",
                provider=self.name,
                model=model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as e:
            # Return structured error response that ModelRouter recognizes for fallback
            return LLMResponse(
                content=f'{{"error": "ollama_unavailable", "message": "Ollama service error: {str(e)}"}}' if request.json_mode else f"Ollama service error: {str(e)}",
                provider=self.name,
                model=model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        if not request.model:
            _, task_model = TASK_MODEL_MAP.get(request.task, ("ollama", "llama3.1:8b"))
            model = task_model
        else:
            model = request.model

        base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": request.system},
                        {"role": "user", "content": request.prompt},
                    ],
                    "stream": True,
                    "options": {
                        "temperature": request.temperature,
                        "num_ctx": 32768,
                    },
                    **({"format": "json"} if request.json_mode else {}),
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue


class MockLLMProvider(BaseLLMProvider):
    """Deterministic fallback used when no real provider keys are configured.

    Output is clearly labelled as not-configured rather than faking AI results.
    """

    name = "mock"

    def is_configured(self) -> bool:
        return True

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content=(
                '{"error": "not_configured", "message": "Run Ollama locally or configure API keys."}'
                if request.json_mode
                else (
                    "Not configured: no AI provider API key or local Ollama is set. "
                    "Run Ollama locally at http://localhost:11434 or set OPENAI_API_KEY / ANTHROPIC_API_KEY."
                )
            ),
            provider=self.name,
            model="mock",
            latency_ms=0,
        )

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        if request.json_mode:
            text = '{"status": "ok", "message": "Jurisiva AI mock response (run Ollama locally or configure API keys)."}'
        else:
            text = f"Jurisiva AI Mock Legal Reasoning: Analysis for {request.task} task grounded in Indian law."
        for word in text.split(" "):
            yield word + " "
            await asyncio.sleep(0.005)


_PROVIDERS: dict[str, BaseLLMProvider] = {
    "groq": GroqProvider(),
    "nvidia": NvidiaProvider(),
    "ollama": OllamaProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "mock": MockLLMProvider(),
}


class ModelRouter:
    """Routes LLM requests across Groq, NVIDIA NIM, Ollama, OpenAI, Anthropic, and hermetic Mock."""

    def resolve(self, task: str, model_preference: Optional[str] = None) -> BaseLLMProvider:
        # 1. Explicit model preference matching
        if model_preference:
            pref = model_preference.lower()
            if any(k in pref for k in ("groq", "llama-3.3", "versatile", "instant")):
                groq = _PROVIDERS.get("groq")
                if groq and groq.is_configured():
                    return groq
            if any(k in pref for k in ("nvidia", "nemotron", "deepseek-r1")):
                nvidia = _PROVIDERS.get("nvidia")
                if nvidia and nvidia.is_configured():
                    return nvidia
            if any(k in pref for k in ("claude", "anthropic", "sonnet")):
                anthropic = _PROVIDERS.get("anthropic")
                if anthropic and anthropic.is_configured():
                    return anthropic
            if any(k in pref for k in ("gpt", "openai", "o1", "o3")):
                openai = _PROVIDERS.get("openai")
                if openai and openai.is_configured():
                    return openai
            if any(k in pref for k in ("ollama", "local", "llama3.1", "qwen")):
                ollama = _PROVIDERS.get("ollama")
                if ollama and ollama.is_configured():
                    return ollama

        # 2. Priority Hierarchy: Groq (sub-600ms latency) -> NVIDIA NIM -> Ollama -> Cloud -> Mock
        groq = _PROVIDERS.get("groq")
        if groq and groq.is_configured():
            return groq

        nvidia = _PROVIDERS.get("nvidia")
        if nvidia and nvidia.is_configured():
            return nvidia

        ollama = _PROVIDERS.get("ollama")
        if ollama and ollama.is_configured():
            return ollama

        # Cloud standard fallback
        preferred, _ = TASK_MODEL_MAP.get(task, ("openai", settings.DEFAULT_MODEL))
        provider = _PROVIDERS.get(preferred)
        if provider and provider.is_configured():
            return provider

        for p in _PROVIDERS.values():
            if p.is_configured() and p.name != "mock":
                return p

        return _PROVIDERS["mock"]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        provider = self.resolve(request.task, request.model)
        try:
            resp = await provider.complete(request)
        except Exception as err:
            resp = LLMResponse(content=f"error: {err}", provider=provider.name, model="error", latency_ms=0)

        # If primary provider returned an error/unreachable, gracefully fall back
        if ("unavailable" in resp.content or "error" in resp.content or "timeout" in resp.content):
            # Try any other configured provider
            for p in _PROVIDERS.values():
                if p.is_configured() and p.name != provider.name and p.name != "mock":
                    try:
                        return await p.complete(request)
                    except Exception:
                        pass
        return resp

    async def stream_complete(self, request: LLMRequest) -> AsyncIterator[str]:
        provider = self.resolve(request.task, request.model)
        try:
            async for token in provider.stream_complete(request):
                yield token
            return
        except Exception:
            pass

        # Fallback to secondary configured providers
        for p in _PROVIDERS.values():
            if p.is_configured() and p.name != provider.name and p.name != "mock":
                try:
                    async for token in p.stream_complete(request):
                        yield token
                    return
                except Exception:
                    pass

        # Final fallback: Mock
        mock = _PROVIDERS["mock"]
        async for token in mock.stream_complete(request):
            yield token


router = ModelRouter()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate an embedding vector using NVIDIA NIM, OpenAI, or local Ollama, or None when unconfigured."""
    if settings.NVIDIA_API_KEY:
        try:
            base_url = (settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{base_url}/embeddings",
                    headers={"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"},
                    json={"model": "nvidia/nv-embedqa-e5-v5", "input": text[:8000], "input_type": "query"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embs = data.get("data")
                    if embs and len(embs) > 0:
                        return embs[0].get("embedding")
        except Exception:
            pass

    if settings.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"model": settings.DEFAULT_EMBEDDING_MODEL, "input": text[:8000]},
                )
                resp.raise_for_status()
                return resp.json()["data"][0]["embedding"]
        except Exception:
            pass

    if settings.OLLAMA_BASE_URL:
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        model = settings.OLLAMA_EMBEDDING_MODEL or "nomic-embed-text"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # 1. Try /api/embed (Ollama 0.1.30+)
                resp = await client.post(
                    f"{base_url}/api/embed",
                    json={"model": model, "input": text[:8000]},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embs = data.get("embeddings")
                    if embs and len(embs) > 0:
                        return embs[0]
        except Exception:
            pass

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # 2. Try legacy /api/embeddings
                resp2 = await client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": model, "prompt": text[:8000]},
                )
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    emb = data2.get("embedding")
                    if emb:
                        return emb
        except Exception:
            pass

    return None
