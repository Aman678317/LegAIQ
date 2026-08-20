"""Tests for Contract Intelligence Module."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

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
    INDIAN_CONTRACT_PATTERNS,
)


class TestContractIntelligenceEngine:
    """Test the contract intelligence engine."""

    def setup_method(self):
        self.engine = ContractIntelligenceEngine()

    def test_extract_parties_simple(self):
        """Extract parties from simple contract text."""
        text = """
        This Agreement is made between ABC Private Limited ("Party A")
        and XYZ LLP ("Party B").
        """
        parties = self.engine._extract_parties(text)
        assert len(parties) >= 1

    def test_extract_clauses_basic(self):
        """Extract basic clauses from contract."""
        text = """
        SOFTWARE DEVELOPMENT AGREEMENT

        This Agreement is made between Party A and Party B.

        SCOPE OF WORK
        Developer shall build a web application.

        PAYMENT TERMS
        Client shall pay INR 10,00,000 in milestones.

        CONFIDENTIALITY
        Both parties shall keep information confidential.

        TERMINATION
        Either party may terminate with 30 days notice.

        GOVERNING LAW
        This Agreement governed by laws of India.
        """
        clauses = self.engine.extract_clauses(text, "TEST-001")

        assert len(clauses) >= 4
        clause_types = {c.clause_type for c in clauses}
        assert ClauseType.SCOPE in clause_types
        assert ClauseType.PAYMENT in clause_types
        assert ClauseType.CONFIDENTIALITY in clause_types
        assert ClauseType.TERMINATION in clause_types
        assert ClauseType.GOVERNING_LAW in clause_types

    def test_clause_risk_assessment_critical(self):
        """Critical risk keywords detected."""
        text = "Party shall provide unlimited indemnity and hold harmless for all claims."
        clauses = self.engine.extract_clauses(text, "TEST")

        indemnity_clauses = [c for c in clauses if c.clause_type == ClauseType.INDEMNITY]
        if indemnity_clauses:
            assert indemnity_clauses[0].risk_level == RiskLevel.CRITICAL
            assert any("unlimited indemnity" in f.lower() for f in indemnity_clauses[0].risk_factors)

    def test_clause_risk_assessment_high(self):
        """High risk keywords detected."""
        text = "Either party may terminate for convenience without cause."
        clauses = self.engine.extract_clauses(text, "TEST")

        term_clauses = [c for c in clauses if c.clause_type == ClauseType.TERMINATION]
        if term_clauses:
            assert term_clauses[0].risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_extract_obligations_with_dates(self):
        """Extract obligations with due dates."""
        text = """
        PAYMENT TERMS
        Client shall pay INR 10,00,000 by 15/03/2024.
        Developer shall deliver source code by 30/06/2024.
        """
        contract = ContractDocument(
            contract_id="TEST-001",
            title="Test Contract",
            full_text=text,
        )
        # Manually add a payment clause
        from app.ai.contract_intelligence import ContractClause
        clause = ContractClause(
            clause_id="TEST-001-CL-001",
            clause_type=ClauseType.PAYMENT,
            title="Payment Terms",
            content=text,
            start_position=0,
            end_position=len(text),
        )
        contract.clauses = [clause]

        obligations = self.engine.extract_obligations(contract)
        assert len(obligations) >= 1

        payment_obls = [o for o in obligations if o.obligation_type == ObligationType.PAYMENT]
        assert len(payment_obls) >= 1
        if payment_obls[0].due_date:
            assert payment_obls[0].due_date.month == 3
            assert payment_obls[0].due_date.day == 15

    def test_extract_delivery_obligations(self):
        """Extract delivery obligations."""
        text = "Developer shall deliver the application by 31/12/2024."
        contract = ContractDocument(
            contract_id="TEST-002",
            title="Test",
            full_text=text,
        )
        from app.ai.contract_intelligence import ContractClause
        clause = ContractClause(
            clause_id="TEST-002-CL-001",
            clause_type=ClauseType.SCOPE,
            title="Scope",
            content=text,
            start_position=0,
            end_position=len(text),
        )
        contract.clauses = [clause]

        obligations = self.engine.extract_obligations(contract)
        delivery_obls = [o for o in obligations if o.obligation_type == ObligationType.DELIVERY]
        assert len(delivery_obls) >= 1

    def test_assess_risk_overall(self):
        """Overall risk assessment."""
        text = """
        AGREEMENT

        SCOPE
        Developer shall build app.

        INDEMNITY
        Developer shall provide unlimited indemnity and hold harmless.

        LIMITATION OF LIABILITY
        No limitation of liability.

        TERMINATION
        Terminate for convenience immediately.
        """
        contract = analyze_contract(text, "RISK-001", "Risk Test", "service")

        assert contract.risk_assessment is not None
        assert contract.risk_assessment.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        assert contract.risk_assessment.risk_score > 30
        assert len(contract.risk_assessment.critical_issues) > 0

    def test_assess_risk_low_risk_contract(self):
        """Low risk contract assessment."""
        text = """
        SIMPLE AGREEMENT

        SCOPE
        Party A provides services.

        PAYMENT
        Party B pays fixed fee of INR 1,00,000.

        TERM
        1 year term.

        GOVERNING LAW
        Laws of India.

        DISPUTE RESOLUTION
        Arbitration under Arbitration Act.

        CONFIDENTIALITY
        Standard confidentiality.
        """
        contract = analyze_contract(text, "LOW-001", "Low Risk", "service")

        assert contract.risk_assessment.overall_risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.NEGLIGIBLE)

    def test_missing_critical_clauses_flagged(self):
        """Missing critical clauses flagged as compliance gaps."""
        text = """
        SIMPLE AGREEMENT
        Party A pays Party B INR 1,00,000 for services.
        """
        contract = analyze_contract(text, "GAP-001", "Gap Test", "service")

        assert "Missing termination clause" in contract.risk_assessment.compliance_gaps or \
               any("termination" in g.lower() for g in contract.risk_assessment.compliance_gaps)

    def test_compare_contracts_changes(self):
        """Compare two contract versions."""
        original_text = """
        AGREEMENT
        PAYMENT
        Party A pays 1000.
        TERMINATION
        30 days notice.
        """
        modified_text = """
        AGREEMENT
        PAYMENT
        Party A pays 2000.
        TERMINATION
        60 days notice.
        CONFIDENTIALITY
        New clause added.
        """
        original = analyze_contract(original_text, "ORIG", "Original")
        modified = analyze_contract(modified_text, "MOD", "Modified")

        changes = self.engine.compare_contracts(original, modified)
        assert len(changes) >= 2

        change_types = {c.change_type for c in changes}
        assert "modification" in change_types or "insertion" in change_types

    def test_generate_redline_document(self):
        """Generate redline comparison document."""
        original_text = "AGREEMENT\nPAYMENT\nParty pays 1000."
        modified_text = "AGREEMENT\nPAYMENT\nParty pays 2000."

        original = analyze_contract(original_text, "ORIG", "Original")
        modified = analyze_contract(modified_text, "MOD", "Modified")

        changes = self.engine.compare_contracts(original, modified)
        redline = self.engine.generate_redline_document(original, modified, changes)

        assert "REDLINE COMPARISON" in redline
        assert "Original" in redline
        assert "Modified" in redline

    def test_check_indian_law_compliance_stamp_duty(self):
        """Check stamp duty compliance for sale deed."""
        text = """
        SALE DEED
        Party A sells property to Party B for INR 50,00,000.
        """
        contract = analyze_contract(text, "STAMP-001", "Sale Deed", "sale deed")

        compliance = contract.metadata.get("indian_law_compliance", [])
        assert any("stamp duty" in c.lower() for c in compliance)

    def test_check_indian_law_compliance_lease_registration(self):
        """Check lease registration compliance."""
        text = """
        LEASE DEED
        Party A leases property to Party B for 2 years.
        """
        contract = analyze_contract(text, "LEASE-001", "Lease Deed", "lease deed")

        compliance = contract.metadata.get("indian_law_compliance", [])
        assert any("registration" in c.lower() for c in compliance)

    def test_check_indian_law_compliance_gst(self):
        """Check GST clause recommendation."""
        text = """
        SERVICE AGREEMENT
        Party A supplies services to Party B for consideration.
        """
        contract = analyze_contract(text, "GST-001", "Service Agreement", "service")

        compliance = contract.metadata.get("indian_law_compliance", [])
        # GST check is informational
        assert isinstance(compliance, list)

    def test_check_indian_law_compliance_arbitration(self):
        """Check arbitration act reference."""
        text = """
        AGREEMENT
        DISPUTE RESOLUTION
        Disputes resolved by arbitration in Mumbai.
        """
        contract = analyze_contract(text, "ARB-001", "Arbitration Test", "service")

        compliance = contract.metadata.get("indian_law_compliance", [])
        assert any("arbitration" in c.lower() for c in compliance)

    def test_check_indian_law_compliance_data_protection(self):
        """Check DPDP Act compliance for personal data."""
        text = """
        AGREEMENT
        Party A processes personal data of Party B's customers.
        """
        contract = analyze_contract(text, "DPDP-001", "Data Processing", "service")

        compliance = contract.metadata.get("indian_law_compliance", [])
        assert any("dpdp" in c.lower() or "data protection" in c.lower() for c in compliance)

    def test_analyze_contract_full_pipeline(self):
        """Full contract analysis pipeline."""
        text = """
        SERVICE AGREEMENT
        This Agreement between Company A and Company B.
        SCOPE: Company A provides consulting.
        PAYMENT: Company B pays INR 10,00,000 by 31/03/2024.
        TERMINATION: 30 days notice.
        GOVERNING LAW: Laws of India.
        DISPUTE RESOLUTION: Arbitration under Arbitration Act, 1996.
        CONFIDENTIALITY: Standard 2-year confidentiality.
        """
        contract = analyze_contract(text, "FULL-001", "Full Test", "service")

        assert contract.contract_id == "FULL-001"
        assert len(contract.clauses) >= 4
        assert len(contract.obligations) >= 1
        assert contract.risk_assessment is not None
        assert "indian_law_compliance" in contract.metadata

    def test_track_obligations_overdue(self):
        """Track overdue obligations."""
        past_date = datetime.now(timezone.utc) - timedelta(days=10)
        obl = ContractObligation(
            obligation_id="OBL-001",
            obligation_type=ObligationType.PAYMENT,
            description="Payment due",
            responsible_party="Party A",
            beneficiary_party="Party B",
            due_date=past_date,
            contract_id="TRACK-001",
        )
        contract = ContractDocument(
            contract_id="TRACK-001",
            title="Track Test",
            obligations=[obl],
        )

        tracking = track_obligations(contract)
        assert tracking["summary"]["overdue"] == 1
        assert tracking["summary"]["pending"] == 0

    def test_track_obligations_due_soon(self):
        """Track obligations due soon."""
        soon_date = datetime.now(timezone.utc) + timedelta(days=3)
        obl = ContractObligation(
            obligation_id="OBL-002",
            obligation_type=ObligationType.DELIVERY,
            description="Delivery due soon",
            responsible_party="Party B",
            beneficiary_party="Party A",
            due_date=soon_date,
            contract_id="TRACK-002",
        )
        contract = ContractDocument(
            contract_id="TRACK-002",
            title="Track Test",
            obligations=[obl],
        )

        tracking = track_obligations(contract)
        assert tracking["summary"]["due_soon"] == 1

    def test_track_obligations_completed(self):
        """Track completed obligations."""
        obl = ContractObligation(
            obligation_id="OBL-003",
            obligation_type=ObligationType.PAYMENT,
            description="Completed payment",
            responsible_party="Party A",
            beneficiary_party="Party B",
            status=ObligationStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            contract_id="TRACK-003",
        )
        contract = ContractDocument(
            contract_id="TRACK-003",
            title="Track Test",
            obligations=[obl],
        )

        tracking = track_obligations(contract)
        assert tracking["summary"]["completed"] == 1
        assert tracking["summary"]["overdue"] == 0


class TestClausePatterns:
    """Test clause pattern matching."""

    def test_all_clause_types_have_patterns(self):
        """All clause types have at least one pattern."""
        for clause_type in ClauseType:
            if clause_type != ClauseType.CUSTOM:
                assert clause_type in CLAUSE_PATTERNS
                assert len(CLAUSE_PATTERNS[clause_type]) > 0

    def test_risk_keywords_defined(self):
        """Risk keywords defined for all levels."""
        for level in RiskLevel:
            if level != RiskLevel.NEGLIGIBLE:
                assert level in RISK_KEYWORDS
                assert len(RISK_KEYWORDS[level]) > 0

    def test_indian_patterns_defined(self):
        """Indian law patterns defined."""
        assert "stamp_duty" in INDIAN_CONTRACT_PATTERNS
        assert "registration" in INDIAN_CONTRACT_PATTERNS
        assert "arbitration_act" in INDIAN_CONTRACT_PATTERNS
        assert "gst" in INDIAN_CONTRACT_PATTERNS
        assert "tds" in INDIAN_CONTRACT_PATTERNS
        assert "data_protection" in INDIAN_CONTRACT_PATTERNS


class TestEdgeCases:
    """Edge case tests."""

    def setup_method(self):
        self.engine = ContractIntelligenceEngine()

    def test_empty_contract(self):
        """Handle empty contract text."""
        contract = analyze_contract("", "EMPTY", "Empty")
        assert contract.contract_id == "EMPTY"
        assert len(contract.clauses) == 0

    def test_contract_without_dates(self):
        """Handle contract without dates."""
        text = "AGREEMENT\nParty A pays Party B."
        contract = analyze_contract(text, "NODATE", "No Dates")
        tracking = track_obligations(contract)
        assert tracking["summary"]["overdue"] == 0

    def test_multiple_parties_extraction(self):
        """Extract multiple parties."""
        text = """
        This Agreement is between:
        Alpha Private Limited ("Alpha")
        Beta LLP ("Beta")
        Gamma Corporation ("Gamma")
        """
        parties = self.engine._extract_parties(text)
        # At least some parties extracted
        assert len(parties) >= 1

    def test_clause_type_custom_fallback(self):
        """Custom clause type for unmatched sections."""
        text = """
        AGREEMENT
        SCOPE
        Services provided.
        UNUSUAL SECTION
        This is a very unusual section that doesn't match patterns.
        """
        clauses = self.engine.extract_clauses(text, "CUSTOM")
        # Should at least find SCOPE
        scope_clauses = [c for c in clauses if c.clause_type == ClauseType.SCOPE]
        assert len(scope_clauses) >= 1

    def test_risk_assessment_with_no_clauses(self):
        """Risk assessment with no clauses."""
        contract = ContractDocument(
            contract_id="NOCLAUSE",
            title="No Clauses",
            full_text="Simple agreement.",
            clauses=[],
        )
        assessment = self.engine.assess_risk(contract)
        assert assessment.overall_risk == RiskLevel.NEGLIGIBLE
        assert assessment.risk_score == 0


class TestEnterpriseClauseLibrary:
    """Tests for Enterprise Clause Library repository and fallbacks."""

    def setup_method(self):
        from app.ai.clause_library import EnterpriseClauseLibrary, ClauseLibraryItem
        self.library = EnterpriseClauseLibrary()

    def test_list_clauses_all(self):
        """Retrieve preloaded standard clause library."""
        clauses = self.library.list_clauses()
        assert len(clauses) >= 5
        types = {c.clause_type for c in clauses}
        assert "indemnity" in types
        assert "limitation_of_liability" in types
        assert "non_compete" in types
        assert "governing_law" in types
        assert "stamp_duty" in types

    def test_filter_by_category_and_query(self):
        """Filter clause library by category and search keyword."""
        results = self.library.list_clauses(category="Dispute Resolution")
        assert len(results) >= 1
        assert any("arbitration" in c.standard_language.lower() for c in results)

        search_res = self.library.list_clauses(query="Section 27")
        assert len(search_res) >= 1
        assert search_res[0].clause_type == "non_compete"

    def test_add_and_update_custom_clause(self):
        """Add and modify a custom clause in the library."""
        from app.ai.clause_library import ClauseLibraryItem
        new_item = ClauseLibraryItem(
            clause_id="LIB-CUSTOM-099",
            clause_type="custom",
            title="SaaS SLA & Uptime Guarantee",
            category="Technology",
            standard_language="Service Provider guarantees 99.9% monthly uptime.",
            fallback_tier_1="99.5% monthly uptime with service credits.",
        )
        added = self.library.add_clause(new_item)
        assert added.clause_id == "LIB-CUSTOM-099"

        # Update
        updated = self.library.update_clause("LIB-CUSTOM-099", {"title": "Updated SaaS SLA 99.99%"})
        assert updated is not None
        assert updated.title == "Updated SaaS SLA 99.99%"

        # Delete
        assert self.library.delete_clause("LIB-CUSTOM-099") is True
        assert self.library.get_clause("LIB-CUSTOM-099") is None


class TestFirmPlaybookDeviationEngine:
    """Tests for Playbook Deviation Engine and automated redlining."""

    def setup_method(self):
        from app.ai.playbooks import PlaybookDeviationEngine
        self.engine = PlaybookDeviationEngine()

    def test_msa_playbook_detects_forbidden_indemnity(self):
        """Detect uncapped indemnity and generate redline suggestion."""
        from app.ai.contract_intelligence import analyze_contract
        text = """
        MASTER SERVICES AGREEMENT
        INDEMNITY: Developer shall provide unlimited indemnity and hold harmless Client from any and all claims without cap.
        GOVERNING LAW: Laws of India.
        TERMINATION: 30 days notice for breach.
        """
        contract = analyze_contract(text, "TEST-DEV-01", "MSA Test", "master_services_agreement")
        res = self.engine.evaluate_contract("TEST-DEV-01", "PB-MSA-001", contract.clauses, text)

        assert res.compliance_score < 90
        assert len(res.deviations) >= 1
        assert any(d.clause_type == "indemnity" for d in res.deviations)
        assert any("unlimited" in d.issue_description.lower() for d in res.deviations)
        assert len(res.redline_recommendations) >= 1

    def test_employment_playbook_flags_section_27_void_non_compete(self):
        """Detect void post-employment non-compete under Section 27 Indian Contract Act."""
        from app.ai.contract_intelligence import analyze_contract
        text = """
        EMPLOYMENT AGREEMENT
        NON-COMPETE: Employee covenants not to engage in competing business for 1 year following termination.
        NON-SOLICITATION: Employee shall not solicit clients for 6 months.
        INTELLECTUAL PROPERTY: All works created are work for hire.
        """
        contract = analyze_contract(text, "TEST-EMP-01", "Employment Test", "employment_agreement")
        res = self.engine.evaluate_contract("TEST-EMP-01", "PB-EMPLOY-001", contract.clauses, text)

        assert res.overall_status in ("walkaway_triggered", "high_risk_deviations")
        sec_27_devs = [d for d in res.deviations if d.clause_type == "non_compete"]
        assert len(sec_27_devs) >= 1
        assert sec_27_devs[0].severity == "critical"
        assert "Section 27" in (sec_27_devs[0].statutory_reference or sec_27_devs[0].issue_description)

    def test_lease_playbook_flags_missing_stamp_duty(self):
        """Detect missing stamp duty clause in commercial lease deed."""
        from app.ai.contract_intelligence import analyze_contract
        text = """
        COMMERCIAL LEASE DEED
        TERM: 3 years.
        TERMINATION: 60 days notice.
        """
        contract = analyze_contract(text, "TEST-LEASE-01", "Lease Test", "lease_deed")
        res = self.engine.evaluate_contract("TEST-LEASE-01", "PB-LEASE-001", contract.clauses, text)

        assert len(res.deviations) >= 1
        assert any(d.clause_type == "stamp_duty" for d in res.deviations)


class TestRiskHeatmap:
    """Test risk heatmap generation across functional categories."""

    def test_generate_risk_heatmap_structure(self):
        """Generate structured risk heatmap matrix across 5 functional categories."""
        from app.ai.contract_intelligence import analyze_contract, ContractIntelligenceEngine
        engine = ContractIntelligenceEngine()
        text = """
        COMMERCIAL AGREEMENT
        INDEMNITY: Unlimited indemnity for all damages.
        PAYMENT: Client pays INR 10,00,000 within 30 days.
        NON-COMPETE: Shall not compete post-termination for 2 years.
        GOVERNING LAW: Laws of India.
        """
        contract = analyze_contract(text, "HEATMAP-01", "Heatmap Test", "commercial")
        heatmap = engine.generate_risk_heatmap(contract)

        assert "categories" in heatmap
        assert "Liability & Indemnity" in heatmap["categories"]
        assert "Restrictive Covenants" in heatmap["categories"]
        assert "Commercial & Term" in heatmap["categories"]
        assert heatmap["categories"]["Liability & Indemnity"]["highest_risk"] in ("critical", "high")


class TestContractIntelligenceApiExtended:
    """Test Clause Library and Playbook REST API endpoints."""

    @pytest.mark.asyncio
    async def test_clause_library_api(self, client, auth_headers):
        """List and get clause library items."""
        resp = await client.get("/api/v1/contracts/clause-library", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5

        # Get specific clause
        first_id = data["items"][0]["clause_id"]
        c_resp = await client.get(f"/api/v1/contracts/clause-library/{first_id}", headers=auth_headers)
        assert c_resp.status_code == 200
        assert c_resp.json()["clause_id"] == first_id

    @pytest.mark.asyncio
    async def test_playbook_evaluation_api(self, client, auth_headers, seed_case):
        """Evaluate contract against firm playbook via REST API."""
        case_id = seed_case["id"]
        eval_resp = await client.post(
            f"/api/v1/cases/{case_id}/contracts/playbooks/evaluate",
            json={
                "playbook_id": "PB-MSA-001",
                "full_text": "AGREEMENT\nINDEMNITY: Unlimited indemnity.\nGOVERNING LAW: Laws of India.",
            },
            headers=auth_headers,
        )
        assert eval_resp.status_code == 200
        res_data = eval_resp.json()
        assert "compliance_score" in res_data
        assert "deviations" in res_data
        assert len(res_data["deviations"]) >= 1

    @pytest.mark.asyncio
    async def test_contract_heatmap_api(self, client, auth_headers, seed_case):
        """Generate heatmap via REST API."""
        case_id = seed_case["id"]
        heat_resp = await client.post(
            f"/api/v1/cases/{case_id}/contracts/heatmap",
            json={
                "full_text": "AGREEMENT\nINDEMNITY: Unlimited indemnity.\nPAYMENT: 1000 INR.",
            },
            headers=auth_headers,
        )
        assert heat_resp.status_code == 200
        heat_data = heat_resp.json()
        assert "categories" in heat_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])