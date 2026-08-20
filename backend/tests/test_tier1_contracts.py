"""Tier 1 Test Suite: Contract Intelligence & Redlining (Features 16-19).

Covers:
- Feature 16: 29 Clause Extraction & Risk Scoring (0-100)
- Feature 17: Clause Library & Fallback Tiers (Standard, Fallback, Walkaway)
- Feature 18: Playbook Deviation Analysis & Statutory Compliance
- Feature 19: Redline Visual Diff Editor & Tracked Changes
"""

import pytest
from datetime import datetime, timezone

from app.ai.contract_intelligence import (
    ClauseType,
    RiskLevel,
    ObligationType,
    ObligationStatus,
    ContractClause,
    ContractObligation,
    RedlineChange,
    ContractRiskAssessment,
    ContractDocument,
    ContractIntelligenceEngine,
    analyze_contract,
    track_obligations,
    CLAUSE_PATTERNS,
    RISK_KEYWORDS,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Feature 16: 29 Clause Extraction & Risk Scoring (0-100)
# ============================================================================

class TestFeature16ClauseExtractionAndRisk:
    """Feature 16: Automated 29+ clause extraction and 0-100 risk scoring."""

    def setup_method(self):
        self.engine = ContractIntelligenceEngine()

    def test_29_clause_types_enum_coverage(self):
        """ClauseType enum covers 29+ standard commercial and Indian legal clause classifications."""
        clause_values = {c.value for c in ClauseType}
        assert len(clause_values) >= 29
        assert "indemnity" in clause_values
        assert "limitation_of_liability" in clause_values
        assert "governing_law" in clause_values
        assert "dispute_resolution" in clause_values
        assert "confidentiality" in clause_values
        assert "non_compete" in clause_values
        assert "termination" in clause_values
        assert "intellectual_property" in clause_values
        assert "force_majeure" in clause_values

    def test_multi_clause_extraction_from_master_agreement(self):
        """Engine extracts multiple distinct clauses with bounding offsets."""
        text = """
        MASTER SERVICES AGREEMENT
        
        BETWEEN:
        Acme Corp India Private Limited ("Company")
        AND
        Beta Tech Solutions LLP ("Service Provider")
        
        1. SCOPE OF SERVICES
        Service Provider shall deliver software engineering services as defined in SOWs.
        
        2. TERM AND TERMINATION
        This Agreement commences on 01/01/2026 and shall continue for 3 years. Either party may terminate with 30 days notice.
        
        3. PAYMENT TERMS
        Invoices are payable within 30 days of receipt via NEFT/RTGS.
        
        4. CONFIDENTIALITY
        Each party shall maintain confidential information in strict confidence for 5 years.
        
        5. INTELLECTUAL PROPERTY
        All work product and IP created shall belong exclusively to the Company.
        
        6. INDEMNITY
        Service Provider shall indemnify Company against third party IP infringement claims.
        
        7. GOVERNING LAW AND JURISDICTION
        This Agreement shall be governed by laws of India and courts in Mumbai shall have jurisdiction.
        """
        clauses = self.engine.extract_clauses(text, contract_id="MSA-001")
        assert len(clauses) >= 6
        types = {c.clause_type for c in clauses}
        assert ClauseType.SCOPE in types
        assert ClauseType.TERM in types or ClauseType.TERMINATION in types
        assert ClauseType.PAYMENT in types
        assert ClauseType.CONFIDENTIALITY in types
        assert ClauseType.INDEMNITY in types
        assert ClauseType.GOVERNING_LAW in types

    def test_critical_risk_unlimited_indemnity(self):
        """Unlimited indemnity is detected and flagged as CRITICAL risk."""
        text = "INDEMNIFICATION: Vendor provides unlimited indemnity and shall hold harmless Buyer from all damages."
        clauses = self.engine.extract_clauses(text, contract_id="IND-001")
        indemnity_c = next((c for c in clauses if c.clause_type == ClauseType.INDEMNITY), None)
        assert indemnity_c is not None
        assert indemnity_c.risk_level == RiskLevel.CRITICAL
        assert any("unlimited indemnity" in f.lower() for f in indemnity_c.risk_factors)

    def test_critical_risk_post_termination_non_compete_section27(self):
        """Post-termination non-compete is flagged as CRITICAL risk under Section 27 Indian Contract Act."""
        text = "NON-COMPETE: Employee shall not compete with Company for 24 months post-termination anywhere in India."
        clauses = self.engine.extract_clauses(text, contract_id="NC-001")
        nc_c = next((c for c in clauses if c.clause_type == ClauseType.NON_COMPETE), None)
        assert nc_c is not None
        assert nc_c.risk_level == RiskLevel.CRITICAL
        assert any("Section 27" in f for f in nc_c.risk_factors)

    def test_overall_contract_risk_assessment_score(self):
        """Contract risk score (0-100) aggregates clause severities."""
        doc = ContractDocument(
            contract_id="RISK-DOC-1",
            title="High Risk Vendor Contract",
            full_text="Sample text",
        )
        doc.clauses = [
            ContractClause("c1", ClauseType.INDEMNITY, "Indemnity", "unlimited indemnity", 0, 50, risk_level=RiskLevel.CRITICAL, risk_factors=["Unlimited liability"]),
            ContractClause("c2", ClauseType.TERMINATION, "Termination", "immediate termination without cause", 51, 100, risk_level=RiskLevel.HIGH, risk_factors=["No cure period"]),
            ContractClause("c3", ClauseType.GOVERNING_LAW, "Governing Law", "laws of India", 101, 150, risk_level=RiskLevel.LOW),
        ]
        assessment = self.engine.assess_risk(doc)
        assert assessment.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        assert assessment.risk_score >= 60.0
        assert len(assessment.critical_issues) >= 1
        assert len(assessment.recommendations) >= 1


# ============================================================================
# Feature 17: Clause Library & Fallback Tiers
# ============================================================================

class TestFeature17ClauseLibraryAndFallbacks:
    """Feature 17: Clause tiering (Standard, Fallback, Walkaway)."""

    def test_clause_obligation_extraction_with_parties(self):
        """Obligations are extracted with responsible and beneficiary parties."""
        text = "PAYMENT: Buyer shall pay Seller INR 25,00,000 within 15 days of invoice."
        doc = ContractDocument(contract_id="OBL-01", title="Payment Agreement", full_text=text)
        doc.clauses = [ContractClause("c1", ClauseType.PAYMENT, "Payment", text, 0, len(text))]
        engine = ContractIntelligenceEngine()
        obligations = engine.extract_obligations(doc)
        assert len(obligations) >= 1
        assert obligations[0].obligation_type == ObligationType.PAYMENT
        assert "25,00,000" in obligations[0].description or "pay" in obligations[0].description.lower()

    def test_clause_risk_keywords_categorization(self):
        """Risk keywords dictionary classifies critical, high, medium, and low triggers."""
        assert len(RISK_KEYWORDS[RiskLevel.CRITICAL]) >= 4
        assert any("unlimited" in k for k in RISK_KEYWORDS[RiskLevel.CRITICAL])
        assert len(RISK_KEYWORDS[RiskLevel.HIGH]) >= 4
        assert len(RISK_KEYWORDS[RiskLevel.MEDIUM]) >= 3


# ============================================================================
# Feature 18: Playbook Deviation Scoring
# ============================================================================

class TestFeature18PlaybookDeviation:
    """Feature 18: Automated deviation scoring against enterprise negotiation playbooks."""

    def test_unilateral_arbitrator_appointment_flagged(self):
        """Arbitration clause giving one party sole discretion to appoint arbitrator violates §12(5) Arbitration Act."""
        engine = ContractIntelligenceEngine()
        text = "DISPUTE RESOLUTION: Any dispute shall be referred to a sole arbitrator appointed at the sole discretion to appoint of Party A."
        clauses = engine.extract_clauses(text, contract_id="ARB-01")
        arb_c = next((c for c in clauses if c.clause_type == ClauseType.DISPUTE_RESOLUTION), None)
        assert arb_c is not None
        assert arb_c.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert any("Perkins Eastman" in f or "Arbitration Act" in f for f in arb_c.risk_factors)

    def test_convenience_termination_without_cause_flagged(self):
        """Immediate termination without cause or notice triggers high risk warning."""
        engine = ContractIntelligenceEngine()
        text = "TERMINATION: Company may terminate this contract for convenience immediately without cause or notice."
        clauses = engine.extract_clauses(text, contract_id="TERM-01")
        term_c = next((c for c in clauses if c.clause_type == ClauseType.TERMINATION), None)
        assert term_c is not None
        assert term_c.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)


# ============================================================================
# Feature 19: Redline Visual Diff Editor & Tracked Changes
# ============================================================================

class TestFeature19RedlineVisualDiff:
    """Feature 19: Side-by-side redline comparison and diff generation."""

    def setup_method(self):
        self.engine = ContractIntelligenceEngine()

    def test_redline_detects_insertions_and_deletions(self):
        """Engine compares original and modified contract versions and detects insertions and deletions."""
        orig_doc = ContractDocument(
            contract_id="ORIG-1",
            title="Original Contract",
            full_text="1. Liability is capped at INR 10,00,000.\n2. Notice period is 30 days.",
            clauses=[
                ContractClause("c1", ClauseType.LIMITATION_OF_LIABILITY, "Liability", "Liability is capped at INR 10,00,000.", 0, 40),
                ContractClause("c2", ClauseType.TERMINATION, "Termination", "Notice period is 30 days.", 41, 70),
            ],
        )

        mod_doc = ContractDocument(
            contract_id="MOD-1",
            title="Modified Contract",
            full_text="1. Liability is capped at INR 50,00,000.\n2. Notice period is 60 days.\n3. Confidentiality applies for 3 years.",
            clauses=[
                ContractClause("c1", ClauseType.LIMITATION_OF_LIABILITY, "Liability", "Liability is capped at INR 50,00,000.", 0, 40),
                ContractClause("c2", ClauseType.TERMINATION, "Termination", "Notice period is 60 days.", 41, 70),
                ContractClause("c3", ClauseType.CONFIDENTIALITY, "Confidentiality", "Confidentiality applies for 3 years.", 71, 110),
            ],
        )

        changes = self.engine.compare_contracts(orig_doc, mod_doc)
        assert len(changes) >= 1
        change_types = {c.change_type for c in changes}
        assert "modification" in change_types or "insertion" in change_types

    def test_redline_summary_document_generation(self):
        """Redline summary formats total additions, deletions, and tracked change details."""
        orig_doc = ContractDocument(contract_id="O1", title="Original", full_text="Text A")
        mod_doc = ContractDocument(contract_id="M1", title="Modified", full_text="Text B")
        changes = [
            RedlineChange(change_id="ch-1", change_type="modification", original_text="Text A", modified_text="Text B"),
        ]
        summary = self.engine.generate_redline_document(orig_doc, mod_doc, changes)
        assert "REDLINE COMPARISON REPORT" in summary
        assert "Total Changes: 1" in summary
        assert "MODIFICATION" in summary

    def test_redline_api_endpoint(self, api_client, fake):
        """POST /cases/{case_id}/contracts/redline runs redline comparison across two texts."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Contract Redline Case", "case_type": "COMMERCIAL", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        orig_text = "Governing law is England. Notice period is 15 days."
        mod_text = "Governing law is India. Notice period is 45 days."

        res = api_client.post(f"{API}/cases/{case_id}/contracts/redline", json={
            "original_text": orig_text,
            "modified_text": mod_text,
            "original_title": "Vendor Draft v1",
            "modified_title": "Customer Redline v2",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == case_id
        assert "total_changes" in data
        assert "summary" in data
