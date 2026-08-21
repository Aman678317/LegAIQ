"""Hermetic Unit Tests for GroqProvider and AI Gateway Routing (Milestone 1).

Verifies:
- GroqProvider configuration detection and model resolution
- GroqProvider.complete() with mocked OpenAI-compatible REST completions
- GroqProvider.stream_complete() with mocked SSE token stream
- ModelRouter routing hierarchy and model preference matching
- Graceful rate-limit/error fallback across providers
- GET /api/v1/ai/providers endpoint exposing Groq status
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.ai.provider import (
    GroqProvider,
    LLMRequest,
    LLMResponse,
    ModelRouter,
    _PROVIDERS,
)
from app.config import get_settings

settings = get_settings()
API = "/api/v1"


class TestGroqProviderConfiguration:
    """Test Groq provider configuration detection and model listing."""

    def test_groq_provider_is_configured_with_groq_key(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key_12345")
        monkeypatch.setattr(settings, "STT_API_KEY", "")
        provider = GroqProvider()
        assert provider.is_configured() is True
        assert provider._get_api_key() == "gsk_test_key_12345"

    def test_groq_provider_is_configured_with_stt_fallback(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        monkeypatch.setattr(settings, "STT_API_KEY", "gsk_stt_key_67890")
        provider = GroqProvider()
        assert provider.is_configured() is True
        assert provider._get_api_key() == "gsk_stt_key_67890"

    def test_groq_provider_unconfigured(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        monkeypatch.setattr(settings, "STT_API_KEY", "")
        provider = GroqProvider()
        assert provider.is_configured() is False
        assert provider._get_api_key() == ""

    @pytest.mark.asyncio
    async def test_groq_provider_list_models(self):
        provider = GroqProvider()
        models = await provider.list_models()
        assert "llama-3.3-70b-versatile" in models
        assert "llama-3.1-8b-instant" in models
        assert "mixtral-8x7b-32768" in models
        assert "llama-guard-3-8b" in models

    def test_groq_provider_resolve_model(self):
        provider = GroqProvider()

        # Explicit model name resolutions
        req_70b = LLMRequest(system="", prompt="", model="llama-3.3-70b-versatile")
        assert provider._resolve_model(req_70b) == "llama-3.3-70b-versatile"

        req_8b = LLMRequest(system="", prompt="", model="llama-3.1-8b-instant")
        assert provider._resolve_model(req_8b) == "llama-3.1-8b-instant"

        req_mixtral = LLMRequest(system="", prompt="", model="mixtral-8x7b-32768")
        assert provider._resolve_model(req_mixtral) == "mixtral-8x7b-32768"

        # Task-based resolutions when model not specified
        req_extract = LLMRequest(system="", prompt="", task="extraction")
        assert provider._resolve_model(req_extract) == "llama-3.1-8b-instant"

        req_reason = LLMRequest(system="", prompt="", task="reasoning")
        assert provider._resolve_model(req_reason) == "llama-3.3-70b-versatile"


class TestGroqProviderExecution:
    """Hermetic tests for GroqProvider.complete() and stream_complete()."""

    @pytest.mark.asyncio
    async def test_groq_provider_complete_success(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_mock")
        provider = GroqProvider()

        mock_payload = {
            "choices": [
                {
                    "message": {
                        "content": "Jurisiva AI Analysis: Section 54 of Transfer of Property Act requires registered conveyance."
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 45,
            },
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            req = LLMRequest(
                system="You are an Indian legal assistant.",
                prompt="Explain Section 54 TP Act.",
                task="reasoning",
                model="llama-3.3-70b-versatile",
            )
            resp = await provider.complete(req)

            assert isinstance(resp, LLMResponse)
            assert resp.provider == "groq"
            assert resp.model == "llama-3.3-70b-versatile"
            assert "Section 54" in resp.content
            assert resp.prompt_tokens == 120
            assert resp.completion_tokens == 45
            assert resp.latency_ms >= 0

            # Verify request headers and URL
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0].endswith("/chat/completions")
            assert "Bearer gsk_test_mock" in call_args[1]["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_groq_provider_stream_complete_tokens(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_mock")
        provider = GroqProvider()

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Under "}}]}',
            'data: {"choices": [{"delta": {"content": "Section 63 "}}]}',
            'data: {"choices": [{"delta": {"content": "of BSA 2023."}}]}',
            'data: [DONE]',
        ]

        class MockStreamResponse:
            def raise_for_status(self):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStreamResponse()):
            req = LLMRequest(
                system="You are an Indian legal assistant.",
                prompt="What is BSA 63?",
                task="chat",
            )
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)

            assert tokens == ["Under ", "Section 63 ", "of BSA 2023."]


class TestModelRouterGroqIntegration:
    """Test ModelRouter dynamic routing with Groq provider."""

    def test_model_router_resolves_explicit_groq_preference(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
        router = ModelRouter()
        
        provider = router.resolve("chat", model_preference="llama-3.3-70b-versatile")
        assert provider.name == "groq"

        provider_groq = router.resolve("reasoning", model_preference="groq")
        assert provider_groq.name == "groq"

    def test_model_router_prioritizes_groq_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
        router = ModelRouter()

        provider = router.resolve("reasoning")
        assert provider.name == "groq"

    @pytest.mark.asyncio
    async def test_model_router_fallback_when_groq_fails(self, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
        monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
        router = ModelRouter()

        # Simulate Groq provider raising exception
        with patch.object(GroqProvider, "complete", side_effect=Exception("Rate limit 429")):
            req = LLMRequest(system="", prompt="Test query", task="reasoning")
            resp = await router.complete(req)

            assert isinstance(resp, LLMResponse)
            # Falls back cleanly to Mock without unhandled crash
            assert resp.provider in ("mock", "ollama")


class TestAIProvidersEndpointGroq:
    """Test /api/v1/ai/providers endpoint reflects Groq status."""

    def test_providers_endpoint_reports_groq_configured(self, api_client, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_live_test_key")
        res = api_client.get(f"{API}/ai/providers")
        assert res.status_code == 200
        data = res.json()
        assert "groq" in data
        assert data["groq"] is True

    def test_providers_endpoint_reports_groq_unconfigured(self, api_client, monkeypatch):
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        monkeypatch.setattr(settings, "STT_API_KEY", "")
        res = api_client.get(f"{API}/ai/providers")
        assert res.status_code == 200
        data = res.json()
        assert "groq" in data
        assert data["groq"] is False
