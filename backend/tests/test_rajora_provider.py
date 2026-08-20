"""Tests for RajoraProvider (Backend LLM Provider Implementation)."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.ai.provider import RajoraProvider, LLMRequest, LLMResponse, _PROVIDERS
from app.config import get_settings


@pytest.fixture
def configured_rajora(monkeypatch):
    """Ensure Rajora settings are configured for tests."""
    settings = get_settings()
    monkeypatch.setattr(settings, "RAJORA_BASE_URL", "http://localhost:8080")
    monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "rj_live_testservicekey123456789012")
    monkeypatch.setattr(settings, "RAJORA_DEFAULT_MODEL", "rajora-private-v1")
    monkeypatch.setattr(settings, "RAJORA_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(settings, "RAJORA_INTERNAL_SECRET", "test-internal-secret-999")
    return settings


class TestRajoraProvider:
    def test_rajora_registered_in_providers(self):
        assert "rajora" in _PROVIDERS
        assert isinstance(_PROVIDERS["rajora"], RajoraProvider)

    def test_is_configured_true(self, configured_rajora):
        provider = RajoraProvider()
        assert provider.is_configured() is True

    def test_is_configured_false_missing_url(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", "")
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "some-key")
        provider = RajoraProvider()
        assert provider.is_configured() is False

    def test_is_configured_false_missing_key(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", "http://localhost:8080")
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "")
        provider = RajoraProvider()
        assert provider.is_configured() is False

    async def test_list_models(self, configured_rajora):
        provider = RajoraProvider()
        models = await provider.list_models()
        assert "rajora-private-v1" in models

    async def test_complete_not_configured_raises(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", "")
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "")
        provider = RajoraProvider()

        req = LLMRequest(system="", prompt="Hello")
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.complete(req)

    async def test_complete_success(self, configured_rajora):
        provider = RajoraProvider()
        req = LLMRequest(
            system="You are a legal assistant.",
            prompt="Analyze this clause.",
            max_tokens=1024,
            temperature=0.1,
            model="rajora-private-v1",
        )

        mock_response_data = {
            "text": "This clause specifies governing law in Karnataka.",
            "prompt_tokens": 15,
            "completion_tokens": 10,
        }

        mock_resp = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("POST", "http://localhost:8080/generate"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            resp = await provider.complete(req)

            assert isinstance(resp, LLMResponse)
            assert resp.provider == "rajora"
            assert resp.model == "rajora-private-v1"
            assert resp.content == "This clause specifies governing law in Karnataka."
            assert resp.prompt_tokens == 15
            assert resp.completion_tokens == 10
            assert resp.estimated_cost_usd == 0.0
            assert resp.latency_ms >= 0

            # Verify request headers and payload
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0] == "http://localhost:8080/generate"
            assert call_kwargs["headers"]["X-API-Key"] == "rj_live_testservicekey123456789012"
            assert "prompt" in call_kwargs["json"]
            assert "Analyze this clause." in call_kwargs["json"]["prompt"]
            assert "You are a legal assistant." in call_kwargs["json"]["prompt"]
            assert call_kwargs["json"]["max_tokens"] == 1024
            assert call_kwargs["json"]["temperature"] == 0.1

    async def test_complete_alternate_response_format(self, configured_rajora):
        provider = RajoraProvider()
        req = LLMRequest(system="", prompt="Summarize deed")

        mock_response_data = {
            "choices": [{"text": "Deed summary content"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 30},
        }

        mock_resp = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("POST", "http://localhost:8080/generate"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            resp = await provider.complete(req)

            assert resp.content == "Deed summary content"
            assert resp.prompt_tokens == 20
            assert resp.completion_tokens == 30
            assert resp.estimated_cost_usd == 0.0

    async def test_complete_http_error_mapped(self, configured_rajora):
        provider = RajoraProvider()
        req = LLMRequest(system="", prompt="Test prompt")

        mock_resp = httpx.Response(
            status_code=500,
            text="Internal Server Error in inference engine",
            request=httpx.Request("POST", "http://localhost:8080/generate"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError, match="Rajora LLM error 500"):
                await provider.complete(req)

    async def test_complete_connection_error_mapped(self, configured_rajora):
        provider = RajoraProvider()
        req = LLMRequest(system="", prompt="Test prompt")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            with pytest.raises(RuntimeError, match="Rajora LLM connection error"):
                await provider.complete(req)
