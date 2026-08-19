"""Tests for Agent Orchestration v2 (LangGraph-based multi-agent workflows)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.agents.orchestration import (
    AgentOrchestrator,
    WorkflowState,
    WorkflowStatus,
    NodeStatus,
    WorkflowPersistence,
    AIKillSwitch,
    run_property_due_diligence,
    run_title_search_report,
    run_contract_intelligence,
    run_voice_qa,
)
from supabase import create_client


class TestAgentOrchestrator:
    """Test the agent orchestrator."""

    def setup_method(self):
        self.orchestrator = AgentOrchestrator()

    def test_register_builtin_workflows(self):
        """Test that built-in workflows are registered."""
        workflows = self.orchestrator.list_workflows()
        workflow_names = {w["name"] for w in workflows}
        
        assert "property_due_diligence" in workflow_names
        assert "title_search_report" in workflow_names
        assert "contract_intelligence" in workflow_names
        assert "voice_qa" in workflow_names

    def test_get_workflow(self):
        """Test getting a workflow by name."""
        workflow = self.orchestrator.get_workflow("property_due_diligence")
        assert workflow is not None
        assert workflow.name == "property_due_diligence"
        assert len(workflow.nodes) >= 4

    def test_get_nonexistent_workflow(self):
        """Test getting a non-existent workflow returns None."""
        workflow = self.orchestrator.get_workflow("nonexistent")
        assert workflow is None

    def test_topological_sort(self):
        """Test topological sorting of workflow nodes."""
        nodes = {
            "a": {"name": "a", "dependencies": []},
            "b": {"name": "b", "dependencies": ["a"]},
            "c": {"name": "c", "dependencies": ["b"]},
        }
        order = self.orchestrator._topological_sort(nodes, "a")
        assert order == ["a", "b", "c"]

    def test_topological_sort_with_branching(self):
        """Test topological sorting with branching dependencies."""
        nodes = {
            "a": {"name": "a", "dependencies": []},
            "b": {"name": "b", "dependencies": ["a"]},
            "c": {"name": "c", "dependencies": ["a"]},
            "d": {"name": "d", "dependencies": ["b", "c"]},
        }
        order = self.orchestrator._topological_sort(nodes, "a")
        assert order[0] == "a"
        assert order[-1] == "d"
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_topological_sort_circular_dependency(self):
        """Test that circular dependencies raise an error."""
        nodes = {
            "a": {"name": "a", "dependencies": ["b"]},
            "b": {"name": "b", "dependencies": ["a"]},
        }
        with pytest.raises(ValueError, match="Circular dependency"):
            self.orchestrator._topological_sort(nodes, "a")

    def test_dependencies_met(self):
        """Test dependency checking."""
        state = WorkflowState(
            workflow_id="test",
            case_id="case-1",
            node_statuses={
                "a": NodeStatus.COMPLETED,
                "b": NodeStatus.PENDING,
            }
        )
        node = {"name": "c", "dependencies": ["a", "b"]}
        assert not self.orchestrator._dependencies_met(node, state)
        
        state.node_statuses["b"] = NodeStatus.COMPLETED
        assert self.orchestrator._dependencies_met(node, state)

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self):
        """Test successful workflow execution."""
        with patch.object(self.orchestrator, '_execute_node', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "completed", "result": "ok"}
            
            result = await self.orchestrator.execute_workflow(
                "property_due_diligence",
                case_id="case-123",
                organization_id="org-123",
            )
            
            assert result["status"] == "completed"
            assert result["case_id"] == "case-123"
            assert "node_results" in result
            assert "node_statuses" in result

    @pytest.mark.asyncio
    async def test_execute_workflow_unknown(self):
        """Test executing unknown workflow raises error."""
        with pytest.raises(ValueError, match="not found"):
            await self.orchestrator.execute_workflow(
                "unknown_workflow",
                case_id="case-123",
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_with_condition(self):
        """Test workflow skips nodes when condition is false."""
        workflow = self.orchestrator.get_workflow("title_search_report")
        verify_node = next(n for n in workflow.nodes if n["name"] == "verify_draft")
        
        # Create state without draft_id
        state = WorkflowState(
            workflow_id="test",
            case_id="case-1",
            metadata={},  # No draft_id
        )
        
        # Condition should return False
        assert verify_node["condition"](state.__dict__) is False
        
        # Create state with draft_id
        state.metadata["draft_id"] = "draft-123"
        assert verify_node["condition"](state.__dict__) is True

    @pytest.mark.asyncio
    async def test_execute_workflow_dependency_failure(self):
        """Test workflow fails when a node fails."""
        with patch.object(self.orchestrator, '_execute_node', new_callable=AsyncMock) as mock_exec:
            # First call succeeds, second fails
            mock_exec.side_effect = [
                {"status": "completed"},
                Exception("Node failed"),
            ]
            
            # Use property_due_diligence which has multiple nodes
            result = await self.orchestrator.execute_workflow(
                "property_due_diligence",
                case_id="case-123",
            )
            
            assert result["status"] == "failed"
            assert result["error"] == "Node failed"


class TestWorkflowState:
    """Test WorkflowState dataclass."""

    def test_initial_state(self):
        """Test initial workflow state."""
        state = WorkflowState(
            workflow_id="wf-1",
            case_id="case-1",
        )
        assert state.status == WorkflowStatus.PENDING
        assert state.current_node is None
        assert state.node_results == {}
        assert state.node_statuses == {}
        assert state.error is None

    def test_state_with_metadata(self):
        """Test workflow state with metadata."""
        state = WorkflowState(
            workflow_id="wf-1",
            case_id="case-1",
            metadata={"report_id": "report-1", "draft_id": "draft-1"},
        )
        assert state.metadata["report_id"] == "report-1"
        assert state.metadata["draft_id"] == "draft-1"


class TestWorkflowPersistence:
    """Test workflow state persistence."""

    @pytest.mark.asyncio
    async def test_save_state(self):
        """Test saving workflow state."""
        state = WorkflowState(
            workflow_id="wf-1",
            case_id="case-1",
            status=WorkflowStatus.COMPLETED,
            node_results={"node1": {"result": "ok"}},
            node_statuses={"node1": NodeStatus.COMPLETED},
        )
        
        with patch("supabase.create_client") as mock_create:
            mock_db = MagicMock()
            mock_create.return_value = mock_db
            mock_upsert = MagicMock()
            mock_db.table.return_value.upsert.return_value = mock_upsert
            mock_upsert.execute.return_value = MagicMock()
            
            await WorkflowPersistence.save_state(state)
            
            mock_db.table.assert_called_with("agent_workflows")
            mock_upsert.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_state(self):
        """Test loading workflow state."""
        with patch("supabase.create_client") as mock_create:
            mock_db = MagicMock()
            mock_create.return_value = mock_db
            mock_select = MagicMock()
            mock_db.table.return_value.select.return_value = mock_select
            mock_single = MagicMock()
            mock_select.eq.return_value.single.return_value = mock_single
            mock_single.execute.return_value = MagicMock(data={
                "id": "wf-1",
                "case_id": "case-1",
                "status": "completed",
                "node_results": {"node1": {"result": "ok"}},
                "node_statuses": {"node1": "completed"},
                "started_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T01:00:00",
            })
            
            state = await WorkflowPersistence.load_state("wf-1")
            
            assert state is not None
            assert state.workflow_id == "wf-1"
            assert state.case_id == "case-1"
            assert state.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_load_state_not_found(self):
        """Test loading non-existent workflow state."""
        with patch("supabase.create_client") as mock_create:
            mock_db = MagicMock()
            mock_create.return_value = mock_db
            mock_select = MagicMock()
            mock_db.table.return_value.select.return_value = mock_select
            mock_single = MagicMock()
            mock_select.eq.return_value.single.return_value = mock_single
            mock_single.execute.return_value = MagicMock(data=None)
            
            state = await WorkflowPersistence.load_state("nonexistent")
            
            assert state is None


class TestAIKillSwitch:
    """Test AI Kill Switch."""

    def test_initial_state(self):
        """Test initial kill switch state."""
        AIKillSwitch.disable()
        assert AIKillSwitch.is_enabled() is False

    def test_enable_disable(self):
        """Test enabling and disabling kill switch."""
        AIKillSwitch.enable()
        assert AIKillSwitch.is_enabled() is True
        
        AIKillSwitch.disable()
        assert AIKillSwitch.is_enabled() is False

    @pytest.mark.asyncio
    async def test_check_and_raise_enabled(self):
        """Test kill switch raises when enabled."""
        AIKillSwitch.enable()
        with pytest.raises(RuntimeError, match="AI operations disabled"):
            await AIKillSwitch.check_and_raise()
        AIKillSwitch.disable()

    @pytest.mark.asyncio
    async def test_check_and_raise_disabled(self):
        """Test kill switch doesn't raise when disabled."""
        AIKillSwitch.disable()
        # Should not raise
        await AIKillSwitch.check_and_raise()


class TestBuiltinWorkflowFunctions:
    """Test the pre-built workflow functions."""

    @pytest.mark.asyncio
    async def test_run_property_due_diligence(self):
        """Test property due diligence workflow function."""
        with patch("app.ai.agents.orchestration.AgentOrchestrator.execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "completed", "workflow_id": "wf-1"}
            
            result = await run_property_due_diligence(
                case_id="case-123",
                organization_id="org-123",
                report_id="report-123",
            )
            
            assert result["status"] == "completed"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_title_search_report(self):
        """Test title search report workflow function."""
        with patch("app.ai.agents.orchestration.AgentOrchestrator.execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "completed", "workflow_id": "wf-1"}
            
            result = await run_title_search_report(
                case_id="case-123",
                organization_id="org-123",
                report_id="report-123",
                draft_id="draft-123",
            )
            
            assert result["status"] == "completed"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_contract_intelligence(self):
        """Test contract intelligence workflow function."""
        with patch("app.ai.agents.orchestration.AgentOrchestrator.execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "completed", "workflow_id": "wf-1"}
            
            result = await run_contract_intelligence(
                case_id="case-123",
                contract_text="Sample contract text",
                contract_id="ctr-123",
                contract_type="service",
            )
            
            assert result["status"] == "completed"
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_voice_qa(self):
        """Test voice Q&A workflow function."""
        with patch("app.ai.agents.orchestration.AgentOrchestrator.execute_workflow", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "completed", "workflow_id": "wf-1"}
            
            result = await run_voice_qa(
                case_id="case-123",
                question="What is the survey number?",
                language="en",
            )
            
            assert result["status"] == "completed"
            mock_exec.assert_called_once()


class TestWorkflowIntegration:
    """Integration tests for workflows."""

    @pytest.mark.asyncio
    async def test_property_due_diligence_workflow_structure(self):
        """Test property due diligence workflow has correct structure."""
        orchestrator = AgentOrchestrator()
        workflow = orchestrator.get_workflow("property_due_diligence")
        
        assert workflow is not None
        node_names = {n["name"] for n in workflow.nodes}
        assert "run_ocr_extraction" in node_names
        assert "run_embeddings" in node_names
        assert "run_comparison" in node_names
        assert "risk_analysis" in node_names
        assert "generate_report" in node_names

    @pytest.mark.asyncio
    async def test_title_search_report_workflow_structure(self):
        """Test title search report workflow has correct structure."""
        orchestrator = AgentOrchestrator()
        workflow = orchestrator.get_workflow("title_search_report")
        
        assert workflow is not None
        node_names = {n["name"] for n in workflow.nodes}
        assert "run_ocr_extraction" in node_names
        assert "run_embeddings" in node_names
        assert "run_ownership_graph" in node_names
        assert "run_comparison" in node_names
        assert "risk_analysis" in node_names
        assert "verify_draft" in node_names
        assert "generate_title_search_report" in node_names

    @pytest.mark.asyncio
    async def test_contract_intelligence_workflow_structure(self):
        """Test contract intelligence workflow has correct structure."""
        orchestrator = AgentOrchestrator()
        workflow = orchestrator.get_workflow("contract_intelligence")
        
        assert workflow is not None
        node_names = {n["name"] for n in workflow.nodes}
        assert "extract_clauses" in node_names
        assert "extract_obligations" in node_names
        assert "assess_risk" in node_names
        assert "check_compliance" in node_names
        assert "generate_redline" in node_names

    @pytest.mark.asyncio
    async def test_voice_qa_workflow_structure(self):
        """Test voice Q&A workflow has correct structure."""
        orchestrator = AgentOrchestrator()
        workflow = orchestrator.get_workflow("voice_qa")
        
        assert workflow is not None
        node_names = {n["name"] for n in workflow.nodes}
        assert "voice_answer" in node_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])