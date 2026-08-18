"""LLM provider abstraction with model routing.

Providers: OpenAI, Anthropic, Google. A mock provider is used when no keys
are configured so every feature still works end-to-end (clearly labelled).
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

TASK_MODEL_MAP = {
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
    def is_configured(self) -> bool: ...


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


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def is_configured(self) -> bool:
        return bool(settings.OLLAMA_BASE_URL)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or settings.OLLAMA_MODEL or "llama3"
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
        except Exception as e:
            # Return structured error response that ModelRouter recognizes for fallback
            return LLMResponse(
                content=f'{{"error": "ollama_unavailable", "message": "Ollama service unreachable: {str(e)}"}}' if request.json_mode else f"Ollama service error: {str(e)}",
                provider=self.name,
                model=model,
                latency_ms=int((time.monotonic() - start) * 1000),
            )


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
                "Not configured: no AI provider API key or local Ollama is set. "
                "Run Ollama locally at http://localhost:11434 or set OPENAI_API_KEY / ANTHROPIC_API_KEY."
                if request.json_mode
                else '{"error": "not_configured", "message": "Run Ollama locally or configure API keys."}'
            ),
            provider=self.name,
            model="mock",
            latency_ms=0,
        )


_PROVIDERS: dict[str, BaseLLMProvider] = {
    "ollama": OllamaProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "mock": MockLLMProvider(),
}


class ModelRouter:
    """Routes a task type to the best available provider with Ollama local-first priority."""

    def resolve(self, task: str) -> BaseLLMProvider:
        # Check Ollama first if configured
        ollama = _PROVIDERS.get("ollama")
        if ollama and ollama.is_configured():
            return ollama

        preferred, _ = TASK_MODEL_MAP.get(task, ("openai", settings.DEFAULT_MODEL))
        provider = _PROVIDERS.get(preferred)
        if provider and provider.is_configured():
            return provider
        # Fall back to any configured provider, then mock
        for p in _PROVIDERS.values():
            if p.is_configured() and p.name != "mock":
                return p
        return _PROVIDERS["mock"]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        provider = self.resolve(request.task)
        resp = await provider.complete(request)

        # If Ollama was called but returned an error/unreachable, gracefully fall back to cloud providers
        if provider.name == "ollama" and ("ollama_unavailable" in resp.content or "Ollama service error" in resp.content):
            preferred, _ = TASK_MODEL_MAP.get(request.task, ("openai", settings.DEFAULT_MODEL))
            fallback_provider = _PROVIDERS.get(preferred)
            if fallback_provider and fallback_provider.is_configured() and fallback_provider.name != "ollama":
                try:
                    return await fallback_provider.complete(request)
                except Exception:
                    pass
            for p in _PROVIDERS.values():
                if p.is_configured() and p.name not in ("mock", "ollama"):
                    try:
                        return await p.complete(request)
                    except Exception:
                        pass
        return resp


router = ModelRouter()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate an embedding vector using OpenAI or local Ollama, or None when unconfigured."""
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
