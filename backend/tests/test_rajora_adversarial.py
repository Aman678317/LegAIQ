"""Adversarial stress tests for Rajora Private LLM implementation.

Empirically tests security boundaries, edge cases, error propagation,
key entropy, and invariant preservation.
"""
import hashlib
import hmac
import math
import secrets
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.ai.provider import RajoraProvider, LLMRequest, LLMResponse, _PROVIDERS
from app.config import get_settings
from tests.conftest import ADMIN_USER_ID, ORG_ID, USER_ID

API = "/api/v1"


@pytest.fixture
def configured_rajora_adversarial(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "RAJORA_BASE_URL", "http://localhost:8080")
    monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "rj_live_valid_service_key_1234567890abcdef")
    monkeypatch.setattr(settings, "RAJORA_DEFAULT_MODEL", "rajora-private-v1")
    monkeypatch.setattr(settings, "RAJORA_INTERNAL_SECRET", "super-secret-rajora-internal-key-888")
    monkeypatch.setattr(settings, "RAJORA_TIMEOUT_SECONDS", 15)
    return settings


# ============================================================================
# 1. Adversarial Tests for Internal Key Verification (/internal/rajora/verify-key)
# ============================================================================

class TestAdversarialInternalKeyVerification:
    """Adversarial challenge for internal key verification endpoint."""

    @pytest.mark.parametrize(
        "secret_header",
        [
            None,                           # Missing header
            "",                             # Empty header
            "wrong-secret",                 # Incorrect secret
            "super-secret-rajora-internal", # Prefix substring attack
            "super-secret-rajora-internal-key-888-extra", # Suffix extension attack
            "SUPER-SECRET-RAJORA-INTERNAL-KEY-888",       # Case sensitivity attack
            "\x00super-secret",             # Null byte prefix
            " " * 32,                       # Whitespace attack
        ],
    )
    def test_unauthorized_internal_secret_rejected(self, api_client, configured_rajora_adversarial, secret_header):
        headers = {"X-API-Key": "rj_live_some_api_key"}
        if secret_header is not None:
            headers["X-Internal-Secret"] = secret_header

        res = api_client.post("/internal/rajora/verify-key", headers=headers)
        assert res.status_code == 401, f"Expected 401 for secret '{secret_header}', got {res.status_code}"

    def test_unconfigured_internal_secret_rejects_all(self, api_client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_INTERNAL_SECRET", "")

        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "any-secret",
                "X-API-Key": "rj_live_any_key",
            },
        )
        assert res.status_code == 401

    @pytest.mark.parametrize(
        "malformed_key",
        [
            "",                                      # Empty string
            "not_even_prefixed",                     # No prefix
            "other_vendor_key_1234567890abcdef",     # Non-rajora prefix
            "Bearer rj_live_1234567890abcdef",       # Bearer scheme prepended
            "rj_live_!@#$%^&*()_+=-~`",             # Special characters
            "rj_live_" + "A" * 48,                   # Uppercase non-hex
            "rj_live_zzzzzzzzzzzzzzzzzzzzzzzzzzzz",  # Invalid hex chars
            "rj_live_12345\x00malicious",            # Null byte injection
            "'; DROP TABLE rajora_llm_keys; --",     # SQL injection attack
            "../../../../etc/passwd",                # Path traversal attempt
            "rj_live_" + "a" * 100000,               # 100KB oversized key
            "rj_live_invalid_escaped_unicode_test",   # Escaped unicode
        ],
    )
    def test_malformed_api_keys_rejected(self, api_client, configured_rajora_adversarial, malformed_key):
        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "super-secret-rajora-internal-key-888",
                "X-API-Key": malformed_key,
            },
        )
        # Must return 401 Unauthorized, never 500 or crash
        assert res.status_code == 401, f"Expected 401 for malformed key '{malformed_key[:30]}', got {res.status_code}"

    def test_inactive_and_revoked_keys_rejected(self, api_client, fake, configured_rajora_adversarial):
        # 1. Inactive key
        raw_inactive = "rj_live_000000000000000000000000000000000000000000000001"
        fake.tables.rows("rajora_llm_keys").append({
            "id": "key-inactive-99",
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "key_hash": hashlib.sha256(raw_inactive.encode("utf-8")).hexdigest(),
            "key_prefix": raw_inactive[:12],
            "label": "Inactive Key",
            "active": False,
            "created_at": "2026-08-20T00:00:00+00:00",
            "revoked_at": None,
        })

        # 2. Revoked key
        raw_revoked = "rj_live_000000000000000000000000000000000000000000000002"
        fake.tables.rows("rajora_llm_keys").append({
            "id": "key-revoked-99",
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "key_hash": hashlib.sha256(raw_revoked.encode("utf-8")).hexdigest(),
            "key_prefix": raw_revoked[:12],
            "label": "Revoked Key",
            "active": False,
            "created_at": "2026-08-20T00:00:00+00:00",
            "revoked_at": "2026-08-20T10:00:00+00:00",
        })

        # Query inactive
        res1 = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "super-secret-rajora-internal-key-888",
                "X-API-Key": raw_inactive,
            },
        )
        assert res1.status_code == 401

        # Query revoked
        res2 = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "super-secret-rajora-internal-key-888",
                "X-API-Key": raw_revoked,
            },
        )
        assert res2.status_code == 401


# ============================================================================
# 2. Key Generation Entropy and Format Invariants
# ============================================================================

class TestKeyGenerationEntropyAndFormat:
    """Verify cryptographic randomness, format, and entropy for generated keys."""

    def test_key_entropy_and_format_distribution(self, admin_api_client, fake):
        generated_keys = set()
        hex_charset = set("0123456789abcdef")

        # Generate 50 keys and stress-test distribution
        for i in range(50):
            res = admin_api_client.post(
                f"{API}/admin/rajora-keys",
                json={"org_id": ORG_ID, "label": f"Key Entropy Test {i}"},
            )
            assert res.status_code == 200, res.text
            data = res.json()
            raw_key = data["api_key"]

            # Invariant 1: Prefix format
            assert raw_key.startswith("rj_live_"), f"Invalid prefix on key: {raw_key}"

            # Invariant 2: Total length is 56 (rj_live_ is 8 chars + 48 hex chars = 56)
            assert len(raw_key) == 56, f"Key length {len(raw_key)} != 56"

            # Invariant 3: Suffix contains only lowercase hex characters
            hex_part = raw_key[8:]
            assert len(hex_part) == 48
            assert set(hex_part).issubset(hex_charset), f"Non-hex chars in key: {hex_part}"

            # Invariant 4: Key prefix stored matches first 12 characters
            assert data["key_prefix"] == raw_key[:12]

            # Invariant 5: Hash in DB is SHA-256 of raw key
            expected_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            row = next(k for k in fake.tables.rows("rajora_llm_keys") if k["id"] == data["id"])
            assert row["key_hash"] == expected_hash

            # Invariant 6: No duplicate keys generated (collision resistance)
            assert raw_key not in generated_keys, "Collision detected in secrets.token_hex generator!"
            generated_keys.add(raw_key)

            # Invariant 7: Shannon entropy of hex portion
            entropy = 0.0
            for c in set(hex_part):
                prob = hex_part.count(c) / len(hex_part)
                entropy -= prob * math.log2(prob)
            # High entropy expectation for random 48-character hex string (max 4.0 bits, expect >= 3.0)
            assert entropy >= 3.0, f"Low entropy detected: {entropy} bits/char"

    def test_key_hashes_never_leaked_in_admin_responses(self, admin_api_client, fake):
        res = admin_api_client.get(f"{API}/admin/rajora-keys?org_id={ORG_ID}")
        assert res.status_code == 200
        items = res.json()["items"]
        for item in items:
            assert "key_hash" not in item, "SECURITY FLAW: key_hash leaked in admin key list!"
            assert "api_key" not in item, "SECURITY FLAW: raw api_key leaked in admin key list!"


# ============================================================================
# 3. RajoraProvider Configuration and Upstream Error Handling
# ============================================================================

class TestAdversarialRajoraProvider:
    """Stress-test RajoraProvider edge cases and error mapping."""

    @pytest.mark.parametrize(
        "base_url,api_key,expected_configured",
        [
            ("", "", False),
            ("http://localhost:8080", "", False),
            ("", "rj_live_valid_key", False),
            ("   ", "rj_live_valid_key", False),
            ("http://localhost:8080", "   ", False),
            ("http://localhost:8080", "rj_live_valid_key", True),
        ],
    )
    def test_is_configured_invariants(self, monkeypatch, base_url, api_key, expected_configured):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", base_url.strip())
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", api_key.strip())
        provider = RajoraProvider()
        assert provider.is_configured() is expected_configured

    async def test_unconfigured_provider_complete_raises_immediately(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", "")
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "")
        provider = RajoraProvider()
        req = LLMRequest(system="", prompt="test")
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.complete(req)

    @pytest.mark.parametrize(
        "status_code,error_body",
        [
            (400, '{"error": "bad_request", "detail": "Invalid prompt format"}'),
            (401, '{"error": "unauthorized", "detail": "Invalid upstream API key"}'),
            (403, '{"error": "forbidden", "detail": "Access to model denied"}'),
            (404, '{"error": "not_found", "detail": "Model rajora-private-v1 not loaded"}'),
            (429, '{"error": "rate_limited", "detail": "Inference worker concurrency limit reached"}'),
            (500, '{"error": "internal_error", "detail": "CUDA out of memory"}'),
            (502, "Bad Gateway: Upstream LLM daemon unreachable"),
            (503, "Service Unavailable: Model warm-up in progress"),
            (504, "Gateway Timeout"),
        ],
    )
    async def test_upstream_http_status_errors_gracefully_mapped(
        self, configured_rajora_adversarial, status_code, error_body
    ):
        provider = RajoraProvider()
        req = LLMRequest(system="System instructions", prompt="Adversarial input")

        mock_resp = httpx.Response(
            status_code=status_code,
            text=error_body,
            request=httpx.Request("POST", "http://localhost:8080/generate"),
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError) as exc_info:
                await provider.complete(req)
            assert f"Rajora LLM error {status_code}" in str(exc_info.value)
            assert (error_body in str(exc_info.value)) or (str(status_code) in str(exc_info.value))

    @pytest.mark.parametrize(
        "network_exception,expected_msg",
        [
            (httpx.ConnectError("Connection refused to 127.0.0.1:8080"), "Rajora LLM connection error"),
            (httpx.ConnectTimeout("Timed out connecting to inference server"), "Rajora LLM connection error"),
            (httpx.ReadTimeout("Inference read timed out after 120s"), "Rajora LLM connection error"),
            (httpx.RemoteProtocolError("Server disconnected unexpectedly"), "Rajora LLM connection error"),
        ],
    )
    async def test_network_and_timeout_drops_gracefully_mapped(
        self, configured_rajora_adversarial, network_exception, expected_msg
    ):
        provider = RajoraProvider()
        req = LLMRequest(system="", prompt="Evaluate deed validity")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = network_exception
            with pytest.raises(RuntimeError) as exc_info:
                await provider.complete(req)
            assert expected_msg in str(exc_info.value)

    # Invariant: Zero Third-Party Cost
    @pytest.mark.parametrize(
        "response_payload",
        [
            {"text": "Sample completion text", "prompt_tokens": 100, "completion_tokens": 50},
            {"content": "Alternate key format", "prompt_tokens": 0, "completion_tokens": 0},
            {"response": "Third format", "usage": {"prompt_tokens": 500, "completion_tokens": 200}},
            {"choices": [{"text": "Choice format"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10}},
            "Raw string response",
        ],
    )
    async def test_cost_invariant_zero_cost(self, configured_rajora_adversarial, response_payload):
        provider = RajoraProvider()
        req = LLMRequest(system="System instructions", prompt="Compute invariant")

        if isinstance(response_payload, (dict, list)):
            mock_resp = httpx.Response(
                status_code=200,
                json=response_payload,
                request=httpx.Request("POST", "http://localhost:8080/generate"),
            )
        else:
            mock_resp = httpx.Response(
                status_code=200,
                text=response_payload,
                request=httpx.Request("POST", "http://localhost:8080/generate"),
            )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            resp = await provider.complete(req)

            assert isinstance(resp, LLMResponse)
            assert resp.provider == "rajora"
            # Critical invariant: Zero third-party inference cost
            assert resp.estimated_cost_usd == 0.0, f"Invariant violated! estimated_cost_usd is {resp.estimated_cost_usd}"
