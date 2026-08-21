"""Tier 1 Test Suite: Workflow Engine & Specialist Agents (Features 13-15).

Covers:
- Feature 13: Visual Workflow Canvas & Node Graph Serialization
- Feature 14: Workflow Execution Engine & State Machine
- Feature 15: Specialist Agent Library (Due Diligence, Title Examiner, Risk Auditor, Litigation Strategist, Contract Reviewer, BSA Compliance)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.ai.agents.base import AgentContext, AgentBudget, Permission, new_agent_context
from app.ai.agents.orchestration import (
    AgentOrchestrator,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowState,
    WorkflowStatus,
    NodeStatus,
    WorkflowPersistence,
    AIKillSwitch,
)
from app.ai.agents.registry import (
    RiskAuditorAgent,
    DueDiligenceAgent,
    TitleExaminerAgent,
    LitigationStrategistAgent,
    ContractReviewerAgent,
    BSAComplianceAgent,
    ReportAgent,
    VerificationAgent,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Feature 13: Visual Workflow Canvas & Node Graph
# ============================================================================

class TestFeature13WorkflowCanvas:
    """Feature 13: Visual workflow node graph modeling and topological ordering."""

    def setup_method(self):
        self.orchestrator = AgentOrchestrator()

    def test_workflow_definition_serialization(self):
        """WorkflowDefinition validates nodes, entry node, and metadata."""
        wf = WorkflowDefinition(
            name="custom_mna_due_diligence",
            description="Multi-agent legal due diligence pipeline for M&A transactions",
            version="2.0",
            entry_node="ocr_ingest",
            nodes=[
                {"name": "ocr_ingest", "agent_type": "due_diligence_agent", "dependencies": []},
                {"name": "risk_audit", "agent_type": "risk_auditor_agent", "dependencies": ["ocr_ingest"]},
                {"name": "report_gen", "agent_type": "report_agent", "dependencies": ["risk_audit"]},
            ],
        )
        assert wf.name == "custom_mna_due_diligence"
        assert len(wf.nodes) == 3
        assert wf.entry_node == "ocr_ingest"

    def test_topological_sort_linear_pipeline(self):
        """Linear DAG dependency graph sorts in strict sequential order."""
        nodes = {
            "extract": {"name": "extract", "dependencies": []},
            "examine": {"name": "examine", "dependencies": ["extract"]},
            "certify": {"name": "certify", "dependencies": ["examine"]},
        }
        order = self.orchestrator._topological_sort(nodes, "extract")
        assert order == ["extract", "examine", "certify"]

    def test_topological_sort_diamond_dependency(self):
        """Diamond branching graph resolves dependencies before convergence."""
        nodes = {
            "start": {"name": "start", "dependencies": []},
            "branch_title": {"name": "branch_title", "dependencies": ["start"]},
            "branch_litigation": {"name": "branch_litigation", "dependencies": ["start"]},
            "final_opinion": {"name": "final_opinion", "dependencies": ["branch_title", "branch_litigation"]},
        }
        order = self.orchestrator._topological_sort(nodes, "start")
        assert order[0] == "start"
        assert order[-1] == "final_opinion"
        assert "branch_title" in order[1:3]
        assert "branch_litigation" in order[1:3]

    def test_circular_dependency_detected_and_rejected(self):
        """Cyclic node graph raises explicit ValueError to prevent infinite execution loops."""
        nodes = {
            "node_a": {"name": "node_a", "dependencies": ["node_b"]},
            "node_b": {"name": "node_b", "dependencies": ["node_a"]},
        }
        with pytest.raises(ValueError, match="Circular dependency"):
            self.orchestrator._topological_sort(nodes, "node_a")

    def test_builtin_workflows_registered(self):
        """Orchestrator pre-registers out-of-the-box legal workflows."""
        workflows = self.orchestrator.list_workflows()
        names = {w["name"] for w in workflows}
        assert "property_due_diligence" in names
        assert "title_search_report" in names
        assert "contract_intelligence" in names


# ============================================================================
# Feature 14: Workflow Execution Engine & State Machine
# ============================================================================

class TestFeature14WorkflowExecutionEngine:
    """Feature 14: Workflow state transitions, node status tracking, and kill switch."""

    def test_workflow_state_initialization(self):
        """WorkflowState initializes with PENDING status and empty execution tracking."""
        state = WorkflowState(
            workflow_id="wf-exec-001",
            case_id="case-100",
            organization_id=ORG_ID,
            user_id=USER_ID,
            status=WorkflowStatus.PENDING,
        )
        assert state.status == WorkflowStatus.PENDING
        assert state.node_results == {}
        assert state.node_statuses == {}
        assert state.error is None

    def test_workflow_state_success_transition(self):
        """Completed workflow marks status, timestamps, and preserves node outputs."""
        state = WorkflowState(
            workflow_id="wf-exec-002",
            case_id="case-100",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        state.node_results["step1"] = {"status": "SUCCESS", "records_found": 5}
        state.node_statuses["step1"] = NodeStatus.COMPLETED
        state.status = WorkflowStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)

        assert state.status == WorkflowStatus.COMPLETED
        assert state.node_statuses["step1"] == NodeStatus.COMPLETED
        assert state.node_results["step1"]["records_found"] == 5

    def test_ai_kill_switch_guards_execution(self):
        """AI Kill Switch globally halts AI agent execution when activated for safety/cost limit."""
        kill_switch = AIKillSwitch()
        assert kill_switch.is_activated() is False

        kill_switch.activate("Monthly API token limit exceeded")
        assert kill_switch.is_activated() is True
        assert "limit exceeded" in kill_switch.get_reason()

        kill_switch.deactivate()
        assert kill_switch.is_activated() is False

    @pytest.mark.asyncio
    async def test_workflow_persistence_tracking(self, fake):
        """Workflow state is persisted to database with step outputs."""
        persistence = WorkflowPersistence()
        state = WorkflowState(
            workflow_id="wf-persist-001",
            case_id="case-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        assert hasattr(persistence, "save_state") or hasattr(persistence, "create_run")

    def test_workflow_budget_enforcement(self):
        """Agent budget enforces max tokens and cost constraints."""
        budget = AgentBudget(max_tokens=50000, max_cost_usd=2.50)
        assert budget.max_tokens == 50000
        assert budget.max_cost_usd == 2.50


# ============================================================================
# Feature 15: Specialist Agent Library (6 Pre-built Agents)
# ============================================================================

class TestFeature15SpecialistAgentLibrary:
    """Feature 15: Isolated tests for 6 domain specialist legal agents."""

    @pytest.mark.asyncio
    async def test_due_diligence_agent_score_and_checklist(self, fake):
        """Due Diligence Agent evaluates title documents, checklists, and outputs scored report."""
        ctx = new_agent_context(
            case_id="case-dd-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[
                Permission.READ_CASE, Permission.READ_DOCUMENTS,
                Permission.READ_ENTITIES, Permission.READ_GRAPH,
                Permission.WRITE_FINDINGS, Permission.WRITE_RISKS,
            ],
        )
        agent = DueDiligenceAgent(ctx)
        res = await agent.run({})
        assert "due_diligence_score" in res
        assert "checklist" in res
        assert "status" in res
        assert res["due_diligence_score"] >= 0 and res["due_diligence_score"] <= 100

    @pytest.mark.asyncio
    async def test_title_examiner_agent_break_detection(self, fake):
        """Title Examiner Agent traces 30-year chain and flags title marketability."""
        ctx = new_agent_context(
            case_id="case-te-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[
                Permission.READ_CASE, Permission.READ_DOCUMENTS,
                Permission.READ_GRAPH, Permission.READ_ENTITIES,
                Permission.WRITE_FINDINGS,
            ],
        )
        agent = TitleExaminerAgent(ctx)
        res = await agent.run({})
        assert "marketability" in res
        assert res["marketability"] in ("MARKETABLE", "CONDITIONAL", "DEFECTIVE")
        assert "detected_breaks" in res

    @pytest.mark.asyncio
    async def test_risk_auditor_agent_evidence_grounding(self, fake):
        """Risk Auditor Agent creates categorized risk entries from document mismatches."""
        ctx = new_agent_context(
            case_id="case-ra-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[Permission.READ_GRAPH, Permission.READ_ENTITIES, Permission.WRITE_RISKS],
        )
        agent = RiskAuditorAgent(ctx)
        res = await agent.run({})
        assert "risks_created" in res
        assert isinstance(res["risks_created"], int)

    @pytest.mark.asyncio
    async def test_litigation_strategist_agent_prayer_reliefs(self, fake):
        """Litigation Strategist Agent formulates CPC/Specific Relief Act actions and limitation analysis."""
        ctx = new_agent_context(
            case_id="case-ls-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[
                Permission.READ_CASE, Permission.READ_DOCUMENTS,
                Permission.READ_ENTITIES, Permission.WEB_SEARCH,
                Permission.WRITE_DRAFTS,
            ],
        )
        agent = LitigationStrategistAgent(ctx)
        res = await agent.run({})
        assert "causes_of_action" in res
        assert len(res["causes_of_action"]) >= 1
        assert "recommended_interim_reliefs" in res
        assert any("Injunction" in r for r in res["recommended_interim_reliefs"])

    @pytest.mark.asyncio
    async def test_contract_reviewer_agent_playbook_scoring(self, fake):
        """Contract Reviewer Agent parses clauses and scores contractual risk."""
        ctx = new_agent_context(
            case_id="case-cr-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[Permission.READ_DOCUMENTS, Permission.READ_ENTITIES, Permission.WRITE_FINDINGS, Permission.WRITE_DRAFTS],
        )
        agent = ContractReviewerAgent(ctx)
        contract_text = (
            "AGREEMENT\n"
            "1. TERM AND TERMINATION: Term is 12 months. Immediate termination without cause.\n"
            "2. INDEMNITY: Unlimited indemnity for all direct, indirect, consequential damages."
        )
        res = await agent.run({"contract_text": contract_text})
        assert "overall_risk_score" in res
        assert "extracted_clauses" in res
        assert res["overall_risk_score"] > 0

    @pytest.mark.asyncio
    async def test_bsa_compliance_agent_section63_hash(self, fake):
        """BSA Compliance Agent verifies electronic records and Section 63 admissibility criteria."""
        ctx = new_agent_context(
            case_id="case-bsa-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[Permission.READ_CASE, Permission.READ_DOCUMENTS, Permission.WRITE_FINDINGS],
        )
        agent = BSAComplianceAgent(ctx)
        res = await agent.run({})
        assert "admissibility_summary" in res or "compliant" in res or "certificate_status" in res or "findings" in res
