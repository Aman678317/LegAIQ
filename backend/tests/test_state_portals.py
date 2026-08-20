"""Tests for 5 State Land Portal Connectors API (Milestone 7)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security.auth import AuthContext, get_auth_context


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id="test-lawyer-1",
        organization_id="test-org-1",
        role="LAWYER",
    )
    yield
    app.dependency_overrides.pop(get_auth_context, None)


@pytest.mark.asyncio
async def test_get_supported_portals(auth_override):
    """Verify supported portals returns all 5 Indian states."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/property/portals/supported")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 5
        states = [p["state_code"] for p in data["portals"]]
        assert "maharashtra" in states
        assert "karnataka" in states
        assert "tamil_nadu" in states
        assert "telangana" in states
        assert "gujarat" in states


@pytest.mark.asyncio
async def test_search_karnataka_bhoomi_portal(auth_override):
    """Test live/mock query against Karnataka Bhoomi portal."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "state": "karnataka",
            "survey_number": "124/2",
            "district": "Bangalore Urban",
            "taluk": "Bangalore South",
            "village": "Varthur",
        }
        res = await ac.post("/api/v1/property/portals/search", json=payload)
        assert res.status_code == 200
        report = res.json()
        assert "base_record" in report
        assert report["base_record"]["survey_number"] == "124/2"
        assert report["base_record"]["document_type"] == "RTC (Record of Rights, Tenancy and Crops)"
        assert len(report["mutation_history"]) >= 1
