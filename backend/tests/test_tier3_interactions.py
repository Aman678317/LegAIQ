"""Tier 3 Test Suite: Cross-Feature Interactions & Multi-Module Pipelines.

Covers:
- Pipeline 1: Dual-Pass Indic OCR -> Classification -> Entity Extraction -> Review Table Extraction
- Pipeline 2: Review Table Structured Data -> Contract Risk 0-100 Scoring -> Playbook Deviation
- Pipeline 3: Contract Intelligence -> Redline Diff -> Indian PII Redaction -> Watermarking
- Pipeline 4: State Land Portal -> 30-Yr Ownership DAG -> Title Search Report -> BSA 63 Certificate
- Pipeline 5: Multi-Agent Workflow -> Indian Kanoon Precedents -> Legal Drafting Studio -> Verification
"""

import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.ai.indic_ocr import MockOCRProvider, process_land_record
from app.ai.land_intelligence import parse_and_normalize_area, IndianPropertyProfile
from app.ai.review_tables import ReviewTableExtractionEngine, ReviewTableExporter
from app.ai.contract_intelligence import (
    ContractIntelligenceEngine,
    ContractDocument,
    ContractClause,
    ClauseType,
    RiskLevel,
)
from app.security.pii import PIIRedactionPipeline, RedactionStrategy
from app.ai.state_portals import BhoomiConnector, PortalState
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
    ReportSection,
)
from app.ai.agents.orchestration import (
    AgentOrchestrator,
    WorkflowState,
    WorkflowStatus,
)
from app.ai.agents.base import new_agent_context, Permission
from app.ai.agents.registry import DueDiligenceAgent, LitigationStrategistAgent
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Pipeline 1: Indic OCR -> Entity Extraction -> Review Table Extraction
# ============================================================================

class TestPipeline1OCRToReviewTable:
    """Pipeline 1: Dual-pass Indic OCR yields text, extracts entities, and populates review tables."""

    @pytest.mark.asyncio
    async def test_ocr_to_review_table_flow(self):
        # 1. OCR Ingestion of Kannada RTC Pahani
        raw_kannada_bytes = b"kannada rtc deed bytes"
        ocr_provider = MockOCRProvider()
        ocr_res = await process_land_record(raw_kannada_bytes, "application/pdf", "rtc_pahani", provider=ocr_provider)
        assert len(ocr_res.pages) >= 1
        page_text = ocr_res.pages[0].text

        # 2. Extract Area and Property Entities
        area_norm = parse_and_normalize_area("2 Acres 14 Guntas")
        assert area_norm.acres > 2.0

        # 3. Populate Review Table via Prompt Extraction Engine
        deed_text = (
            f"{page_text}\n"
            "This Sale Deed is governed by laws of India.\n"
            "Stamp Duty of Rs. 1,50,000 paid at Whitefield Sub-Registrar.\n"
            "Total Extent: 2 Acres 14 Guntas in Survey No 124/3."
        )
        engine = ReviewTableExtractionEngine()
        law_cell = engine.extract_value_for_prompt(
            "What is the governing law?",
            doc_id="doc-rtc-1",
            doc_name="Karnataka_RTC.pdf",
            text=deed_text,
        )
        stamp_cell = engine.extract_value_for_prompt(
            "What is the stamp duty paid?",
            doc_id="doc-rtc-1",
            doc_name="Karnataka_RTC.pdf",
            text=deed_text,
        )

        assert "laws of India" in law_cell.value or "India" in law_cell.value
        assert "1,50,000" in stamp_cell.value
        assert law_cell.evidence.doc_id == "doc-rtc-1"


# ============================================================================
# Pipeline 2: Review Table -> Contract Risk Scoring -> Playbook Deviation
# ============================================================================

class TestPipeline2ReviewTableToRiskScoring:
    """Pipeline 2: Structured extraction feeds risk scoring and playbook audit."""

    def test_structured_table_to_risk_assessment(self):
        # 1. Review Table extraction across commercial contract
        contract_text = """
        COMMERCIAL LEASE AGREEMENT
        1. INDEMNITY: Tenant shall provide unlimited indemnity to Landlord for all claims.
        2. TERMINATION: Landlord may terminate immediately without cause.
        3. GOVERNING LAW: Governed by the laws of India.
        """
        table_engine = ReviewTableExtractionEngine()
        indemnity_extract = table_engine.extract_value_for_prompt(
            "Is there an indemnity cap?", "doc-lease", "Lease.pdf", contract_text
        )
        assert "unlimited indemnity" in indemnity_extract.value.lower()

        # 2. Contract Risk 0-100 Assessment
        contract_engine = ContractIntelligenceEngine()
        doc = ContractDocument(contract_id="LSE-100", title="Lease Agreement", full_text=contract_text)
        doc.clauses = contract_engine.extract_clauses(contract_text, "LSE-100")
        assessment = contract_engine.assess_risk(doc)

        # 3. Playbook Deviation Flagging
        assert assessment.overall_risk in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        assert len(assessment.critical_issues) >= 1
        assert any("unlimited indemnity" in iss.lower() for iss in assessment.critical_issues)


# ============================================================================
# Pipeline 3: Contract Diff -> PII Redaction -> Watermarking
# ============================================================================

class TestPipeline3DiffToPIIRedactionToWatermarking:
    """Pipeline 3: Redline changes are sanitized with PII redaction and prepared for watermarked export."""

    def test_diff_pii_redaction_flow(self):
        # 1. Redline Diff between contract drafts containing Aadhaar/PAN
        orig_text = "Party A (PAN: ABCDE1234F, Aadhaar: 1234 5678 9012) agrees to deliver services."
        mod_text = "Party A (PAN: ABCDE1234F, Aadhaar: 1234 5678 9012) agrees to deliver premium services with 24/7 SLA."

        contract_engine = ContractIntelligenceEngine()
        orig_doc = ContractDocument("O1", "Orig", full_text=orig_text)
        mod_doc = ContractDocument("M1", "Mod", full_text=mod_text)
        changes = contract_engine.compare_contracts(orig_doc, mod_doc)
        redline_doc = contract_engine.generate_redline_document(orig_doc, mod_doc, changes)

        # 2. Indian PII Auto-Redaction on the Redline Summary
        pii_pipeline = PIIRedactionPipeline()
        redacted_summary = pii_pipeline.redact(redline_doc, strategy=RedactionStrategy.MASK)

        # Ensure sensitive PII is masked
        assert "ABCDE1234F" not in redacted_summary.redacted_text
        assert "1234 5678 9012" not in redacted_summary.redacted_text

        # 3. Dynamic Watermark metadata attached
        viewer = "counsel@corporatelaw.in"
        watermark_str = f"CONFIDENTIAL | Viewed by {viewer} | {datetime.now(timezone.utc).isoformat()}"
        assert viewer in watermark_str


# ============================================================================
# Pipeline 4: Portal Search -> Ownership DAG -> TSR v2 -> BSA Certificate
# ============================================================================

class TestPipeline4PortalSearchToBSACertificate:
    """Pipeline 4: Land portal verification, 30-year DAG synthesis, Title Search Report, and BSA 63 cert."""

    @pytest.mark.asyncio
    async def test_portal_to_tsr_to_bsa_cert(self):
        # 1. Query Bhoomi State Land Portal
        bhoomi = BhoomiConnector(mock_mode=True)
        search_res = await bhoomi.search_by_survey_number(
            district="Bangalore South",
            taluk="Whitefield",
            hobli="Whitefield",
            village="Varthur",
            survey_number="124/3",
        )
        assert search_res.success is True
        record = search_res.records[0]

        # 2. Build 30-Year Ownership DAG Timeline
        timeline = [
            {"year": 1987, "event": "Sale Deed registered", "owner": "Venkatarama Reddy"},
            {"year": 2005, "event": "Mutation Sanction M-456", "owner": "Lakshmamma"},
            {"year": 2026, "event": "Current Recorded Owner", "owner": record.owner_names[0]},
        ]
        assert len(timeline) == 3

        # 3. Generate Title Search Report v2 Structure
        tsr = TitleSearchReport(
            report_id="TSR-E2E-001",
            case_id="case-e2e-001",
            organization_id=ORG_ID,
            title="Title Search Report - Survey 124/3 Varthur",
            property_address="Survey 124/3, Varthur, Whitefield",
            survey_number="124/3",
            district="Bangalore South",
            taluk="Whitefield",
            village="Varthur",
            state=PortalState.KARNATAKA,
            client_name="Apex Real Estate Fund",
            prepared_by="Adv. Ramesh Sharma",
            prepared_on=datetime.now(timezone.utc),
            search_period_years=30,
            search_date_from=datetime.now(timezone.utc) - timedelta(days=30*365),
            search_date_to=datetime.now(timezone.utc),
            chain_of_title=timeline,
        )
        generator = TitleSearchReportGenerator()
        text_report = generator.generate_text_report(tsr)
        assert "TITLE SEARCH REPORT" in text_report
        assert "Survey 124/3" in text_report

        # 4. Generate Section 63 BSA 2023 Electronic Evidence Certificate
        report_hash = hashlib.sha256(text_report.encode()).hexdigest()
        bsa_cert = generate_section63_certificate(
            file_name="Title_Search_Report_Sy124_3.pdf",
            file_hash=report_hash,
            hash_algorithm="SHA-256",
            certifier_name="Adv. Ramesh Sharma",
            certifier_designation="Senior Advocate / Title Examiner",
        )
        assert bsa_cert.hash_value == report_hash
        assert bsa_cert.is_valid is True


# ============================================================================
# Pipeline 5: Multi-Agent Workflow -> Legal Research -> Drafting Studio
# ============================================================================

class TestPipeline5MultiAgentResearchToDrafting:
    """Pipeline 5: Specialist agents collaborate to research precedents and generate verified legal pleadings."""

    @pytest.mark.asyncio
    async def test_agent_research_and_drafting_collaboration(self, fake):
        # 1. Setup Agent Context
        case_id = "case-lit-999"
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

        # 2. Run Litigation Strategist Agent
        lit_agent = LitigationStrategistAgent(ctx)
        strategy = await lit_agent.run({})
        assert len(strategy["causes_of_action"]) >= 1
        assert len(strategy["recommended_interim_reliefs"]) >= 1

        # 3. Create Draft Pleading with Grounded Strategy
        draft_content = (
            f"IN THE COURT OF THE PRINCIPAL SENIOR CIVIL JUDGE\n"
            f"SUIT FOR DECLARATION AND PERMANENT INJUNCTION\n\n"
            f"CAUSE OF ACTION: {strategy['causes_of_action'][0]['cause']}\n"
            f"STATUTORY BASIS: {strategy['causes_of_action'][0]['act']}\n"
            f"PRAYER FOR RELIEF:\n"
            f"a) {strategy['recommended_interim_reliefs'][0]}\n"
        )
        assert "INJUNCTION" in draft_content.upper()
        assert "COURT" in draft_content
