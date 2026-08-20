"""Tests for Matter Shared Spaces API (Milestone 6)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security.auth import AuthContext, get_auth_context, get_case_access


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id="test-lawyer-1",
        organization_id="test-org-1",
        role="LAWYER",
    )
    app.dependency_overrides[get_case_access] = lambda: (
        AuthContext(user_id="test-lawyer-1", organization_id="test-org-1", role="LAWYER"),
        {"id": "case-test-101", "name": "Brigade Meadows Sy 124 Title Search"},
    )
    yield
    app.dependency_overrides.pop(get_auth_context, None)
    app.dependency_overrides.pop(get_case_access, None)


@pytest.mark.asyncio
async def test_create_and_access_shared_space(auth_override):
    """Test full shared space flow: creation, metadata retrieval, and passcode unlock."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create Shared Space
        payload = {
            "case_id": "case-test-101",
            "name": "Client Title Review Space",
            "recipient_email": "client@enterprise.com",
            "recipient_name": "General Counsel",
            "role": "VIEWER",
            "duration": "24h",
            "passcode": "Secret1234",
            "watermark_enabled": True,
        }
        res_create = await ac.post("/api/v1/shared-spaces/cases/case-test-101/create", json=payload)
        assert res_create.status_code == 200
        share_data = res_create.json()
        token = share_data["token"]
        assert share_data["has_passcode"] is True
        assert share_data["recipient_email"] == "client@enterprise.com"

        # 2. Get Public Metadata (Unauthenticated)
        res_meta = await ac.get(f"/api/v1/shared-spaces/access/{token}")
        assert res_meta.status_code == 200
        meta = res_meta.json()
        assert meta["has_passcode"] is True
        assert meta["watermark_enabled"] is True

        # 3. Fail on Wrong Passcode
        res_fail = await ac.post(f"/api/v1/shared-spaces/access/{token}/verify", json={"passcode": "WrongPass"})
        assert res_fail.status_code == 401

        # 4. Success on Correct Passcode
        res_pass = await ac.post(f"/api/v1/shared-spaces/access/{token}/verify", json={"passcode": "Secret1234"})
        assert res_pass.status_code == 200
        session_data = res_pass.json()
        assert session_data["authenticated"] is True
        assert session_data["role"] == "VIEWER"
        assert "svg_watermark" in session_data
