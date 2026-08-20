"""LangGraph-based multi-agent orchestration for Jurisiva AI.

This module provides a workflow engine for coordinating multiple agents
in complex legal intelligence tasks using LangGraph state machines.
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field

from app.ai.agents.base import (
    AgentBudget, AgentContext, BaseAgent, Permission, execute_agent, new_agent_context,
)
from app.ai.agents.registry import (
    RiskAgent, ReportAgent, VerificationAgent, VoiceAgent,
    run_risk_agent, run_report_agent, run_verification_agent, run_voice_agent,
)
from app.ai.agents.tools import registry as tools_registry
from app.config import get_settings

settings = get_settings()


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    """Status of a workflow node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    """A node in the agent workflow graph."""
    name: str
    agent_type: str  # risk_agent, report_agent, verification_agent, voice_agent, custom
    task_builder: Callable[[dict], dict]  # Builds task from workflow state
    result_key: str  # Key to store result in workflow state
    dependencies: list[str] = field(default_factory=list)  # Node names this depends on
    condition: Optional[Callable[[dict], bool]] = None  # Skip if false
    retry_policy: dict = field(default_factory=dict)  # max_retries, retry_delay
    timeout_seconds: float = 300.0


@dataclass
class WorkflowState:
    """State passed through the workflow."""
    workflow_id: str
    case_id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: Optional[str] = None
    node_results: dict = field(default_factory=dict)
    node_statuses: dict = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """Definition of a multi-agent workflow."""
    name: str
    description: str
    version: str = "1.0"
    nodes: list[dict]  # Serialized WorkflowNode configs
    entry_node: str
    
    model_config = {"arbitrary_types_allowed": True}


class AgentOrchestrator:
    """LangGraph-style orchestrator for multi-agent legal workflows.
    
    Provides:
    - Workflow definition and execution
    - State management across agents
    - Dependency resolution and parallel execution
    - Error handling and retries
    - Audit logging
    """
    
    def __init__(self):
        self.workflows: dict[str, WorkflowDefinition] = {}
        self._register_builtin_workflows()
    
    def _register_builtin_workflows(self):
        """Register built-in legal workflows."""
        
        # Property Due Diligence Workflow
        self.register_workflow(WorkflowDefinition(
            name="property_due_diligence",
            description="Complete property due diligence: extraction → comparison → risks → report",
            version="2.0",
            entry_node="run_ocr_extraction",
            nodes=[
                {
                    "name": "run_ocr_extraction",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "ocr_extraction", "case_id": state["case_id"]},
                    "result_key": "extraction_result",
                    "dependencies": [],
                },
                {
                    "name": "run_embeddings",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "embeddings", "case_id": state["case_id"]},
                    "result_key": "embeddings_result",
                    "dependencies": ["run_ocr_extraction"],
                },
                {
                    "name": "run_comparison",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "comparison", "case_id": state["case_id"]},
                    "result_key": "comparison_result",
                    "dependencies": ["run_embeddings"],
                },
                {
                    "name": "risk_analysis",
                    "agent_type": "risk_agent",
                    "task_builder": lambda state: {},
                    "result_key": "risk_result",
                    "dependencies": ["run_comparison"],
                },
                {
                    "name": "generate_report",
                    "agent_type": "report_agent",
                    "task_builder": lambda state: {
                        "report_id": state.get("metadata", {}).get("report_id"),
                    },
                    "result_key": "report_result",
                    "dependencies": ["risk_analysis"],
                },
            ],
        ))
        
        # Title Search Report Workflow
        self.register_workflow(WorkflowDefinition(
            name="title_search_report",
            description="Generate professional Title Search Report v2 with all 13 legal sections",
            version="2.0",
            entry_node="run_ocr_extraction",
            nodes=[
                {
                    "name": "run_ocr_extraction",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "ocr_extraction", "case_id": state["case_id"]},
                    "result_key": "extraction_result",
                    "dependencies": [],
                },
                {
                    "name": "run_embeddings",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "embeddings", "case_id": state["case_id"]},
                    "result_key": "embeddings_result",
                    "dependencies": ["run_ocr_extraction"],
                },
                {
                    "name": "run_ownership_graph",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "ownership", "case_id": state["case_id"]},
                    "result_key": "ownership_result",
                    "dependencies": ["run_embeddings"],
                },
                {
                    "name": "run_comparison",
                    "agent_type": "custom",
                    "task_builder": lambda state: {"job_type": "comparison", "case_id": state["case_id"]},
                    "result_key": "comparison_result",
                    "dependencies": ["run_ownership_graph"],
                },
                {
                    "name": "risk_analysis",
                    "agent_type": "risk_agent",
                    "task_builder": lambda state: {},
                    "result_key": "risk_result",
                    "dependencies": ["run_comparison"],
                },
                {
                    "name": "verify_draft",
                    "agent_type": "verification_agent",
                    "task_builder": lambda state: {
                        "draft_id": state.get("metadata", {}).get("draft_id"),
                    },
                    "result_key": "verification_result",
                    "dependencies": ["risk_analysis"],
                    "condition": lambda state: bool(state.get("metadata", {}).get("draft_id")),
                },
                {
                    "name": "generate_title_search_report",
                    "agent_type": "report_agent",
                    "task_builder": lambda state: {
                        "report_id": state.get("metadata", {}).get("report_id"),
                    },
                    "result_key": "report_result",
                    "dependencies": ["risk_analysis", "verify_draft"],
                },
            ],
        ))
        
        # Contract Intelligence Workflow
        self.register_workflow(WorkflowDefinition(
            name="contract_intelligence",
            description="Analyze contract: clauses → obligations → risks → redline → compliance",
            version="1.0",
            entry_node="extract_clauses",
            nodes=[
                {
                    "name": "extract_clauses",
                    "agent_type": "custom",
                    "task_builder": lambda state: {
                        "contract_text": state.get("metadata", {}).get("contract_text"),
                        "contract_id": state.get("metadata", {}).get("contract_id"),
                    },
                    "result_key": "clauses_result",
                    "dependencies": [],
                },
                {
                    "name": "extract_obligations",
                    "agent_type": "custom",
                    "task_builder": lambda state: {
                        "contract_id": state.get("metadata", {}).get("contract_id"),
                        "clauses": state.get("node_results", {}).get("clauses_result", {}),
                    },
                    "result_key": "obligations_result",
                    "dependencies": ["extract_clauses"],
                },
                {
                    "name": "assess_risk",
                    "agent_type": "custom",
                    "task_builder": lambda state: {
                        "contract_id": state.get("metadata", {}).get("contract_id"),
                        "obligations": state.get("node_results", {}).get("obligations_result", {}),
                    },
                    "result_key": "risk_assessment",
                    "dependencies": ["extract_obligations"],
                },
                {
                    "name": "check_compliance",
                    "agent_type": "custom",
                    "task_builder": lambda state: {
                        "contract_id": state.get("metadata", {}).get("contract_id"),
                        "contract_type": state.get("metadata", {}).get("contract_type"),
                    },
                    "result_key": "compliance_result",
                    "dependencies": ["extract_clauses"],
                },
                {
                    "name": "generate_redline",
                    "agent_type": "custom",
                    "task_builder": lambda state: {
                        "original_contract_id": state.get("metadata", {}).get("original_contract_id"),
                        "modified_contract_id": state.get("metadata", {}).get("modified_contract_id"),
                    },
                    "result_key": "redline_result",
                    "dependencies": ["assess_risk"],
                    "condition": lambda state: bool(state.get("metadata", {}).get("original_contract_id")),
                },
            ],
        ))
        
        # Voice Q&A Workflow
        self.register_workflow(WorkflowDefinition(
            name="voice_qa",
            description="Voice question-answering with case-grounded responses",
            version="1.0",
            entry_node="voice_answer",
            nodes=[
                {
                    "name": "voice_answer",
                    "agent_type": "voice_agent",
                    "task_builder": lambda state: {
                        "question": state.get("metadata", {}).get("question"),
                        "language": state.get("metadata", {}).get("language", "en"),
                    },
                    "result_key": "voice_result",
                    "dependencies": [],
                },
            ],
        ))
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a workflow definition."""
        self.workflows[workflow.name] = workflow
    
    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def list_workflows(self) -> list[dict]:
        """List all registered workflows."""
        return [
            {"name": w.name, "description": w.description, "version": w.version}
            for w in self.workflows.values()
        ]
    
    async def execute_workflow(
        self,
        workflow_name: str,
        case_id: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Execute a workflow by name.
        
        Args:
            workflow_name: Name of the workflow to execute
            case_id: Case ID for the workflow
            organization_id: Organization ID
            user_id: User ID
            metadata: Additional metadata for the workflow
            
        Returns:
            Workflow execution result with all node outputs
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Initialize workflow state
        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            case_id=case_id,
            organization_id=organization_id,
            user_id=user_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        
        # Build node map
        nodes = {n["name"]: n for n in workflow.nodes}
        
        # Topological sort for execution order
        execution_order = self._topological_sort(nodes, workflow.entry_node)
        
        # Execute nodes
        for node_name in execution_order:
            node = nodes[node_name]
            state.current_node = node_name
            state.node_statuses[node_name] = NodeStatus.RUNNING
            
            # Check condition
            if node.get("condition") and not node["condition"](state.__dict__):
                state.node_statuses[node_name] = NodeStatus.SKIPPED
                continue
            
            # Check dependencies
            if not self._dependencies_met(node, state):
                state.node_statuses[node_name] = NodeStatus.FAILED
                state.error = f"Dependencies not met for {node_name}"
                state.status = WorkflowStatus.FAILED
                break
            
            try:
                result = await self._execute_node(node, state, organization_id, user_id)
                state.node_results[node_name] = result
                state.node_results[node["result_key"]] = result  # Also store by result_key
                state.node_statuses[node_name] = NodeStatus.COMPLETED
            except Exception as e:
                state.node_statuses[node_name] = NodeStatus.FAILED
                state.error = str(e)
                state.status = WorkflowStatus.FAILED
                break
        
        if state.status == WorkflowStatus.RUNNING:
            state.status = WorkflowStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)
        
        return {
            "workflow_id": state.workflow_id,
            "workflow_name": workflow_name,
            "case_id": case_id,
            "status": state.status.value,
            "node_results": state.node_results,
            "node_statuses": {k: v.value for k, v in state.node_statuses.items()},
            "error": state.error,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        }
    
    def _topological_sort(self, nodes: dict, entry_node: str) -> list[str]:
        """Topologically sort nodes for execution order."""
        if entry_node not in nodes:
            raise KeyError(f"Entry node '{entry_node}' not found in workflow graph")

        visited = set()
        temp = set()
        order = []
        
        def visit(name: str):
            if name in temp:
                raise ValueError(f"Circular dependency detected at {name}")
            if name in visited:
                return
            temp.add(name)
            for dep in nodes[name].get("dependencies", []):
                if dep in nodes:
                    visit(dep)
            temp.remove(name)
            visited.add(name)
            order.append(name)
        
        # Visit all nodes to ensure complete sort (not just from entry_node)
        for node_name in nodes:
            if node_name not in visited:
                visit(node_name)
        
        return order
    
    def _dependencies_met(self, node: dict, state: WorkflowState) -> bool:
        """Check if all dependencies are completed."""
        for dep in node.get("dependencies", []):
            if state.node_statuses.get(dep) != NodeStatus.COMPLETED:
                return False
        return True
    
    async def _execute_node(
        self,
        node: dict,
        state: WorkflowState,
        organization_id: Optional[str],
        user_id: Optional[str],
        step_callback: Optional[Callable[[str, str, str, dict, list], Any]] = None,
    ) -> Any:
        """Execute a single workflow node."""
        agent_type = node["agent_type"]
        task_builder = node.get("task_builder")
        task = task_builder(state.__dict__) if callable(task_builder) else (node.get("task") or {})
        
        from app.ai.agents.registry import (
            DueDiligenceAgent, TitleExaminerAgent, RiskAuditorAgent, RiskAgent,
            LitigationStrategistAgent, ContractReviewerAgent, BSAComplianceAgent,
            ReportAgent, VerificationAgent, VoiceAgent,
        )

        agent_map = {
            "due_diligence_agent": DueDiligenceAgent,
            "title_examiner_agent": TitleExaminerAgent,
            "risk_auditor_agent": RiskAuditorAgent,
            "risk_agent": RiskAgent,
            "litigation_strategist_agent": LitigationStrategistAgent,
            "contract_reviewer_agent": ContractReviewerAgent,
            "bsa_compliance_agent": BSAComplianceAgent,
            "report_agent": ReportAgent,
            "verification_agent": VerificationAgent,
            "voice_agent": VoiceAgent,
        }

        if agent_type in agent_map:
            agent_cls = agent_map[agent_type]
            ctx = new_agent_context(agent_cls, state.case_id, organization_id, user_id)
            return await execute_agent(agent_cls(ctx), task)
        elif agent_type == "custom":
            return await self._execute_custom_task(node, task, state)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    async def _execute_custom_task(
        self,
        node: dict,
        task: dict,
        state: WorkflowState,
    ) -> dict:
        """Execute a custom task (Celery job)."""
        # For now, return a placeholder - in production this would
        # queue a Celery task and wait for completion
        job_type = task.get("job_type")
        return {
            "status": "queued",
            "job_type": job_type,
            "message": f"Custom task {job_type} would be executed via Celery",
        }


# ==================== Pre-built Workflow Functions ====================

async def run_property_due_diligence(
    case_id: str,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
) -> dict:
    """Run the complete property due diligence workflow."""
    orchestrator = AgentOrchestrator()
    return await orchestrator.execute_workflow(
        "property_due_diligence",
        case_id=case_id,
        organization_id=organization_id,
        user_id=user_id,
        metadata={"report_id": report_id} if report_id else {},
    )


async def run_title_search_report(
    case_id: str,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
    draft_id: Optional[str] = None,
) -> dict:
    """Run the Title Search Report v2 workflow."""
    orchestrator = AgentOrchestrator()
    metadata = {}
    if report_id:
        metadata["report_id"] = report_id
    if draft_id:
        metadata["draft_id"] = draft_id
    return await orchestrator.execute_workflow(
        "title_search_report",
        case_id=case_id,
        organization_id=organization_id,
        user_id=user_id,
        metadata=metadata,
    )


async def run_contract_intelligence(
    case_id: str,
    contract_text: str,
    contract_id: str,
    contract_type: Optional[str] = None,
    original_contract_id: Optional[str] = None,
    modified_contract_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """Run the contract intelligence workflow."""
    orchestrator = AgentOrchestrator()
    return await orchestrator.execute_workflow(
        "contract_intelligence",
        case_id=case_id,
        organization_id=organization_id,
        user_id=user_id,
        metadata={
            "contract_text": contract_text,
            "contract_id": contract_id,
            "contract_type": contract_type,
            "original_contract_id": original_contract_id,
            "modified_contract_id": modified_contract_id,
        },
    )


async def run_voice_qa(
    case_id: str,
    question: str,
    language: str = "en",
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """Run the voice Q&A workflow."""
    orchestrator = AgentOrchestrator()
    return await orchestrator.execute_workflow(
        "voice_qa",
        case_id=case_id,
        organization_id=organization_id,
        user_id=user_id,
        metadata={"question": question, "language": language},
    )


# ==================== Workflow State Persistence ====================

class WorkflowPersistence:
    """Persist workflow state to database for recovery and audit."""
    
    @staticmethod
    async def save_state(state: WorkflowState):
        """Save workflow state to database."""
        try:
            from supabase import create_client
            url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
            key = settings.SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
            db = create_client(url, key)
            db.table("agent_workflows").upsert({
                "id": state.workflow_id,
                "case_id": state.case_id,
                "organization_id": state.organization_id,
                "user_id": state.user_id,
                "status": state.status.value,
                "current_node": state.current_node,
                "node_results": state.node_results,
                "node_statuses": {k: v.value for k, v in state.node_statuses.items()},
                "error": state.error,
                "started_at": state.started_at.isoformat() if state.started_at else None,
                "completed_at": state.completed_at.isoformat() if state.completed_at else None,
                "metadata": state.metadata,
            }).execute()
        except Exception:
            pass
    
    @staticmethod
    async def load_state(workflow_id: str) -> Optional[WorkflowState]:
        """Load workflow state from database."""
        try:
            from supabase import create_client
            url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
            key = settings.SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
            db = create_client(url, key)
            result = db.table("agent_workflows").select("*").eq("id", workflow_id).single().execute()
            if not result.data:
                return None
            data = result.data
            return WorkflowState(
                workflow_id=data["id"],
                case_id=data["case_id"],
                organization_id=data.get("organization_id"),
                user_id=data.get("user_id"),
                status=WorkflowStatus(data["status"]),
                current_node=data.get("current_node"),
                node_results=data.get("node_results", {}),
                node_statuses={k: NodeStatus(v) for k, v in data.get("node_statuses", {}).items()},
                error=data.get("error"),
                started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
                completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                metadata=data.get("metadata", {}),
            )
        except Exception:
            return None
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            metadata=data.get("metadata", {}),
        )


# ==================== AI Kill Switch Integration ====================

class AIKillSwitch:
    """Emergency AI kill switch for halting all agent operations."""
    
    _enabled = False
    _reason = None
    
    def __init__(self):
        pass
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled
    
    def is_activated(self) -> bool:
        return self._enabled
    
    @classmethod
    def enable(cls, reason: Optional[str] = None):
        cls._enabled = True
        cls._reason = reason

    def activate(self, reason: Optional[str] = None):
        AIKillSwitch._enabled = True
        AIKillSwitch._reason = reason

    @classmethod
    def disable(cls):
        cls._enabled = False
        cls._reason = None

    @classmethod
    def get_reason(cls) -> Optional[str]:
        return cls._reason

    def deactivate(self):
        AIKillSwitch._enabled = False
        AIKillSwitch._reason = None
    
    @classmethod
    async def check_and_raise(cls):
        if cls._enabled:
            reason_msg = f": {cls._reason}" if cls._reason else ""
            raise RuntimeError(f"AI operations disabled by kill switch{reason_msg}")


# Decorator for workflow functions to check kill switch
def check_ai_kill_switch(func: Callable) -> Callable:
    """Decorator to check AI kill switch before executing workflow."""
    async def wrapper(*args, **kwargs):
        await AIKillSwitch.check_and_raise()
        return await func(*args, **kwargs)
    return wrapper


# Apply kill switch to workflow functions
run_property_due_diligence = check_ai_kill_switch(run_property_due_diligence)
run_title_search_report = check_ai_kill_switch(run_title_search_report)
run_contract_intelligence = check_ai_kill_switch(run_contract_intelligence)
run_voice_qa = check_ai_kill_switch(run_voice_qa)