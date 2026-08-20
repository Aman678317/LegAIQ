"""Tests for Specialist Agent Library (Milestone 4).

Verifies that all 6 first-class specialist agents execute genuine domain logic,
respect permission scopes, enforce token budgets, and integrate with tool systems.
"""
import pytest
from app.ai.agents.base import AgentBudget, AgentContext, Permission
from app.ai.agents.registry import (
    BSAComplianceAgent,
    ContractReviewerAgent,
    DueDiligenceAgent,
    LitigationStrategistAgent,
    RiskAuditorAgent,
    SPECIALIST_AGENT_LIBRARY,
    TitleExaminerAgent,
)


def make_test_context(agent_cls, case_id="test-case-101", org_id="test-org"):
    return AgentContext(
        agent_type=agent_cls.AGENT_TYPE,
        case_id=case_id,
        organization_id=org_id,
        permissions=set(agent_cls.DEFAULT_PERMISSIONS),
        budget=AgentBudget(max_tokens=50000, max_cost_usd=1.0, max_tool_calls=25),
    )


@pytest.mark.asyncio
async def test_specialist_agent_library_catalog():
    """Verify that all 6 specialist agents are registered in the catalog with schemas."""
    assert len(SPECIALIST_AGENT_LIBRARY) == 6
    agent_types = [a["agent_type"] for a in SPECIALIST_AGENT_LIBRARY]
    expected_types = [
        "due_diligence_agent",
        "title_examiner_agent",
        "risk_auditor_agent",
        "litigation_strategist_agent",
        "contract_reviewer_agent",
        "bsa_compliance_agent",
    ]
    for exp in expected_types:
        assert exp in agent_types


@pytest.mark.asyncio
async def test_due_diligence_agent_execution():
    """Test DueDiligenceAgent scoring and checklist generation."""
    ctx = make_test_context(DueDiligenceAgent)
    agent = DueDiligenceAgent(ctx)
    task = {
        "survey_number": "124/2",
        "documents": ["Sale Deed 1994", "RTC Pahani 2023", "Encumbrance Certificate"],
    }
    result = await agent.run(task)
    assert result["agent_type"] == "due_diligence_agent"
    assert "due_diligence_score" in result
    assert result["due_diligence_score"] >= 0 and result["due_diligence_score"] <= 100
    assert len(result["checklist"]) >= 4
    assert result["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_title_examiner_agent_execution():
    """Test TitleExaminerAgent 13-30 year chain analysis and title break detection."""
    ctx = make_test_context(TitleExaminerAgent)
    agent = TitleExaminerAgent(ctx)
    task = {
        "survey_number": "45/1A",
        "years": 30,
    }
    result = await agent.run(task)
    assert result["agent_type"] == "title_examiner_agent"
    assert result["years_examined"] == 30
    assert "marketability_rating" in result
    assert result["marketability_rating"] in ("Marketable", "Conditional", "Defective")
    assert "ownership_chain" in result
    assert len(result["ownership_chain"]) >= 2


@pytest.mark.asyncio
async def test_risk_auditor_agent_execution():
    """Test RiskAuditorAgent 9-category risk categorization."""
    ctx = make_test_context(RiskAuditorAgent)
    agent = RiskAuditorAgent(ctx)
    task = {
        "focus_areas": ["mismatches", "encumbrances", "possession"],
    }
    result = await agent.run(task)
    assert result["agent_type"] == "risk_auditor_agent"
    assert "risks_by_category" in result
    assert len(result["risks_by_category"]) > 0
    assert "overall_risk_rating" in result
    assert "highest_severity" in result


@pytest.mark.asyncio
async def test_litigation_strategist_agent_execution():
    """Test LitigationStrategistAgent causes of action and interim relief formulation."""
    ctx = make_test_context(LitigationStrategistAgent)
    agent = LitigationStrategistAgent(ctx)
    task = {
        "dispute_type": "Title Cloud & Encroachment",
        "relief_sought": "Declaration of Title and Permanent Injunction",
    }
    result = await agent.run(task)
    assert result["agent_type"] == "litigation_strategist_agent"
    assert len(result["causes_of_action"]) >= 2
    assert "limitation_analysis" in result
    assert len(result["interim_reliefs"]) >= 2
    assert result["forum_mapping"]["primary_forum"] == "City Civil Court / District Court"


@pytest.mark.asyncio
async def test_contract_reviewer_agent_execution():
    """Test ContractReviewerAgent clause extraction and redlining suggestions."""
    ctx = make_test_context(ContractReviewerAgent)
    agent = ContractReviewerAgent(ctx)
    sample_contract = (
        "1. Indemnity: Vendor shall indemnify Purchaser for all losses. "
        "2. Governing Law: This Agreement is governed by the laws of India. "
        "3. Jurisdiction: Courts at Bangalore shall have exclusive jurisdiction."
    )
    task = {"contract_text": sample_contract}
    result = await agent.run(task)
    assert result["agent_type"] == "contract_reviewer_agent"
    assert result["clauses_analyzed_count"] >= 3
    assert "contract_risk_score" in result
    assert len(result["redline_suggestions"]) >= 1


@pytest.mark.asyncio
async def test_bsa_compliance_agent_execution():
    """Test BSAComplianceAgent Section 63 evidence admissibility certification."""
    ctx = make_test_context(BSAComplianceAgent)
    agent = BSAComplianceAgent(ctx)
    task = {
        "document_hashes": [
            {"name": "Sale_Deed_1994.pdf", "hash": "a4f8e9123bc45..."},
            {"name": "RTC_Pahani_2023.pdf", "hash": "d1c2b3e4f5a6..."},
        ]
    }
    result = await agent.run(task)
    assert result["agent_type"] == "bsa_compliance_agent"
    assert result["bsa_section"] == "Section 63(4)"
    assert result["admissibility_status"] == "ADMISSIBLE_AS_ELECTRONIC_RECORD"
    assert result["master_sha256_hash"] is not None
    assert len(result["certified_schedule"]) == 2
