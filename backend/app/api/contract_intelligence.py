"""Contract Intelligence API Endpoints.

Provides clause-level extraction, risk scoring, redlining comparison,
and obligation tracking.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.security.auth import get_case_access
from app.ai.contract_intelligence import (
    ContractIntelligenceEngine,
    ContractDocument,
    ContractClause,
    ContractObligation,
    ContractRiskAssessment,
)

router = APIRouter(tags=["contract-intelligence"])
engine = ContractIntelligenceEngine()


class ContractAnalyzeRequest(BaseModel):
    contract_id: Optional[str] = "contract-001"
    title: str = "Legal Contract"
    full_text: str


class ContractRedlineRequest(BaseModel):
    original_text: str
    modified_text: str
    original_title: Optional[str] = "Original Contract"
    modified_title: Optional[str] = "Modified Contract"


@router.post("/cases/{case_id}/contracts/analyze")
async def analyze_contract(case_id: str, body: ContractAnalyzeRequest, _=Depends(get_case_access)):
    """Extract clauses, assess risks, and track obligations from contract text."""
    doc = ContractDocument(
        contract_id=body.contract_id or "contract-001",
        title=body.title,
        full_text=body.full_text,
    )
    
    # 1. Extract clauses
    clauses = engine.extract_clauses(body.full_text, contract_id=doc.contract_id)
    doc.clauses = clauses
    
    # 2. Extract obligations
    obligations = engine.extract_obligations(doc)
    
    # 3. Assess risk
    risk_assessment = engine.assess_risk(doc)
    
    return {
        "case_id": case_id,
        "contract_id": doc.contract_id,
        "title": doc.title,
        "clause_count": len(clauses),
        "clauses": [
            {
                "clause_id": c.clause_id,
                "clause_type": c.clause_type.value,
                "title": c.title,
                "content": c.content,
                "risk_level": c.risk_level.value,
                "risk_factors": c.risk_factors,
            }
            for c in clauses
        ],
        "obligations": [
            {
                "obligation_id": o.obligation_id,
                "type": o.obligation_type.value,
                "description": o.description,
                "responsible_party": o.responsible_party,
                "beneficiary_party": o.beneficiary_party,
                "due_date": o.due_date.isoformat() if o.due_date else None,
                "clause_ref": o.clause_ref,
            }
            for o in obligations
        ],
        "risk_assessment": {
            "overall_risk": risk_assessment.overall_risk.value,
            "risk_score": risk_assessment.risk_score,
            "critical_issues": risk_assessment.critical_issues,
            "high_risk_issues": risk_assessment.high_risk_issues,
            "recommendations": risk_assessment.recommendations,
            "compliance_gaps": risk_assessment.compliance_gaps,
        },
    }


@router.post("/cases/{case_id}/contracts/redline")
async def redline_comparison(case_id: str, body: ContractRedlineRequest, _=Depends(get_case_access)):
    """Compare two contract versions and generate redline changes."""
    orig_doc = ContractDocument(
        contract_id="ORIG-001",
        title=body.original_title or "Original",
        full_text=body.original_text,
    )
    orig_doc.clauses = engine.extract_clauses(body.original_text, contract_id="ORIG-001")
    
    mod_doc = ContractDocument(
        contract_id="MOD-001",
        title=body.modified_title or "Modified",
        full_text=body.modified_text,
    )
    mod_doc.clauses = engine.extract_clauses(body.modified_text, contract_id="MOD-001")
    
    changes = engine.compare_contracts(orig_doc, mod_doc)
    summary_doc = engine.generate_redline_document(orig_doc, mod_doc, changes)
    
    return {
        "case_id": case_id,
        "total_changes": len(changes),
        "changes": [
            {
                "change_id": c.change_id,
                "change_type": c.change_type,
                "clause_id": c.clause_id,
                "original_text": c.original_text,
                "modified_text": c.modified_text,
            }
            for c in changes
        ],
        "summary": summary_doc,
    }
