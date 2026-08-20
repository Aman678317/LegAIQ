"""Contract Intelligence, Clause Library & Playbooks API Endpoints.

Provides 29+ clause extraction, 0-100 risk scoring, risk heatmaps,
Enterprise Clause Library management, and Firm Playbook deviation evaluation.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.security.auth import AuthContext, get_auth_context, get_case_access, require_role
from app.ai.contract_intelligence import (
    ContractIntelligenceEngine,
    ContractDocument,
    ContractClause,
    ContractObligation,
    ContractRiskAssessment,
)
from app.ai.clause_library import EnterpriseClauseLibrary, ClauseLibraryItem
from app.ai.playbooks import (
    PlaybookDeviationEngine,
    ContractPlaybook,
    PlaybookRule,
)

router = APIRouter(tags=["contract-intelligence"])
engine = ContractIntelligenceEngine()
clause_library = EnterpriseClauseLibrary()
playbook_engine = PlaybookDeviationEngine(clause_library)


# --- Request/Response Models ---

class ContractAnalyzeRequest(BaseModel):
    contract_id: Optional[str] = "contract-001"
    title: str = "Legal Contract"
    full_text: str
    contract_type: Optional[str] = None


class ContractRedlineRequest(BaseModel):
    original_text: str
    modified_text: str
    original_title: Optional[str] = "Original Contract"
    modified_title: Optional[str] = "Modified Contract"


class CreateClauseLibraryItemRequest(BaseModel):
    clause_type: str
    title: str
    category: str
    standard_language: str
    fallback_tier_1: str
    fallback_tier_2: Optional[str] = None
    walkaway_language: Optional[str] = None
    guidance_notes: Optional[str] = ""
    statutory_reference: Optional[str] = None
    jurisdiction: Optional[str] = "India"
    tags: Optional[List[str]] = None


class UpdateClauseLibraryItemRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    standard_language: Optional[str] = None
    fallback_tier_1: Optional[str] = None
    fallback_tier_2: Optional[str] = None
    walkaway_language: Optional[str] = None
    guidance_notes: Optional[str] = None
    statutory_reference: Optional[str] = None
    tags: Optional[List[str]] = None


class CreatePlaybookRuleRequest(BaseModel):
    rule_id: str
    clause_type: str
    rule_name: str
    mandatory: bool = True
    standard_position: str
    acceptable_fallbacks: Optional[List[str]] = None
    forbidden_terms: Optional[List[str]] = None
    risk_weight: Optional[int] = 15
    recommended_redline: str
    guidance_notes: Optional[str] = ""
    statutory_reference: Optional[str] = None


class CreatePlaybookRequest(BaseModel):
    playbook_id: Optional[str] = None
    name: str
    description: str
    contract_type: str
    rules: List[CreatePlaybookRuleRequest]


class EvaluatePlaybookRequest(BaseModel):
    playbook_id: str
    contract_id: Optional[str] = "contract-001"
    full_text: str
    title: Optional[str] = "Contract Under Review"


# --- Core Contract Analysis Endpoints ---

@router.post("/cases/{case_id}/contracts/analyze")
async def analyze_contract(case_id: str, body: ContractAnalyzeRequest, _=Depends(get_case_access)):
    """Extract 29+ clause types, calculate 0-100 risk score, and assess Indian statutory compliance."""
    doc = ContractDocument(
        contract_id=body.contract_id or "contract-001",
        title=body.title,
        full_text=body.full_text,
        contract_type=body.contract_type,
    )

    # 1. Extract parties & clauses
    doc.parties = engine._extract_parties(body.full_text)
    clauses = engine.extract_clauses(body.full_text, contract_id=doc.contract_id)
    doc.clauses = clauses

    # 2. Extract obligations
    obligations = engine.extract_obligations(doc)

    # 3. Assess risk (0-100)
    risk_assessment = engine.assess_risk(doc)

    # 4. Indian statutory compliance checks
    indian_compliance = engine.check_indian_law_compliance(doc)

    return {
        "case_id": case_id,
        "contract_id": doc.contract_id,
        "title": doc.title,
        "contract_type": doc.contract_type,
        "parties": doc.parties,
        "clause_count": len(clauses),
        "clauses": [
            {
                "clause_id": c.clause_id,
                "clause_type": c.clause_type.value,
                "title": c.title,
                "content": c.content,
                "start_position": c.start_position,
                "end_position": c.end_position,
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
        "indian_law_compliance": indian_compliance,
    }


@router.post("/cases/{case_id}/contracts/heatmap")
async def get_contract_heatmap(case_id: str, body: ContractAnalyzeRequest, _=Depends(get_case_access)):
    """Generate structured risk heatmap matrix across 5 functional legal categories."""
    doc = ContractDocument(
        contract_id=body.contract_id or "contract-001",
        title=body.title,
        full_text=body.full_text,
    )
    doc.clauses = engine.extract_clauses(body.full_text, contract_id=doc.contract_id)
    doc.risk_assessment = engine.assess_risk(doc)
    heatmap = engine.generate_risk_heatmap(doc)
    return {"case_id": case_id, **heatmap}


@router.post("/cases/{case_id}/contracts/redline")
async def redline_comparison(case_id: str, body: ContractRedlineRequest, _=Depends(get_case_access)):
    """Compare two contract versions and generate redline changes with additions and deletions."""
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


# --- Enterprise Clause Library Endpoints ---

@router.get("/contracts/clause-library")
async def list_clause_library(
    category: Optional[str] = None,
    clause_type: Optional[str] = None,
    q: Optional[str] = None,
    _=Depends(get_auth_context),
):
    """Search and filter the Enterprise Clause Library (Standard, Fallback Tier 1/2, Walkaway)."""
    items = clause_library.list_clauses(category=category, clause_type=clause_type, query=q)
    return {
        "items": [item.to_dict() for item in items],
        "total": len(items),
    }


@router.get("/contracts/clause-library/{clause_id}")
async def get_clause_library_item(clause_id: str, _=Depends(get_auth_context)):
    """Get a specific clause library entry with standard, fallback, and walkaway language."""
    item = clause_library.get_clause(clause_id)
    if not item:
        raise HTTPException(404, f"Clause '{clause_id}' not found in library")
    return item.to_dict()


@router.post("/contracts/clause-library", status_code=status.HTTP_201_CREATED)
async def create_clause_library_item(body: CreateClauseLibraryItemRequest, _=Depends(get_auth_context)):
    """Add a new custom clause template to the Enterprise Clause Library."""
    item = ClauseLibraryItem(
        clause_id="",
        clause_type=body.clause_type,
        title=body.title,
        category=body.category,
        standard_language=body.standard_language,
        fallback_tier_1=body.fallback_tier_1,
        fallback_tier_2=body.fallback_tier_2,
        walkaway_language=body.walkaway_language,
        guidance_notes=body.guidance_notes or "",
        statutory_reference=body.statutory_reference,
        jurisdiction=body.jurisdiction or "India",
        tags=body.tags or [],
    )
    created = clause_library.add_clause(item)
    return created.to_dict()


@router.put("/contracts/clause-library/{clause_id}")
async def update_clause_library_item(clause_id: str, body: UpdateClauseLibraryItemRequest, _=Depends(get_auth_context)):
    """Update standard language, fallbacks, or guidance notes of a clause library entry."""
    updated = clause_library.update_clause(clause_id, body.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(404, f"Clause '{clause_id}' not found in library")
    return updated.to_dict()


@router.delete("/contracts/clause-library/{clause_id}")
async def delete_clause_library_item(clause_id: str, _=Depends(get_auth_context)):
    """Delete a clause from the library."""
    deleted = clause_library.delete_clause(clause_id)
    if not deleted:
        raise HTTPException(404, f"Clause '{clause_id}' not found in library")
    return {"status": "deleted", "clause_id": clause_id}


# --- Firm Playbook Deviation Endpoints ---

@router.get("/cases/{case_id}/contracts/playbooks")
async def list_playbooks(case_id: str, _=Depends(get_case_access)):
    """List all available firm negotiation playbooks with rules and risk weights."""
    playbooks = playbook_engine.list_playbooks()
    return {
        "items": [pb.to_dict() for pb in playbooks],
        "total": len(playbooks),
    }


@router.get("/cases/{case_id}/contracts/playbooks/{playbook_id}")
async def get_playbook(case_id: str, playbook_id: str, _=Depends(get_case_access)):
    """Get detailed rules, acceptable fallbacks, and walkaway conditions of a playbook."""
    pb = playbook_engine.get_playbook(playbook_id)
    if not pb:
        raise HTTPException(404, f"Playbook '{playbook_id}' not found")
    return pb.to_dict()


@router.post("/cases/{case_id}/contracts/playbooks", status_code=status.HTTP_201_CREATED)
async def create_playbook(case_id: str, body: CreatePlaybookRequest, _=Depends(get_case_access)):
    """Create a new custom negotiation playbook for a case or firm."""
    rules = [
        PlaybookRule(
            rule_id=r.rule_id,
            clause_type=r.clause_type,
            rule_name=r.rule_name,
            mandatory=r.mandatory,
            standard_position=r.standard_position,
            acceptable_fallbacks=r.acceptable_fallbacks or [],
            forbidden_terms=r.forbidden_terms or [],
            risk_weight=r.risk_weight or 15,
            recommended_redline=r.recommended_redline,
            guidance_notes=r.guidance_notes or "",
            statutory_reference=r.statutory_reference,
        )
        for r in body.rules
    ]
    pb = ContractPlaybook(
        playbook_id=body.playbook_id or f"PB-CUSTOM-{body.contract_type.upper()[:6]}",
        name=body.name,
        description=body.description,
        contract_type=body.contract_type,
        rules=rules,
    )
    created = playbook_engine.add_playbook(pb)
    return created.to_dict()


@router.post("/cases/{case_id}/contracts/playbooks/evaluate")
async def evaluate_contract_against_playbook(
    case_id: str,
    body: EvaluatePlaybookRequest,
    _=Depends(get_case_access),
):
    """Evaluate contract against firm playbook, flag deviations, and generate automated redlines."""
    contract_id = body.contract_id or "contract-001"

    # 1. Extract clauses from contract text
    clauses = engine.extract_clauses(body.full_text, contract_id=contract_id)

    # 2. Evaluate against selected playbook
    eval_result = playbook_engine.evaluate_contract(
        contract_id=contract_id,
        playbook_id=body.playbook_id,
        clauses=clauses,
        full_text=body.full_text,
    )

    return {
        "case_id": case_id,
        **eval_result.to_dict(),
    }
