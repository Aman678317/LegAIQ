"""Tests for Rajora API endpoints: Internal Key Verification, Health Check, and Admin Key Management."""
import hashlib
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.config import get_settings
from tests.conftest import ADMIN_USER_ID, ORG_ID, USER_ID

API = "/api/v1"


@pytest.fixture
def configured_rajora_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "RAJORA_BASE_URL", "http://localhost:8080")
    monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "rj_live_mock_service_key_1234567890")
    monkeypatch.setattr(settings, "RAJORA_DEFAULT_MODEL", "rajora-private-v1")
    monkeypatch.setattr(settings, "RAJORA_INTERNAL_SECRET", "super-secret-internal-token-42")
    return settings


class TestInternalVerifyKey:
    def test_verify_key_success(self, api_client, fake, configured_rajora_settings):
        # Seed an active Rajora key
        raw_key = "rj_live_1234567890abcdef1234567890abcdef1234567890abcdef"
        key_prefix = raw_key[:12]
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        key_row = {
            "id": "key-test-001",
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "label": "Test Production Key",
            "active": True,
            "created_at": "2026-08-20T00:00:00+00:00",
            "last_used_at": None,
        }
        fake.tables.rows("rajora_llm_keys").append(key_row)

        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "super-secret-internal-token-42",
                "X-API-Key": raw_key,
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["valid"] is True
        assert data["active"] is True
        assert data["org_id"] == ORG_ID
        assert data["user_id"] == USER_ID
        assert data["key_prefix"] == key_prefix
        assert data["last_used_at"] is not None

        # Verify DB touch
        stored = next(k for k in fake.tables.rows("rajora_llm_keys") if k["id"] == "key-test-001")
        assert stored["last_used_at"] is not None

    def test_verify_key_invalid_secret(self, api_client, configured_rajora_settings):
        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "wrong-secret",
                "X-API-Key": "rj_live_anykey",
            },
        )
        assert res.status_code == 401

    def test_verify_key_missing_secret(self, api_client, configured_rajora_settings):
        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={"X-API-Key": "rj_live_anykey"},
        )
        assert res.status_code == 401

    def test_verify_key_missing_key(self, api_client, configured_rajora_settings):
        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={"X-Internal-Secret": "super-secret-internal-token-42"},
        )
        assert res.status_code == 401

    def test_verify_key_inactive_or_revoked(self, api_client, fake, configured_rajora_settings):
        raw_key = "rj_live_revoked_key_1234567890abcdef1234567890abcdef"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        key_row = {
            "id": "key-revoked-001",
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "key_hash": key_hash,
            "key_prefix": raw_key[:12],
            "label": "Revoked Key",
            "active": False,
            "created_at": "2026-08-20T00:00:00+00:00",
            "revoked_at": "2026-08-20T12:00:00+00:00",
        }
        fake.tables.rows("rajora_llm_keys").append(key_row)

        res = api_client.post(
            "/internal/rajora/verify-key",
            headers={
                "X-Internal-Secret": "super-secret-internal-token-42",
                "X-API-Key": raw_key,
            },
        )
        assert res.status_code == 401


class TestRajoraHealth:
    def test_health_online(self, api_client, configured_rajora_settings):
        mock_resp = httpx.Response(
            status_code=200,
            json={"status": "ok"},
            request=httpx.Request("GET", "http://localhost:8080/health"),
        )
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("app.api.rajora.httpx.AsyncClient", return_value=mock_client):
            res = api_client.get(f"{API}/rajora/health")
            assert res.status_code == 200
            data = res.json()
            assert data["online"] is True
            assert data["status"] == "healthy"
            assert data["provider"] == "rajora"
            assert data["model"] == "rajora-private-v1"
            assert "latency_ms" in data

    def test_health_direct_api_prefix(self, api_client, configured_rajora_settings):
        mock_resp = httpx.Response(
            status_code=200,
            json={"status": "ok"},
            request=httpx.Request("GET", "http://localhost:8080/health"),
        )
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("app.api.rajora.httpx.AsyncClient", return_value=mock_client):
            res = api_client.get("/api/rajora/health")
            assert res.status_code == 200
            data = res.json()
            assert data["online"] is True
            assert data["status"] == "healthy"

    def test_health_unconfigured(self, api_client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "RAJORA_BASE_URL", "")
        monkeypatch.setattr(settings, "RAJORA_SERVICE_API_KEY", "")

        res = api_client.get(f"{API}/rajora/health")
        assert res.status_code == 200
        data = res.json()
        assert data["online"] is False
        assert data["status"] == "unconfigured"

    def test_health_unreachable(self, api_client, configured_rajora_settings):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with patch("app.api.rajora.httpx.AsyncClient", return_value=mock_client):
            res = api_client.get(f"{API}/rajora/health")
            assert res.status_code == 200
            data = res.json()
            assert data["online"] is False
            assert data["status"] == "unreachable"


class TestAdminRajoraKeyManagement:
    def test_admin_create_key(self, admin_api_client, fake):
        res = admin_api_client.post(
            f"{API}/admin/rajora-keys",
            json={
                "org_id": ORG_ID,
                "user_id": USER_ID,
                "label": "Primary Inference Key",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["id"]
        assert data["org_id"] == ORG_ID
        assert data["user_id"] == USER_ID
        assert data["label"] == "Primary Inference Key"
        assert data["active"] is True
        assert "api_key" in data
        assert data["api_key"].startswith("rj_live_")
        assert data["key_prefix"] == data["api_key"][:12]

        # Verify key hash is in database
        expected_hash = hashlib.sha256(data["api_key"].encode("utf-8")).hexdigest()
        stored = next(k for k in fake.tables.rows("rajora_llm_keys") if k["id"] == data["id"])
        assert stored["key_hash"] == expected_hash
        assert stored["key_prefix"] == data["key_prefix"]
        assert stored["active"] is True

        # Verify audit event
        audits = [a for a in fake.tables.rows("audit_events") if a["action"] == "admin.rajora_key_created"]
        assert len(audits) == 1
        assert audits[0]["resource_id"] == data["id"]

    def test_admin_create_key_invalid_org(self, admin_api_client, fake):
        res = admin_api_client.post(
            f"{API}/admin/rajora-keys",
            json={
                "org_id": "00000000-0000-4000-8000-999999999999",
                "label": "Invalid Org Key",
            },
        )
        assert res.status_code == 404

    def test_admin_revoke_key(self, admin_api_client, fake):
        # Create key first
        create_res = admin_api_client.post(
            f"{API}/admin/rajora-keys",
            json={"org_id": ORG_ID, "label": "Key to Revoke"},
        )
        key_id = create_res.json()["id"]

        # Revoke key
        res = admin_api_client.post(f"{API}/admin/rajora-keys/{key_id}/revoke")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["id"] == key_id
        assert data["active"] is False
        assert data["revoked_at"] is not None

        # Verify in DB
        stored = next(k for k in fake.tables.rows("rajora_llm_keys") if k["id"] == key_id)
        assert stored["active"] is False
        assert stored["revoked_at"] is not None

        # Verify audit event
        audits = [a for a in fake.tables.rows("audit_events") if a["action"] == "admin.rajora_key_revoked"]
        assert len(audits) == 1

    def test_admin_list_keys(self, admin_api_client, fake):
        admin_api_client.post(
            f"{API}/admin/rajora-keys",
            json={"org_id": ORG_ID, "label": "Key 1"},
        )
        admin_api_client.post(
            f"{API}/admin/rajora-keys",
            json={"org_id": ORG_ID, "label": "Key 2"},
        )

        res = admin_api_client.get(f"{API}/admin/rajora-keys?org_id={ORG_ID}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        # Ensure secret key_hash is NOT exposed in listing
        for item in data["items"]:
            assert "key_hash" not in item
            assert "key_prefix" in item
            assert "label" in item

    def test_non_admin_forbidden(self, api_client):
        # api_client is authenticated as standard lawyer, not platform admin
        res = api_client.post(
            f"{API}/admin/rajora-keys",
            json={"org_id": ORG_ID, "label": "Forbidden Key"},
        )
        assert res.status_code == 403

        res_revoke = api_client.post(f"{API}/admin/rajora-keys/some-id/revoke")
        assert res_revoke.status_code == 403

        res_list = api_client.get(f"{API}/admin/rajora-keys")
        assert res_list.status_code == 403
