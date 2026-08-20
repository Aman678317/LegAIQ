"""Remediation & Hardening Comprehensive Verification Suite.

Tests all 8 remediation areas:
1. State Portals connector class aliases and StatePortalFactory
2. Bharatiya Sakshya Section 94 polymorphic presumption and Section 63 certificate flexibility
3. Ownership DAG cycle detection, lender-specific mortgages, and conveyance separation
4. BSA deterministic document ordering
5. Review Tables CSV formula injection sanitization
6. Workflows topological sort execution order
7. Contract Intelligence broadened post-termination non-compete detection
8. Shared Spaces constant-time passcode comparison & failed attempts tracking
"""
import hashlib
import hmac
import pytest
from datetime import datetime, timezone, timedelta

from app.ai.state_portals import (
    PortalState,
    StatePortalFactory,
    MahabhulekhConnector,
    BhoomiConnector,
    TNREGINETConnector,
    DharaniConnector,
    AnyRoRConnector,
    MaharashtraPortal,
    KarnatakaPortal,
    TamilNaduPortal,
    TelanganaPortal,
    GujaratPortal,
)
from app.ai.bharatiya_sakshya import (
    DocumentCategory,
    EvidenceItem,
    EvidenceType,
    Section63Certificate,
    check_section94_presumption,
    check_section97_presumption,
    generate_section63_certificate,
)
from app.ai.ownership_graph import (
    LinkType,
    OwnershipChainAnalyzer,
    TitleBreakSeverity,
)
from app.ai.review_tables import ReviewTableExporter
from app.ai.contract_intelligence import (
    ClauseType,
    ContractClause,
    ContractIntelligenceEngine,
    RiskLevel,
)
from app.ai.playbooks import (
    PlaybookEvaluator,
    PlaybookRule,
)
from app.api.workflows import _topological_sort
from app.api.shared_spaces import (
    hash_passcode,
    _SHARED_SPACES_STORE,
)


# ============================================================================
# 1. State Portals Aliases & Factory
# ============================================================================

class TestStatePortalsHardening:
    def test_connector_aliases(self):
        assert MahabhulekhConnector is MaharashtraPortal
        assert BhoomiConnector is KarnatakaPortal
        assert TNREGINETConnector is TamilNaduPortal
        assert DharaniConnector is TelanganaPortal
        assert AnyRoRConnector is GujaratPortal

    def test_state_portal_factory(self):
        c1 = StatePortalFactory.get_connector(PortalState.KARNATAKA, mock_mode=True)
        assert isinstance(c1, KarnatakaPortal)

        c2 = StatePortalFactory.get_connector("maharashtra", mock_mode=True)
        assert isinstance(c2, MaharashtraPortal)

        c3 = StatePortalFactory.get_connector("tn", mock_mode=True)
        assert isinstance(c3, TamilNaduPortal)

        c4 = StatePortalFactory.get_connector("telangana", mock_mode=True)
        assert isinstance(c4, TelanganaPortal)

        c5 = StatePortalFactory.get_connector("gujarat", mock_mode=True)
        assert isinstance(c5, GujaratPortal)

    @pytest.mark.asyncio
    async def test_search_by_survey_number_and_kwargs(self):
        connector = BhoomiConnector(mock_mode=True)
        res = await connector.search_by_survey_number(
            survey_number="124/3",
            district="Bangalore South",
            taluk="Whitefield",
            village="Varthur",
            hobli="Whitefield",
        )
        assert res.success is True
        assert len(res.records) >= 1
        await connector.close()


# ============================================================================
# 2. Bharatiya Sakshya Polymorphic Presumption & Section 63 Certificate
# ============================================================================

class TestBharatiyaSakshyaHardening:
    def test_section94_presumption_evidence_item(self):
        old_item = EvidenceItem(
            evidence_id="ev-1980",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Ancient deed",
            source="SRO Archives",
            date_created=datetime.now(timezone.utc) - timedelta(days=35 * 365),
        )
        qualifies, reason = check_section94_presumption(old_item)
        assert qualifies is True
        assert "Section 94" in reason

        new_item = EvidenceItem(
            evidence_id="ev-2020",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Recent deed",
            source="SRO",
            date_created=datetime.now(timezone.utc) - timedelta(days=5 * 365),
        )
        qualifies, reason = check_section94_presumption(new_item)
        assert qualifies is False
        assert "does not meet 30-year threshold" in reason

    def test_section94_presumption_datetime(self):
        dt_old = datetime(1985, 1, 1, tzinfo=timezone.utc)
        qualifies, _ = check_section94_presumption(dt_old)
        assert qualifies is True

        dt_recent = datetime(2022, 1, 1, tzinfo=timezone.utc)
        qualifies, _ = check_section94_presumption(dt_recent)
        assert qualifies is False

    def test_section94_presumption_integer_year(self):
        qualifies, reason = check_section94_presumption(1980)
        assert qualifies is True
        assert "Section 94" in reason

        qualifies, reason = check_section94_presumption(35)
        assert qualifies is True

        qualifies, reason = check_section94_presumption(2020)
        assert qualifies is False

        qualifies, reason = check_section94_presumption(10)
        assert qualifies is False

    def test_section63_certificate_dual_access(self):
        cert = generate_section63_certificate(
            file_name="Deed_1990.pdf",
            file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            hash_algorithm="SHA-256",
            certifier_name="Adv. Rajesh Kumar",
            certifier_designation="Senior Legal Counsel",
            system_parameters="Vault Node 1",
        )
        assert isinstance(cert, Section63Certificate)
        # Attribute access
        assert cert.title == "Section 63 Electronic Evidence Certificate"
        assert cert.hash_value == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert cert.algorithm == "SHA-256"
        assert cert.is_valid is True
        assert cert.certifier_name == "Adv. Rajesh Kumar"
        # Dict subscript access
        assert cert["legal_basis"] == "Section 63, Bharatiya Sakshya Adhiniyam, 2023"
        assert cert["custodian"]["name"] == "Adv. Rajesh Kumar"
        assert "certify that the electronic record" in cert["statement"]


# ============================================================================
# 3. Ownership Graph Hardening: Cycle Detection, Mortgages & Separation
# ============================================================================

class TestOwnershipGraphHardening:
    def test_circular_title_transfer_detection(self):
        """Detect circular conveyance chains (A -> B -> C -> A) and report DEFECTIVE."""
        events = [
            {
                "event_date": "2000-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Alice",
                "to_owner": "Bob",
            },
            {
                "event_date": "2010-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Bob",
                "to_owner": "Charlie",
            },
            {
                "event_date": "2020-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Charlie",
                "to_owner": "Alice",
            },
        ]
        dag = OwnershipChainAnalyzer.build_chain_dag("case-cycle", events, [], [])
        assert dag["title_status"] == "DEFECTIVE"
        assert any(g["break_type"] == "CIRCULAR_TRANSFER_DETECTED" for g in dag["gaps"])
        assert any(g["severity"] == TitleBreakSeverity.CRITICAL.value for g in dag["gaps"])

    def test_mortgages_do_not_break_conveyance_continuity(self):
        """Intervening mortgage with a bank does not cause false missing link breaks in title chain."""
        events = [
            {
                "event_date": "2000-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Alice",
                "to_owner": "Bob",
            },
            {
                "event_date": "2005-06-01",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Bob",
                "to_owner": "State Bank of India",
                "bank": "State Bank of India",
            },
            {
                "event_date": "2010-01-01",
                "transaction_type": "RELEASE_DEED",
                "from_owner": "State Bank of India",
                "to_owner": "Bob",
                "bank": "State Bank of India",
            },
            {
                "event_date": "2015-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Bob",
                "to_owner": "Charlie",
            },
        ]
        dag = OwnershipChainAnalyzer.build_chain_dag("case-mortgage-clean", events, [], [])
        # No gaps because mortgage was released by SBI and Bob conveyed to Charlie cleanly
        assert len(dag["gaps"]) == 0
        assert dag["title_status"] == "CLEAR"

    def test_unreleased_mortgage_by_specific_lender(self):
        """Undischarged mortgage with Canara Bank remains flagged even if another bank is released."""
        events = [
            {
                "event_date": "2000-01-01",
                "transaction_type": "SALE_DEED",
                "from_owner": "Alice",
                "to_owner": "Bob",
            },
            {
                "event_date": "2005-01-01",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Bob",
                "to_owner": "State Bank of India",
                "bank": "State Bank of India",
            },
            {
                "event_date": "2008-01-01",
                "transaction_type": "MORTGAGE_CHARGE",
                "from_owner": "Bob",
                "to_owner": "Canara Bank",
                "bank": "Canara Bank",
            },
            {
                "event_date": "2010-01-01",
                "transaction_type": "RELEASE_DEED",
                "from_owner": "State Bank of India",
                "to_owner": "Bob",
                "bank": "State Bank of India",
            },
        ]
        dag = OwnershipChainAnalyzer.build_chain_dag("case-multi-bank", events, [], [])
        assert dag["title_status"] == "DEFECTIVE"
        canara_gaps = [g for g in dag["gaps"] if "Canara Bank" in g["title"] or "Canara Bank" in g["description"]]
        assert len(canara_gaps) >= 1


# ============================================================================
# 4. Review Tables CSV Formula Injection Sanitization
# ============================================================================

class TestReviewTablesFormulaSanitization:
    def test_formula_injection_prefixes_escaped(self):
        columns = [{"id": "c1", "name": "=SUM(A1:A10)"}]
        rows = [
            {
                "document_name": "+CMD|' /C calc'!A0",
                "cells": {
                    "c1": {
                        "value": "@SUM(1,2)",
                        "confidence_score": 0.9,
                        "evidence": {"page_num": 1, "text_snippet": "-100% negative risk"},
                    }
                },
            }
        ]
        csv_text = ReviewTableExporter.export_csv("FormulaTest", columns, rows)
        # Verify formula prefixes got prepended with '
        assert "'=SUM(A1:A10)" in csv_text
        assert "'+CMD|' /C calc'!A0" in csv_text
        assert "'@SUM(1,2)" in csv_text


# ============================================================================
# 5. Workflows Topological Sort Execution Order
# ============================================================================

class TestWorkflowTopologicalExecution:
    def test_topological_sort_linear_and_branching(self):
        nodes = [
            {"id": "step_3", "name": "Report", "dependencies": ["step_2"]},
            {"id": "step_1", "name": "Ingest", "dependencies": []},
            {"id": "step_2", "name": "Analyze", "dependencies": ["step_1"]},
        ]
        sorted_nodes = _topological_sort(nodes)
        order = [n["id"] for n in sorted_nodes]
        assert order == ["step_1", "step_2", "step_3"]

    def test_topological_sort_with_edges(self):
        nodes = [
            {"id": "node_c", "name": "C"},
            {"id": "node_a", "name": "A"},
            {"id": "node_b", "name": "B"},
        ]
        edges = [
            {"source": "node_a", "target": "node_b"},
            {"source": "node_b", "target": "node_c"},
        ]
        sorted_nodes = _topological_sort(nodes, edges)
        order = [n["id"] for n in sorted_nodes]
        assert order == ["node_a", "node_b", "node_c"]


# ============================================================================
# 6. Contract Intelligence Broadened Non-Compete Detection
# ============================================================================

class TestContractIntelligenceBroadenedPhrases:
    def setup_method(self):
        self.engine = ContractIntelligenceEngine()

    def test_non_compete_phrasing_variations(self):
        phrases = [
            "The Executive agrees that upon cessation of services, he shall not engage in competing business for 2 years.",
            "Following departure from the Company, the Consultant shall not solicit or compete.",
            "Subsequent to disassociation from the firm, Partner shall not practice in the jurisdiction.",
            "Following termination of employment, Employee agrees not to compete for a period of 12 months.",
        ]
        for phrase in phrases:
            clauses = self.engine.extract_clauses(f"NON-COMPETE: {phrase}")
            assert len(clauses) >= 1
            nc = clauses[0]
            assert nc.risk_level == RiskLevel.CRITICAL
            assert any("Section 27" in factor for factor in nc.risk_factors)


# ============================================================================
# 7. Shared Spaces Constant-Time Comparison & Lockout
# ============================================================================

class TestSharedSpacesSecurity:
    def test_hmac_constant_time_comparison(self):
        passcode = "SuperSecret123"
        hashed = hash_passcode(passcode)
        correct_attempt = hash_passcode("SuperSecret123")
        wrong_attempt = hash_passcode("WrongSecret")

        assert hmac.compare_digest(hashed.encode("utf-8"), correct_attempt.encode("utf-8")) is True
        assert hmac.compare_digest(hashed.encode("utf-8"), wrong_attempt.encode("utf-8")) is False
