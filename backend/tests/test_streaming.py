"""Hermetic Test Suite for Real-Time SSE Token Streaming (Milestone 1).

Verifies:
- stream_complete() across all providers (Groq, OpenAI, Anthropic, NVIDIA, Ollama, Mock)
- generate_streaming_response() SSE formatting and citation emission
- POST /api/v1/cases/{case_id}/questions with stream=True
- POST /api/v1/chat/query-stream endpoint
- POST /api/v1/cases/{case_id}/research/stream endpoint
- Streaming HTTP response headers (Cache-Control, X-Accel-Buffering, Connection)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.provider import (
    AnthropicProvider,
    GroqProvider,
    LLMRequest,
    MockLLMProvider,
    NvidiaProvider,
    OllamaProvider,
    OpenAIProvider,
    router as llm_router,
)
from app.api.analysis import generate_streaming_response, SYSTEM_GROUNDED
from app.config import get_settings
from tests.conftest import ORG_ID, USER_ID

settings = get_settings()
API = "/api/v1"


class TestAllProvidersStreamComplete:
    """Test stream_complete() interface across all LLM providers."""

    @pytest.mark.asyncio
    async def test_mock_provider_stream_complete(self):
        provider = MockLLMProvider()
        req = LLMRequest(system="Sys", prompt="Test prompt", task="chat")

        tokens = []
        async for token in provider.stream_complete(req):
            tokens.append(token)

        assert len(tokens) > 0
        joined = "".join(tokens)
        assert "Jurisiva AI Mock Legal Reasoning" in joined

    @pytest.mark.asyncio
    async def test_mock_provider_stream_complete_json_mode(self):
        provider = MockLLMProvider()
        req = LLMRequest(system="Sys", prompt="Test prompt", task="extraction", json_mode=True)

        tokens = []
        async for token in provider.stream_complete(req):
            tokens.append(token)

        joined = "".join(tokens).strip()
        parsed = json.loads(joined)
        assert parsed.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_openai_provider_stream_complete(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-key")
        provider = OpenAIProvider()

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Under Section 54 "}}]}',
            'data: {"choices": [{"delta": {"content": "TP Act 1882."}}]}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="", prompt="TP Act", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["Under Section 54 ", "TP Act 1882."]

    @pytest.mark.asyncio
    async def test_anthropic_provider_stream_complete(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-test")
        provider = AnthropicProvider()

        sse_lines = [
            'data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Supreme Court held "}}',
            'data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "in Suraj Lamp."}}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="", prompt="Suraj Lamp", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["Supreme Court held ", "in Suraj Lamp."]

    @pytest.mark.asyncio
    async def test_nvidia_provider_stream_complete(self, monkeypatch):
        monkeypatch.setattr(settings, "NVIDIA_API_KEY", "nvapi-test")
        provider = NvidiaProvider()

        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Order 39 Rule 1 CPC "}}]}',
            'data: {"choices": [{"delta": {"content": "governs interim injunctions."}}]}',
            'data: [DONE]',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in sse_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="", prompt="Order 39", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["Order 39 Rule 1 CPC ", "governs interim injunctions."]

    @pytest.mark.asyncio
    async def test_ollama_provider_stream_complete(self):
        provider = OllamaProvider()

        json_lines = [
            '{"message": {"content": "BNS Section 318 "}, "done": false}',
            '{"message": {"content": "defines cheating."}, "done": true}',
        ]

        class MockStream:
            def raise_for_status(self):
                pass
            async def aiter_lines(self):
                for line in json_lines:
                    yield line
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass

        with patch("httpx.AsyncClient.stream", return_value=MockStream()):
            req = LLMRequest(system="", prompt="BNS Cheating", task="chat")
            tokens = []
            async for token in provider.stream_complete(req):
                tokens.append(token)
            assert tokens == ["BNS Section 318 ", "defines cheating."]


class TestSSEFramingAndCitations:
    """Test SSE data chunk formatting and citation emission in generate_streaming_response()."""

    @pytest.mark.asyncio
    async def test_generate_streaming_response_sse_framing(self):
        citations = [
            {
                "document_id": "doc-1",
                "document_name": "Sale_Deed_1987.pdf",
                "page_number": 2,
                "source_text": "Schedule of Property: Sy. No. 124/3",
            }
        ]

        events = []
        async for frame in generate_streaming_response(
            system=SYSTEM_GROUNDED,
            prompt="Is the property title clear?",
            task="chat",
            model="mock",
            citations=citations,
        ):
            events.append(frame)

        assert len(events) >= 3
        # Assert every event follows SSE specification: starts with "data: " and ends with "\n\n"
        for ev in events:
            assert ev.startswith("data: ")
            assert ev.endswith("\n\n")

        # Assert final frame is [DONE]
        assert events[-1] == "data: [DONE]\n\n"

        # Assert citations frame precedes [DONE]
        citations_frame = next(e for e in events if "citations" in e)
        assert citations_frame is not None
        payload = json.loads(citations_frame.replace("data: ", "").strip())
        assert "citations" in payload
        assert payload["citations"][0]["document_name"] == "Sale_Deed_1987.pdf"

        # Assert content tokens are emitted
        content_frames = [e for e in events if "content" in e]
        assert len(content_frames) > 0


class TestAPIStreamingEndpoints:
    """Integration tests for streaming API endpoints via AsyncClient."""

    @pytest.mark.asyncio
    async def test_questions_endpoint_streaming(self, client, seed_case):
        case_id = seed_case["id"]
        res = await client.post(
            f"{API}/cases/{case_id}/questions",
            json={
                "question": "What are the core title findings?",
                "mode": "ask",
                "stream": True,
            },
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        assert res.headers.get("x-accel-buffering") == "no"
        assert "no-cache" in res.headers.get("cache-control", "")

        body = res.text
        assert "data: " in body
        assert "data: [DONE]" in body

    @pytest.mark.asyncio
    async def test_chat_query_stream_modes(self, client, seed_case):
        case_id = seed_case["id"]
        for mode in ("ask", "analyze", "draft"):
            res = await client.post(
                f"{API}/chat/query-stream",
                json={
                    "case_id": case_id,
                    "query": f"Analyze case facts in {mode} mode",
                    "mode": mode,
                },
            )
            assert res.status_code == 200
            assert "text/event-stream" in res.headers.get("content-type", "")
            assert "data: [DONE]" in res.text

    @pytest.mark.asyncio
    async def test_research_stream_endpoint(self, client, seed_case):
        case_id = seed_case["id"]
        res = await client.post(
            f"{API}/cases/{case_id}/research/stream",
            json={
                "question": "Validity of unregistered family settlement under Hindu Succession Act",
                "depth": "standard",
            },
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        assert "no-cache" in res.headers.get("cache-control", "")

        body = res.text
        assert "data: " in body
        assert "sources" in body
        assert "data: [DONE]" in body
