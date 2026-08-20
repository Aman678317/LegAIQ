"""Tests for Workflows API and Async Execution Engine (Milestone 4)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.workflows import PREBUILT_TEMPLATES
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
async def test_get_agent_library(auth_override):
    """Verify library endpoint returns all 6 specialist agents."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/workflows/agents/library")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 6
        assert len(data["agents"]) == 6


@pytest.mark.asyncio
async def test_list_workflows_with_templates(auth_override):
    """Verify workflow list includes pre-built templates."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/workflows?include_templates=true")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= len(PREBUILT_TEMPLATES)
        tpl_ids = [w["id"] for w in data["workflows"]]
        assert "tpl-prop-dd" in tpl_ids
        assert "tpl-litigation-strategy" in tpl_ids


@pytest.mark.asyncio
async def test_create_and_execute_custom_workflow(auth_override):
    """Test custom workflow creation and async execution initiation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create Workflow
        wf_payload = {
            "name": "Quick Title Risk Pipeline",
            "description": "Examines title and assesses risk",
            "version": "1.0",
            "nodes": [
                {
                    "id": "step_1",
                    "name": "Title Check",
                    "agent_type": "title_examiner_agent",
                    "dependencies": [],
                    "result_key": "title_res",
                },
                {
                    "id": "step_2",
                    "name": "Risk Audit",
                    "agent_type": "risk_auditor_agent",
                    "dependencies": ["step_1"],
                    "result_key": "risk_res",
                },
            ],
            "tags": ["Property", "Fast Track"],
        }
        res_create = await ac.post("/api/v1/workflows", json=wf_payload)
        assert res_create.status_code == 200
        created = res_create.json()
        wf_id = created["id"]
        assert created["name"] == "Quick Title Risk Pipeline"

        # 2. Execute Workflow
        exec_payload = {
            "case_id": "test-case-101",
            "inputs": {"survey_number": "124/2"},
        }
        res_exec = await ac.post(f"/api/v1/workflows/{wf_id}/execute", json=exec_payload)
        assert res_exec.status_code == 200
        exec_data = res_exec.json()
        assert "execution_id" in exec_data
        assert exec_data["status"] == "running"
        assert "stream_url" in exec_data
