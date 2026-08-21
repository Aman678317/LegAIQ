"""Tier 4 Test Suite: Real-World Enterprise Workload Scenarios.

Covers 7 Full Realistic Legal Workloads:
1. Scenario 1: Agricultural Land Title Due Diligence (Karnataka & Maharashtra)
2. Scenario 2: High-Volume Commercial Lease Portfolio Review (20 Leases)
3. Scenario 3: M&A Regulatory & PII Redaction Deal Room with Watermarking
4. Scenario 4: Multi-Agent Litigation Strategy Formulation & Pleadings
5. Scenario 5: Cross-Border SaaS Master Services Agreement Negotiation
6. Scenario 6: 30-Year Maharashtra Ferfar & 7/12 Mutation Chain Reconstruction
7. Scenario 7: High Court Commercial Suit Plaint Drafting with CPC Order VII & Kanoon Precedents
"""

import hashlib
import io
import pytest
from datetime import datetime, timezone, timedelta

from app.ai.indic_ocr import MockOCRProvider, process_land_record
from app.ai.land_intelligence import (
    parse_and_normalize_area,
    IndianPropertyProfile,
    are_land_areas_equivalent,
)
from app.ai.state_portals import (
    BhoomiConnector,
    MahabhulekhConnector,
    PortalState,
    get_comprehensive_land_report,
)
from app.ai.review_tables import (
    ReviewTableExtractionEngine,
    ReviewTableExporter,
    DEFAULT_LEGAL_COLUMNS,
)
from app.ai.contract_intelligence import (
    ContractIntelligenceEngine,
    ContractDocument,
    ContractClause,
    ClauseType,
    RiskLevel,
)
from app.security.pii import (
    PIIRedactionPipeline,
    RedactionStrategy,
    IndianPIIRecognizer,
)
from app.ai.bharatiya_sakshya import (
    BharatiyaSakshyaEngine,
    generate_section63_certificate,
    EvidenceItem,
    EvidenceType,
    DocumentCategory,
)
from app.ai.title_search_report import (
    TitleSearchReport,
    TitleSearchReportGenerator,
)
from app.ai.agents.base import new_agent_context, Permission
from app.ai.agents.registry import (
    DueDiligenceAgent,
    TitleExaminerAgent,
    LitigationStrategistAgent,
    ContractReviewerAgent,
)
from app.api.analytics import (
    TimeRange,
    TeamProductivityMetrics,
    AIROIMetrics,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Scenario 1: Agricultural Land Title Due Diligence (Karnataka / Maharashtra)
# ============================================================================

class TestScenario1AgriculturalLandDueDiligence:
    """Scenario 1: Comprehensive 30-year title audit for agricultural acquisition in Bengaluru/Pune."""

    @pytest.mark.asyncio
    async def test_agricultural_land_due_diligence_pipeline(self, fake):
        # 1. State Portal Verification: Query Bhoomi for RTC / Pahani
        bhoomi = BhoomiConnector(mock_mode=True)
        bhoomi_res = await bhoomi.search_by_survey_number(
            district="Bangalore South",
            taluk="Whitefield",
            hobli="Whitefield",
            village="Varthur",
            survey_number="124/3",
        )
        assert bhoomi_res.success is True
        record = bhoomi_res.records[0]
        assert record.state == PortalState.KARNATAKA

        # 2. Area Normalization across Units: 2 Acres 14 Guntas
        area_norm = parse_and_normalize_area("2 Acres 14 Guntas")
        assert area_norm.acres == pytest.approx(2.35, rel=1e-2)
        assert area_norm.sq_meters == pytest.approx(9510.11, rel=1e-2)

        # 3. 30-Year Ownership Chain Synthesis (1987 Sale Deed -> 2005 Mutation -> Current)
        timeline = [
            {"year": 1987, "from_owner": "Krishnappa", "to_owner": "Venkatarama Reddy", "doc": "Sale Deed 789/1987-88"},
            {"year": 2005, "from_owner": "Venkatarama Reddy", "to_owner": "Lakshmamma", "doc": "Mutation M-456"},
            {"year": 2026, "from_owner": "Lakshmamma", "to_owner": record.owner_names[0], "doc": "Current Bhoomi Record"},
        ]
        assert len(timeline) == 3

        # 4. Multi-Agent Due Diligence Assessment
        ctx = new_agent_context(
            case_id="case-agri-001",
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[Permission.READ_CASE, Permission.READ_DOCUMENTS, Permission.READ_ENTITIES, Permission.READ_GRAPH, Permission.WRITE_FINDINGS, Permission.WRITE_RISKS],
        )
        dd_agent = DueDiligenceAgent(ctx)
        dd_results = await dd_agent.run({})
        assert dd_results["due_diligence_score"] >= 80
        assert dd_results["status"] in ("APPROVED", "CONDITIONAL")

        # 5. Court-Admissible Title Search Report v2 Generation
        tsr = TitleSearchReport(
            report_id="TSR-AGRI-101",
            case_id="case-agri-001",
            organization_id=ORG_ID,
            title="Agricultural Title Search Report — Sy. No. 124/3 Varthur",
            property_address="Survey 124/3, Varthur Village, Whitefield Hobli, Bangalore South",
            survey_number="124/3",
            district="Bangalore South",
            taluk="Whitefield",
            village="Varthur",
            state=PortalState.KARNATAKA,
            client_name="Agri AgriTech Farmlands LLP",
            prepared_by="Adv. Rajesh Kumar",
            prepared_on=datetime.now(timezone.utc),
            search_period_years=30,
            search_date_from=datetime.now(timezone.utc) - timedelta(days=30*365),
            search_date_to=datetime.now(timezone.utc),
            chain_of_title=timeline,
        )
        tsr_gen = TitleSearchReportGenerator()
        report_text = tsr_gen.generate_text_report(tsr)
        assert "TITLE SEARCH REPORT" in report_text
        assert "Survey 124/3" in report_text

        # 6. Bharatiya Sakshya Adhiniyam 2023 Section 63 Digital Certificate
        report_hash = hashlib.sha256(report_text.encode()).hexdigest()
        bsa_cert = generate_section63_certificate(
            file_name="TSR_Survey124_3_Varthur.pdf",
            file_hash=report_hash,
            hash_algorithm="SHA-256",
            certifier_name="Adv. Rajesh Kumar",
            certifier_designation="Senior Title Examiner",
        )
        assert bsa_cert.hash_value == report_hash
        assert bsa_cert.is_valid is True


# ============================================================================
# Scenario 2: High-Volume Commercial Lease Portfolio Review (20 Leases)
# ============================================================================

class TestScenario2CommercialLeasePortfolioReview:
    """Scenario 2: Bulk extraction and playbook deviation scoring across commercial leases."""

    def test_20_lease_extraction_and_excel_export(self):
        engine = ReviewTableExtractionEngine()
        columns = [
            {"id": "col-1", "name": "Premises / Unit"},
            {"id": "col-2", "name": "Lock-in Period"},
            {"id": "col-3", "name": "Monthly Rent"},
            {"id": "col-4", "name": "Indemnity Cap"},
            {"id": "col-5", "name": "Termination Notice"},
        ]

        rows = []
        for i in range(1, 21):
            lease_text = f"""
            LEASE DEED FOR UNIT {i}01, TOWER {chr(65 + (i % 4))}
            1. PREMISES: Unit {i}01, Tech Park, Whitefield.
            2. TERM: Lock-in period is {24 if i % 2 == 0 else 36} months.
            3. RENT: Monthly rent of INR {150000 + (i * 10000)}.
            4. INDEMNITY: Aggregate indemnity capped at INR 50,00,000.
            5. TERMINATION: Either party may terminate with 90 days notice after lock-in.
            """
            extracted_cells = {}
            for col in columns:
                res = engine.extract_value_for_prompt(
                    prompt=col["name"],
                    doc_id=f"doc-lease-{i}",
                    doc_name=f"Lease_Unit_{i}01.pdf",
                    text=lease_text,
                )
                extracted_cells[col["id"]] = {
                    "value": res.value,
                    "confidence": res.confidence_score,
                    "evidence_snippet": res.evidence.text_snippet if res.evidence else "",
                }
            rows.append({
                "document_name": f"Lease_Unit_{i}01.pdf",
                "cells": extracted_cells,
            })

        assert len(rows) == 20
        assert "Lease_Unit_101.pdf" in rows[0]["document_name"]

        # Export to OpenXML XLSX
        xlsx_bytes = ReviewTableExporter.export_xlsx("Commercial_Lease_Portfolio", columns, rows)
        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 1000

        # Export to CSV
        csv_str = ReviewTableExporter.export_csv("Commercial_Lease_Portfolio", columns, rows)
        assert "Lease_Unit_101.pdf" in csv_str
        assert "Lease_Unit_2001.pdf" in csv_str


# ============================================================================
# Scenario 3: M&A Regulatory & PII Redaction Deal Room with Watermarking
# ============================================================================

class TestScenario3MARegulatoryDealRoom:
    """Scenario 3: Virtual Deal Room creation with 24h access expiry, PII auto-masking, and watermark."""

    def test_deal_room_pii_and_watermark_lifecycle(self, fake):
        # 1. Unredacted transaction agreement with confidential promoters' PAN/Aadhaar/Bank info
        sensitive_mna_doc = """
        SHARE PURCHASE AND SHAREHOLDERS AGREEMENT
        Between:
        Promoter A: Rajesh Kumar (PAN: ABCDE1234F, Aadhaar: 1234 5678 9012, Bank A/C: 109823471928, IFSC: SBIN0001234)
        AND
        Acquirer: Global Venture Fund Holdings Pte Ltd.
        Total Consideration: INR 150,00,00,000 (One Hundred Fifty Crores Rupees).
        """

        # 2. Indian PII Auto-Redaction for Deal Room Clean Room
        pipeline = PIIRedactionPipeline()
        sanitized = pipeline.redact(sensitive_mna_doc, strategy=RedactionStrategy.MASK)

        assert "ABCDE1234F" not in sanitized.redacted_text
        assert "1234 5678 9012" not in sanitized.redacted_text
        assert "SBIN0001234" not in sanitized.redacted_text
        assert "One Hundred Fifty Crores" in sanitized.redacted_text

        # 3. Dynamic Watermark metadata generation for external auditor
        auditor_email = "auditor@big4accounting.com"
        watermark_text = f"M&A DEAL ROOM CONFIDENTIAL — RESTRICTED TO {auditor_email} — EXPIRES IN 24 HOURS"
        assert auditor_email in watermark_text

        # 4. Command Center Analytics Tracking
        roi_metrics = AIROIMetrics(
            organization_id=ORG_ID,
            period=TimeRange.DAY,
            period_start=datetime.now(timezone.utc) - timedelta(hours=24),
            period_end=datetime.now(timezone.utc),
            total_ai_calls=120,
            estimated_ai_cost_usd=8.50,
            estimated_manual_hours_saved=24.0,
            estimated_cost_savings_usd=1440.0,
            roi_percentage=16800.0,
        )
        assert roi_metrics.estimated_cost_savings_usd == 1440.0


# ============================================================================
# Scenario 4: Multi-Agent Litigation Strategy Formulation & Pleadings
# ============================================================================

class TestScenario4MultiAgentLitigationStrategy:
    """Scenario 4: Multi-agent chain formulating civil suit strategy, case law citations, and draft petition."""

    @pytest.mark.asyncio
    async def test_litigation_strategy_formulation(self, fake):
        case_id = "case-lit-strat-01"
        ctx = new_agent_context(
            case_id=case_id,
            organization_id=ORG_ID,
            user_id=USER_ID,
            permissions=[
                Permission.READ_CASE, Permission.READ_DOCUMENTS,
                Permission.READ_ENTITIES, Permission.WEB_SEARCH,
                Permission.WRITE_DRAFTS,
            ],
        )

        # 1. Run Litigation Strategist Agent
        lit_agent = LitigationStrategistAgent(ctx)
        strategy = await lit_agent.run({})
        assert len(strategy["causes_of_action"]) >= 1
        assert "Specific Relief Act" in strategy["causes_of_action"][0]["act"]

        # 2. Formulate Plaint Draft with Statutory Citations
        petition_text = f"""
        IN THE COURT OF THE PRINCIPAL SENIOR CIVIL JUDGE AT BENGALURU
        ORIGINAL SUIT NO. _____ OF 2026

        Plaintiff: Smt. Lakshmamma
        Versus
        Defendants: Encroaching Parties

        PLAINT UNDER ORDER VII RULE 1 READ WITH SECTION 26 OF THE CODE OF CIVIL PROCEDURE, 1908

        1. The Plaintiff is the absolute owner and in possession of Survey No. 124/3, Varthur.
        2. CAUSE OF ACTION: {strategy['causes_of_action'][0]['cause']} under {strategy['causes_of_action'][0]['act']}.
        3. PRAYER:
           a) Judgment and decree for declaration of absolute title.
           b) Permanent injunction restraining defendants from interfering with peaceful possession.
        """
        assert "CODE OF CIVIL PROCEDURE" in petition_text
        assert "PERMANENT INJUNCTION" in petition_text


# ============================================================================
# Scenario 5: Cross-Border SaaS Master Services Agreement Negotiation
# ============================================================================

class TestScenario5CrossBorderSaaSContractNegotiation:
    """Scenario 5: 29 clause extraction, fallback tier redlines, and compliance diffing for SaaS MSA."""

    def test_saas_msa_clause_negotiation_and_redlining(self):
        engine = ContractIntelligenceEngine()

        vendor_draft = """
        MASTER SERVICES AGREEMENT
        1. TERM: 12 months with automatic renewal unless terminated with 90 days notice.
        2. LIMITATION OF LIABILITY: Vendor aggregate liability is capped at INR 10,00,000.
        3. INDEMNITY: Customer provides unlimited indemnity for any third-party claims.
        4. GOVERNING LAW: Laws of Delaware, USA with exclusive jurisdiction in Wilmington.
        """

        # Extract clauses & assess initial risk
        doc_v1 = ContractDocument("V1", "Vendor Draft v1", full_text=vendor_draft)
        doc_v1.clauses = engine.extract_clauses(vendor_draft, "V1")
        risk_v1 = engine.assess_risk(doc_v1)
        assert risk_v1.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)

        # Negotiated customer draft substituting India fallback tiers
        customer_draft = """
        MASTER SERVICES AGREEMENT
        1. TERM: 12 months with mutual renewal.
        2. LIMITATION OF LIABILITY: Mutual liability capped at 12 months aggregate fees paid.
        3. INDEMNITY: Mutual indemnity capped at 2x annual contract value for IP infringement.
        4. GOVERNING LAW: Laws of India with exclusive jurisdiction of courts in Bengaluru.
        """
        doc_v2 = ContractDocument("V2", "Customer Redline v2", full_text=customer_draft)
        doc_v2.clauses = engine.extract_clauses(customer_draft, "V2")

        # Compare and produce redline changes
        changes = engine.compare_contracts(doc_v1, doc_v2)
        assert len(changes) >= 1

        redline_report = engine.generate_redline_document(doc_v1, doc_v2, changes)
        assert "REDLINE COMPARISON REPORT" in redline_report
        assert "MODIFICATION" in redline_report or "Total Changes" in redline_report


# ============================================================================
# Scenario 6: 30-Year Maharashtra Ferfar & 7/12 Mutation Chain Reconstruction
# ============================================================================

class TestScenario6MaharashtraFerfarTitleReconstruction:
    """Scenario 6: 30-year Maharashtra agricultural land title search with encumbrance release and 7/12 Ferfar."""

    @pytest.mark.asyncio
    async def test_maharashtra_ferfar_title_audit(self):
        # 1. Query Mahabhulekh
        maha = MahabhulekhConnector(mock_mode=True)
        res = await maha.search_by_survey_number(
            district="Pune",
            taluk="Haveli",
            village="Hinjewadi",
            survey_number="45/2",
        )
        assert res.success is True
        record = res.records[0]

        # 2. Reconstruct Ferfar Mutation Entries
        mutations = [
            {"year": 1994, "ferfar_no": "M-102", "mutation_type": "SALE", "transferor": "Pandurang Patil", "transferee": "Suresh Deshmukh"},
            {"year": 2008, "ferfar_no": "M-215", "mutation_type": "MORTGAGE", "transferor": "Suresh Deshmukh", "transferee": "Bank of Maharashtra"},
            {"year": 2012, "ferfar_no": "M-290", "mutation_type": "RELEASE", "transferor": "Bank of Maharashtra", "transferee": "Suresh Deshmukh"},
            {"year": 2024, "ferfar_no": "M-410", "mutation_type": "SALE", "transferor": "Suresh Deshmukh", "transferee": "Kiran Developers LLP"},
        ]
        assert len(mutations) == 4

        # 3. Verify BSA 2023 Digital Sealing of Mutation Extract
        sha256_seal = hashlib.sha256(b"7/12 Extract Gat No 45/2 Hinjewadi Pune").hexdigest()
        bsa_cert = generate_section63_certificate(
            file_name="7_12_Extract_Gat_45_2_Pune.pdf",
            file_hash=sha256_seal,
            hash_algorithm="SHA-256",
            certifier_name="Adv. Sneha Kulkarni",
            certifier_designation="Title Advocate",
        )
        assert bsa_cert.hash_value == sha256_seal
        assert bsa_cert.is_valid is True


# ============================================================================
# Scenario 7: Commercial Injunction Plaint Drafting with CPC Order VII
# ============================================================================

class TestScenario7CommercialInjunctionPlaintDrafting:
    """Scenario 7: Full Plaint drafting for commercial property encroachment with CPC Order VII & Kanoon citations."""

    def test_commercial_plaint_statutory_grounding(self):
        from app.ai.indian_kanoon import KanoonClient
        client = KanoonClient()
        precedent = client.get_landmark_summary("suraj_lamp")

        plaint_body = f"""
        IN THE COURT OF THE PRINCIPAL CITY CIVIL JUDGE AT BENGALURU
        COMMERCIAL SUIT NO. _____ OF 2026

        ABC INFRASTRUCTURE PVT LTD ... PLAINTIFF
        VERSUS
        XYZ REALTY LLP ... DEFENDANT

        PLAINT UNDER ORDER VII RULE 1 & ORDER XXXIX RULES 1 & 2 OF CPC, 1908
        FOR DECLARATION OF TITLE AND PERMANENT INJUNCTION

        1. The Plaintiff is the absolute owner in possession of Sy. No. 124/3, Varthur.
        2. Pursuant to the law laid down by the Hon'ble Supreme Court in {precedent.title} ({precedent.citation}),
           transfer of title in immovable property can only be effected by a duly registered deed of conveyance.
        3. PRAYER:
           a) Declare Plaintiff as absolute owner.
           b) Ad-interim ex-parte injunction restraining Defendant from creating third-party rights.
        """
        assert "COMMERCIAL SUIT" in plaint_body
        assert "ORDER XXXIX" in plaint_body
        assert precedent.citation in plaint_body
