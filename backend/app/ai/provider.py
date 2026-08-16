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
        model = TASK_MODEL_MAP.get(request.task, ("openai", settings.DEFAULT_MODEL))[1]
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
        model = "claude-sonnet-4-20250514"
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
                "Not configured: no AI provider API key is set. "
                "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable real AI analysis."
                if request.json_mode
                else '{"error": "not_configured", "message": "No AI provider API key is set. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."}'
            ),
            provider=self.name,
            model="mock",
            latency_ms=0,
        )


_PROVIDERS: dict[str, BaseLLMProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "mock": MockLLMProvider(),
}


class ModelRouter:
    """Routes a task type to the best available provider."""

    def resolve(self, task: str) -> BaseLLMProvider:
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
        return await provider.complete(request)


router = ModelRouter()


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate an embedding vector, or None when unconfigured."""
    if not settings.OPENAI_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": settings.DEFAULT_EMBEDDING_MODEL, "input": text[:8000]},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
