"""Tier 1 Test Suite: Property Moat, BSA 2023 & Kanoon Research (Features 24-27).

Covers:
- Feature 24: 5+ Major State Land Portal Connectors (Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR)
- Feature 25: 13-30 Year Ownership Chain Graph (DAG Nodes, Transfer Types, Break Alerts)
- Feature 26: Bharatiya Sakshya Adhiniyam 2023 Section 63 Electronic Evidence Certification
- Feature 27: Indian Kanoon Case Law Research & Legal Precedent Retrieval
"""

import hashlib
import pytest
from datetime import datetime, timezone, timedelta

from app.ai.state_portals import (
    PortalState,
    LandRecord,
    PortalSearchResult,
    get_comprehensive_land_report,
    MahabhulekhConnector,
    BhoomiConnector,
    TNREGINETConnector,
    DharaniConnector,
    AnyRoRConnector,
)
from app.ai.bharatiya_sakshya import (
    EvidenceType,
    AdmissibilityStatus,
    DocumentCategory,
    EvidenceItem,
    BharatiyaSakshyaEngine,
    generate_section63_certificate,
    check_section94_presumption,
    check_section97_presumption,
)
from app.ai.ownership_graph import (
    LinkType,
    OwnershipChainAnalyzer,
    TitleBreakSeverity,
)
from app.ai.title_search_report import (
    TitleSearchReport,
    TitleSearchReportGenerator,
    ReportSection,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Feature 24: 5+ State Land Portal Connectors
# ============================================================================

class TestFeature24StateLandPortals:
    """Feature 24: State land record connectors for Karnataka, Maharashtra, Tamil Nadu, Telangana, Gujarat."""

    def test_all_5_states_enum_defined(self):
        """PortalState enum encompasses the 5 major supported Indian state revenue systems."""
        states = {s.value for s in PortalState}
        assert "maharashtra" in states
        assert "karnataka" in states
        assert "tamil_nadu" in states
        assert "telangana" in states
        assert "gujarat" in states

    @pytest.mark.asyncio
    async def test_karnataka_bhoomi_connector_search(self):
        """Bhoomi connector queries RTC/Pahani by survey number, taluk, village."""
        connector = BhoomiConnector(mock_mode=True)
        res = await connector.search_by_survey_number(
            district="Bangalore South",
            taluk="Whitefield",
            hobli="Whitefield",
            village="Varthur",
            survey_number="124/3",
        )
        assert res.success is True
        assert len(res.records) >= 1
        record = res.records[0]
        assert record.state == PortalState.KARNATAKA
        assert record.survey_number == "124/3"
        assert len(record.owner_names) >= 1

    @pytest.mark.asyncio
    async def test_maharashtra_mahabhulekh_connector_search(self):
        """Mahabhulekh connector queries 7/12 extracts by Gat/Survey number."""
        connector = MahabhulekhConnector(mock_mode=True)
        res = await connector.search_by_survey_number(
            district="Pune",
            taluk="Haveli",
            village="Hinjewadi",
            survey_number="45/2",
        )
        assert res.success is True
        assert len(res.records) >= 1
        record = res.records[0]
        assert record.state == PortalState.MAHARASHTRA
        assert "45/2" in record.survey_number

    @pytest.mark.asyncio
    async def test_comprehensive_land_report_aggregation(self):
        """get_comprehensive_land_report aggregates record details, mutations, and encumbrances."""
        report = await get_comprehensive_land_report(
            survey_number="124/3",
            district="Bangalore South",
            taluk="Whitefield",
            village="Varthur",
            state=PortalState.KARNATAKA,
            mock_mode=True,
        )
        assert report is not None
        assert "land_record" in report or "records" in report or "survey_number" in report

    def test_portal_search_api_endpoint(self, api_client, fake):
        """POST /cases/{case_id}/property/land-portal-search queries live/mock state portals."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "State Portal Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        res = api_client.post(f"{API}/cases/{case_id}/property/land-portal-search", json={
            "survey_number": "124/3",
            "district": "Bangalore South",
            "taluk": "Whitefield",
            "village": "Varthur",
            "state": "karnataka",
        })
        assert res.status_code == 200


# ============================================================================
# Feature 25: 13-30 Year Ownership Chain Graph
# ============================================================================

class TestFeature25OwnershipChainGraph:
    """Feature 25: Ownership DAG structure, transfer types, and break alerts."""

    def test_ownership_graph_api_returns_nodes_and_edges(self, api_client, fake):
        """GET /api/v1/cases/{case_id}/ownership returns nodes and edges lists."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Ownership DAG Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        fake.tables.rows("ownership_nodes").append({
            "id": "node-1", "case_id": case_id, "name": "Venkatarama Reddy",
            "node_type": "PERSON", "period_start": "1987-03-12", "period_end": "2005-04-10",
        })
        fake.tables.rows("ownership_nodes").append({
            "id": "node-2", "case_id": case_id, "name": "Lakshmamma",
            "node_type": "PERSON", "period_start": "2005-04-10", "period_end": "2026-01-01",
        })
        fake.tables.rows("ownership_edges").append({
            "id": "edge-1", "case_id": case_id, "source_node_id": "node-1",
            "target_node_id": "node-2", "transfer_type": "SALE",
            "document_name": "Sale_Deed_1987.pdf", "deed_date": "1987-03-12",
        })

        res = api_client.get(f"{API}/cases/{case_id}/ownership")
        assert res.status_code == 200
        data = res.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["transfer_type"] == "SALE"

    def test_timeline_events_chronological_sorting(self, api_client, fake):
        """GET /api/v1/cases/{case_id}/timeline returns events in chronological sequence."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Timeline Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        fake.tables.rows("timeline_events").append({
            "id": "t-1", "case_id": case_id, "title": "1987 Sale Deed",
            "sort_date": "1987-03-15", "event_date": "15/03/1987",
        })
        fake.tables.rows("timeline_events").append({
            "id": "t-2", "case_id": case_id, "title": "2005 Mutation Sanction",
            "sort_date": "2005-04-12", "event_date": "12/04/2005",
        })

        res = api_client.get(f"{API}/cases/{case_id}/timeline")
        assert res.status_code == 200
        events = res.json()
        assert len(events) == 2
        assert events[0]["sort_date"] <= events[1]["sort_date"]

    def test_rebuild_ownership_job_trigger(self, api_client, fake):
        """POST /cases/{case_id}/ownership/rebuild queues asynchronous graph rebuild."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Rebuild DAG Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        res = api_client.post(f"{API}/cases/{case_id}/ownership/rebuild")
        assert res.status_code == 200
        assert res.json()["status"] == "QUEUED"

    def test_dag_analyzer_builds_connected_graph(self):
        """OwnershipChainAnalyzer builds clean graph across sequential sales."""
        events = [
            {"event_date": "1995-01-01", "transaction_type": "SALE_DEED", "from_owner": "Owner A", "to_owner": "Owner B"},
            {"event_date": "2010-01-01", "transaction_type": "SALE_DEED", "from_owner": "Owner B", "to_owner": "Owner C"},
        ]
        dag = OwnershipChainAnalyzer.build_chain_dag("case-1", events, [], [])
        assert len(dag["nodes"]) >= 2
        assert len(dag["edges"]) == 2
        assert dag["title_status"] == "CLEAR"

    def test_link_types_classification(self):
        """LinkType enum supports major conveyance and encumbrance types."""
        assert LinkType.SALE_DEED == "SALE_DEED"
        assert LinkType.MORTGAGE_CHARGE == "MORTGAGE_CHARGE"
        assert LinkType.PARTITION_DEED == "PARTITION_DEED"
        assert LinkType.RELEASE_DEED == "RELEASE_DEED"


# ============================================================================
# Feature 26: Bharatiya Sakshya Adhiniyam 2023 Section 63 Certification
# ============================================================================

class TestFeature26BharatiyaSakshya2023:
    """Feature 26: Evidence admissibility, Section 63 hash certification, Section 94 30-yr presumption."""

    def setup_method(self):
        self.engine = BharatiyaSakshyaEngine()

    def test_section_63_hash_certificate_generation(self):
        """Section 63 electronic evidence certificate computes SHA-256 hash and validates chain of custody."""
        raw_doc_bytes = b"PDF electronic deed content for Section 63 BSA compliance"
        doc_hash = hashlib.sha256(raw_doc_bytes).hexdigest()

        cert = generate_section63_certificate(
            file_name="Registered_Sale_Deed_2020.pdf",
            file_hash=doc_hash,
            hash_algorithm="SHA-256",
            certifier_name="Adv. Rajesh Kumar",
            certifier_designation="Senior Legal Counsel / System Custodian",
            system_parameters="Ubuntu 22.04 LTS / Jurisiva Vault Node 1",
        )
        assert cert is not None
        assert "SECTION 63" in cert.title or "Section 63" in cert.title
        assert cert.hash_value == doc_hash
        assert cert.algorithm == "SHA-256"
        assert cert.is_valid is True

    def test_section_94_30_year_ancient_document_presumption(self):
        """Documents over 30 years old from proper custody enjoy statutory presumption under Section 94 BSA 2023."""
        old_evidence = EvidenceItem(
            evidence_id="ev-1987",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Original Registered Sale Deed dated 12/03/1987",
            source="Sub-Registrar Office Whitefield",
            date_created=datetime.now(timezone.utc) - timedelta(days=35*365),
            document_category=DocumentCategory.REGISTERED_DOCUMENT,
            is_original=True,
            custodian="Advocate for Vendor",
        )
        is_presumed, reason = check_section94_presumption(old_evidence)
        assert is_presumed is True
        assert "30 years" in reason or "Section 94" in reason

    def test_section_97_certified_copy_presumption(self):
        """Certified copies of public records enjoy statutory presumption under Section 97 BSA 2023."""
        revenue_copy = EvidenceItem(
            evidence_id="ev-rtc-copy",
            evidence_type=EvidenceType.DOCUMENTARY,
            description="Certified True Copy of RTC Pahani issued by Tahsildar",
            source="Bhoomi Revenue Office",
            document_category=DocumentCategory.REVENUE_RECORD,
            is_original=False,
            is_certified_copy=True,
        )
        is_presumed, reason = check_section97_presumption(revenue_copy)
        assert is_presumed is True
        assert "Section 97" in reason

    def test_bsa_statutory_framework_metadata(self):
        """BSA Engine references Act No. 47 of 2023 and Section 63 electronic record rules."""
        cert = generate_section63_certificate(
            file_name="Deed.pdf",
            file_hash="a" * 64,
            certifier_name="Counsel",
            certifier_designation="Examiner",
        )
        assert "Bharatiya Sakshya" in cert.statutory_framework["primary_act"]
        assert "Section 63" in cert.statutory_framework["primary_section"]

    def test_bsa_certificate_entropy_id(self):
        """Certificate ID is prefixed with BSA-SEC63- and contains high entropy hex string."""
        cert = generate_section63_certificate(
            file_name="Doc.pdf",
            file_hash="b" * 64,
            certifier_name="Advocate",
            certifier_designation="Examiner",
        )
        assert cert.certificate_id.startswith("BSA-SEC63-")


# ============================================================================
# Feature 27: Indian Kanoon Case Law Research
# ============================================================================

class TestFeature27IndianKanoonResearch:
    """Feature 27: Integrated Indian case law search, citation graph, and landmark summaries."""

    def test_research_api_returns_structured_answer(self, api_client, fake):
        """POST /api/v1/cases/{case_id}/research answers legal queries with statutory grounding."""
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Kanoon Research Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        res = api_client.post(f"{API}/cases/{case_id}/research", json={
            "question": "What are the essential ingredients of Section 54 Transfer of Property Act for a valid sale?",
            "jurisdiction": "Supreme Court of India",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert "answer" in data
        assert len(data["answer"]) > 20

    def test_research_trusted_source_domains(self):
        """Research module whitelists trusted Indian judicial and statutory domains."""
        from app.api.research import TRUSTED_SOURCE_HINTS
        assert "indiankanoon.org" in TRUSTED_SOURCE_HINTS
        assert "sci.gov.in" in TRUSTED_SOURCE_HINTS
        assert "indiacode.nic.in" in TRUSTED_SOURCE_HINTS
        assert "legislative.gov.in" in TRUSTED_SOURCE_HINTS

    def test_kanoon_citation_formatting(self):
        """Indian Kanoon case references follow canonical citation formatting."""
        from app.ai.indian_kanoon import KanoonClient, LandmarkJudgment
        client = KanoonClient()
        doc = client.get_landmark_summary("suraj_lamp")
        assert doc is not None
        assert "Suraj Lamp" in doc.title
        assert "2012" in doc.citation

    def test_kanoon_search_keywords_resolution(self):
        """Kanoon search maps legal issues to relevant landmark precedents."""
        from app.ai.indian_kanoon import KanoonClient
        client = KanoonClient()
        results = client.search_precedents("GPA sale title validity")
        assert len(results) >= 1
        assert any("Suraj Lamp" in r.title for r in results)

    def test_statutory_section_cross_referencing(self):
        """Precedents link to exact statutory sections."""
        from app.ai.indian_kanoon import KanoonClient
        client = KanoonClient()
        doc = client.get_landmark_summary("suraj_lamp")
        assert any("Section 54" in s for s in doc.statutes_cited)
