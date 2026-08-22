"""Tests for Deep Research FastAPI Endpoints & Streaming Engine."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.security.auth import AuthContext, get_auth_context, get_case_access
from tests.conftest import USER_ID, ORG_ID


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="LAWYER",
    )
    app.dependency_overrides[get_case_access] = lambda: (
        AuthContext(user_id=USER_ID, organization_id=ORG_ID, role="LAWYER"),
        {"id": "case-test-101", "name": "Deep Research Test Case", "organization_id": ORG_ID},
    )
    yield
    app.dependency_overrides.pop(get_auth_context, None)
    app.dependency_overrides.pop(get_case_access, None)


@pytest.mark.asyncio
async def test_start_deep_research_endpoint(auth_override):
    """Test starting deep research session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "question": "What is the landmark Supreme Court ratio on electronic secondary evidence under BSA 2023 §63?",
            "model": "o4-mini-deep-research",
            "max_tool_calls": 3,
        }
        res = await ac.post("/api/v1/cases/case-test-101/deep-research", json=payload)
        assert res.status_code == 202
        data = res.json()
        assert "task_id" in data
        assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_list_deep_research_history(auth_override):
    """Test listing deep research results for case."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/cases/case-test-101/deep-research")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
