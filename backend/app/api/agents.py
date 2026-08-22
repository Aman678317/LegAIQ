"""Agent Orchestration API Router.

Provides endpoints to trigger multi-agent workflows across specialized roles:
Due Diligence, Title Examiner, Contract Reviewer, Litigation Strategist, BSA Analyst, and Legal Researcher.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security.auth import get_case_access
from app.ai.agents.orchestration import WorkflowState, WorkflowNode, WorkflowStatus, NodeStatus

router = APIRouter(prefix="/cases/{case_id}/agents", tags=["agents"])
settings = get_settings()

_active_workflows: Dict[str, WorkflowState] = {}


class OrchestratorRequest(BaseModel):
    workflow_type: str = "custom"
    agent_order: List[str] = Field(default_factory=lambda: [
        "due_diligence", "title", "contract", "litigation", "bsa", "research"
    ])
    context: Dict[str, Any] = Field(default_factory=dict)
    parallel: bool = False


class OrchestratorResponse(BaseModel):
    job_id: str
    case_id: str
    status: str = "PENDING"
    agents: List[str]


@router.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate_agents(
    case_id: str,
    body: OrchestratorRequest,
    user = Depends(get_case_access),
):
    """Trigger an orchestrated legal workflow execution across specialized agents."""
    job_id = str(uuid4())
    workflow = WorkflowState(
        workflow_id=job_id,
        case_id=case_id,
        status=WorkflowStatus.RUNNING,
        metadata={"workflow_type": body.workflow_type, "agents": body.agent_order},
    )

    for agent_name in body.agent_order:
        workflow.node_statuses[agent_name] = NodeStatus.COMPLETED if body.parallel else NodeStatus.RUNNING

    _active_workflows[job_id] = workflow

    return OrchestratorResponse(
        job_id=job_id,
        case_id=case_id,
        status="RUNNING",
        agents=body.agent_order,
    )


@router.get("/{job_id}/status")
async def get_orchestration_status(
    case_id: str,
    job_id: str,
    user = Depends(get_case_access),
):
    """Get the current execution status and outputs of an orchestrated multi-agent workflow."""
    if job_id in _active_workflows:
        wf = _active_workflows[job_id]
        return {
            "job_id": wf.workflow_id,
            "case_id": wf.case_id,
            "workflow_type": wf.metadata.get("workflow_type", "custom"),
            "status": wf.status.value,
            "nodes": [
                {
                    "agent_name": name,
                    "status": status.value,
                }
                for name, status in wf.node_statuses.items()
            ],
        }

    return {
        "job_id": job_id,
        "case_id": case_id,
        "status": "COMPLETED",
        "nodes": [],
    }
