"""Comprehensive Hermetic Tests for Milestone 1 & 2:
- Milestone 1 (R1): Assistant & Chat Workspace (3-mode switcher, SSE streaming, multi-LLM, India context toggle)
- Milestone 2 (R2): Secure Matter Vault & Indic Document Intelligence (Dual-pass Indic OCR, DOCX/XLSX parsing, classification badges, entity extraction, side-by-side version comparison)
"""
import io
import json
import zipfile
import pytest
from tests.conftest import ADMIN_USER_ID, ORG_ID, USER_ID

API = "/api/v1"


class TestMilestone1AssistantWorkspace:
    """Test Assistant & Chat Workspace: 3-mode switcher, India context, multi-LLM, citations."""

    @pytest.fixture
    def active_case(self, api_client, fake):
        res = api_client.post(f"{API}/cases", json={
            "name": "Whitefield Property Dispute & Title Audit",
            "case_type": "PROPERTY",
            "organization_id": ORG_ID,
            "jurisdiction_state": "Karnataka",
        })
        assert res.status_code == 200
        case_id = res.json()["id"]

        # Seed document and chunks
        doc_id = "doc-deed-1987"
        fake.tables.rows("documents").append({
            "id": doc_id,
            "case_id": case_id,
            "file_name": "Sale_Deed_1987.pdf",
            "file_type": "application/pdf",
            "badge_label": "Sale Deed",
            "badge_color": "emerald",
            "status": "COMPLETED",
            "uploaded_by": USER_ID,
        })
        fake.tables.rows("document_pages").append({
            "id": "page-1",
            "document_id": doc_id,
            "page_number": 1,
            "text": "THIS SALE DEED executed on 12/03/1987 by Venkatarama Reddy in favour of Lakshmamma for consideration Rs. 45,000.",
            "language": "en",
            "confidence": 0.96,
        })
        fake.tables.rows("document_pages").append({
            "id": "page-2",
            "document_id": doc_id,
            "page_number": 2,
            "text": "SCHEDULE: Sy. No. 124/3 measuring 2 Acres 14 Guntas in Varthur Village, Whitefield Hobli.",
            "language": "en",
            "confidence": 0.94,
        })

        return case_id

    def test_mode_switcher_ask_mode(self, api_client, active_case):
        """Ask mode should provide direct, crisp legal answer with citations."""
        res = api_client.post(f"{API}/cases/{active_case}/questions", json={
            "question": "Who is the vendor and what is the consideration in the 1987 sale deed?",
            "mode": "ask",
            "india_context": True,
            "model": "claude-3-5-sonnet",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "assistant"
        assert data["mode"] == "ask"
        assert "content" in data
        assert len(data["content"]) > 0

    def test_mode_switcher_analyze_mode(self, api_client, active_case):
        """Analyze mode should produce deep FIRAC legal analysis."""
        res = api_client.post(f"{API}/cases/{active_case}/questions", json={
            "question": "Analyze title validity and encumbrance risks under Transfer of Property Act.",
            "mode": "analyze",
            "india_context": True,
            "model": "gpt-4o",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "assistant"
        assert data["mode"] == "analyze"
        assert "content" in data

    def test_mode_switcher_draft_mode(self, api_client, active_case):
        """Draft mode should produce formal court-ready legal draft."""
        res = api_client.post(f"{API}/cases/{active_case}/questions", json={
            "question": "Draft a legal notice under Section 106 of Transfer of Property Act 1882.",
            "mode": "draft",
            "india_context": True,
            "model": "deepseek-r1",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "assistant"
        assert data["mode"] == "draft"
        assert "content" in data

    def test_india_context_toggle_injects_statutes(self, api_client, active_case):
        """When india_context is True, Indian statutory framework is enabled."""
        res = api_client.post(f"{API}/cases/{active_case}/questions", json={
            "question": "What is the penalty for fraudulent execution under BNS 2023 vs IPC?",
            "mode": "analyze",
            "india_context": True,
            "model": "llama3.1:70b",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["content"]

    def test_query_stream_sse_endpoint(self, api_client, active_case):
        """Direct /chat/query-stream endpoint matching PROJECT.md interface contract."""
        res = api_client.post(f"{API}/chat/query-stream", json={
            "case_id": active_case,
            "query": "What is the survey number in the schedule property?",
            "mode": "ask",
            "india_context": True,
            "model": "claude-3-5-sonnet",
        })
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "data:" in res.text
        assert "[DONE]" in res.text


class TestMilestone2VaultAndIndicIntelligence:
    """Test Secure Matter Vault, Multi-format ingestion, Dual-pass OCR & Classification."""

    @pytest.fixture
    def test_case(self, api_client):
        res = api_client.post(f"{API}/cases", json={
            "name": "Deed Vault Matter",
            "case_type": "PROPERTY",
            "organization_id": ORG_ID,
        })
        return res.json()["id"]

    def test_multi_format_docx_ingestion(self, api_client, test_case):
        """Test DOCX file ingestion and automated paragraph extraction."""
        from app.ai.document_parser import IngestionEngine, IndianLegalDocumentClassifier

        # Generate a valid mock DOCX in memory
        docx_buf = io.BytesIO()
        with zipfile.ZipFile(docx_buf, "w") as z:
            doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>ABSOLUTE SALE DEED</w:t></w:r></w:p>
                    <w:p><w:r><w:t>VENDOR: Ramesh Kumar S/o Suresh Kumar</w:t></w:r></w:p>
                    <w:p><w:r><w:t>VENDEE: Anand Sharma S/o Mohan Sharma</w:t></w:r></w:p>
                    <w:p><w:r><w:t>SCHEDULE: Survey No. 89/1 measuring 1 Acre 20 Guntas, Whitefield.</w:t></w:r></w:p>
                </w:body>
            </w:document>"""
            z.writestr("word/document.xml", doc_xml)

        pages = IngestionEngine.parse_docx(docx_buf.getvalue(), "commercial_sale_deed.docx")
        assert len(pages) >= 1
        assert "ABSOLUTE SALE DEED" in pages[0].text
        assert "Survey No. 89/1" in pages[0].text

        doc_type, badge, color, conf = IndianLegalDocumentClassifier.classify(pages[0].text, "commercial_sale_deed.docx")
        assert doc_type == "sale_deed"
        assert badge == "Sale Deed"
        assert color == "emerald"
        assert conf >= 0.70

    def test_multi_format_xlsx_ingestion(self, api_client, test_case):
        """Test XLSX spreadsheet ingestion and table row extraction."""
        from app.ai.document_parser import IngestionEngine

        xlsx_buf = io.BytesIO()
        with zipfile.ZipFile(xlsx_buf, "w") as z:
            ss_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
                <si><t>Survey No</t></si>
                <si><t>Area Extent</t></si>
                <si><t>124/3</t></si>
                <si><t>2 Acres 14 Guntas</t></si>
            </sst>"""
            sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                <sheetData>
                    <row r="1">
                        <c r="A1" t="s"><v>0</v></c>
                        <c r="B1" t="s"><v>1</v></c>
                    </row>
                    <row r="2">
                        <c r="A2" t="s"><v>2</v></c>
                        <c r="B2" t="s"><v>3</v></c>
                    </row>
                </sheetData>
            </worksheet>"""
            z.writestr("xl/sharedStrings.xml", ss_xml)
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

        pages = IngestionEngine.parse_xlsx(xlsx_buf.getvalue(), "land_records_schedule.xlsx")
        assert len(pages) >= 1
        assert "Survey No" in pages[0].text
        assert "124/3" in pages[0].text

    def test_indian_legal_classification_badges(self):
        """Verify automatic classification across major Indian document formats."""
        from app.ai.document_parser import IndianLegalDocumentClassifier

        test_cases = [
            ("गावनिहाय सातबारा उतारा गाव नमुना ७ आणि १२ खाते क्रमांक ४५६", "7_12_extract.pdf", "7_12_extract", "7/12 Extract"),
            ("ಕರ್ನಾಟಕ ಸರ್ಕಾರ ಕಂದಾಯ ಇಲಾಖೆ ಪಹಣಿ ಆರ್‌ಟಿಸಿ ನಮೂನೆ ೧೬ ಸರ್ವೆ ನಂಬರ್ ೧೨೪/೩", "rtc_record.pdf", "rtc_pahani", "RTC / Pahani"),
            ("DEED OF PARTITION between coparceners dividing Schedule A and B", "partition.pdf", "partition_deed", "Partition Deed"),
            ("DEED OF GIFT executed out of natural love and affection without monetary consideration", "gift.pdf", "gift_deed", "Gift Deed"),
            ("INDENTURE OF LEASE for commercial demised premises monthly rent Rs 50,000", "lease.pdf", "lease_deed", "Lease Deed"),
            ("IN THE HIGH COURT OF KARNATAKA WRIT PETITION ORDER XXXIX", "court_injunction.pdf", "court_order", "Court Order"),
            ("ENCUMBRANCE CERTIFICATE FORM NO 15 search period 30 years Nil Encumbrance", "ec.pdf", "encumbrance_certificate", "Encumbrance Certificate"),
        ]

        for sample_text, filename, expected_type, expected_badge in test_cases:
            doc_type, badge, color, conf = IndianLegalDocumentClassifier.classify(sample_text, filename)
            assert doc_type == expected_type
            assert badge == expected_badge
            assert conf >= 0.70

    def test_party_and_entity_extraction(self):
        """Verify entity extractor retrieves Grantor, Grantee, Survey No, Area, Consideration, SRO."""
        from app.ai.document_parser import IndianLegalDocumentClassifier

        sample_deed = """
        THIS SALE DEED is executed on 14th July 1995 before Sub-Registrar Whitefield.
        VENDOR: Venkatarama Reddy S/o Late Krishnappa
        VENDEE: Anand Prakash S/o Ram Prakash
        SCHEDULE PROPERTY: All that piece and parcel of land bearing Sy. No. 124/3 measuring an area of 2 Acres 14 Guntas.
        CONSIDERATION: For a total consideration of Rs. 1,50,000 (Rupees One Lakh Fifty Thousand).
        Registered as Doc No. 1245/1995-96.
        """

        entities = IndianLegalDocumentClassifier.extract_entities(sample_deed)
        assert len(entities["grantors"]) >= 1
        assert "Venkatarama Reddy" in entities["grantors"][0]
        assert len(entities["grantees"]) >= 1
        assert "Anand Prakash" in entities["grantees"][0]
        assert "124/3" in entities["survey_numbers"]
        assert "2 Acres 14 Guntas" in entities["area"]
        assert "1,50,000" in entities["consideration_amount"]
        assert "1245/1995-96" in entities["registration_number"]

    def test_document_ocr_view_endpoint(self, api_client, test_case, fake):
        """Test GET /cases/{case_id}/documents/{document_id}/ocr-view with Indic layers."""
        doc_id = "doc-ocr-view-1"
        fake.tables.rows("documents").append({
            "id": doc_id,
            "case_id": test_case,
            "file_name": "kannada_partition_deed.pdf",
            "file_type": "application/pdf",
            "badge_label": "Partition Deed",
            "badge_color": "purple",
            "status": "COMPLETED",
            "uploaded_by": USER_ID,
        })
        fake.tables.rows("document_pages").append({
            "id": "page-p1",
            "document_id": doc_id,
            "page_number": 1,
            "text": "ವಿಭಾಗ ಪತ್ರ ದಿನಾಂಕ 15/06/2004 [UNCERTAIN: ಸರ್ವೆ ನಂ. 124/2 (conf: 52%)]",
            "language": "kn",
            "confidence": 0.91,
        })

        res = api_client.get(f"{API}/cases/{test_case}/documents/{doc_id}/ocr-view")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == doc_id
        assert data["total_pages"] == 1
        assert len(data["supported_indic_languages"]) == 13
        assert data["preprocessing"]["clahe_contrast_enhancement"] is True
        assert data["preprocessing"]["deskew_correction"] is True
        assert data["uncertain_token_count"] >= 1

    def test_side_by_side_direct_comparison(self, api_client, test_case, fake):
        """Test POST /cases/{case_id}/compare-direct computing word diff and field comparisons."""
        doc1_id = "doc-comp-1"
        doc2_id = "doc-comp-2"

        fake.tables.rows("documents").append({
            "id": doc1_id, "case_id": test_case, "file_name": "Sale_Deed_1987.pdf",
            "file_type": "application/pdf", "status": "COMPLETED", "uploaded_by": USER_ID,
        })
        fake.tables.rows("documents").append({
            "id": doc2_id, "case_id": test_case, "file_name": "Partition_Deed_2004.pdf",
            "file_type": "application/pdf", "status": "COMPLETED", "uploaded_by": USER_ID,
        })

        fake.tables.rows("document_pages").append({
            "id": "p1", "document_id": doc1_id, "page_number": 1,
            "text": "Sale Deed 1987 Survey No 124/3 2 Acres 14 Guntas", "language": "en", "confidence": 0.95,
        })
        fake.tables.rows("document_pages").append({
            "id": "p2", "document_id": doc2_id, "page_number": 1,
            "text": "Partition Deed 2004 Survey No 124/2 1 Acre 7 Guntas", "language": "en", "confidence": 0.95,
        })

        fake.tables.rows("extracted_entities").append({
            "id": "e1", "case_id": test_case, "document_id": doc1_id, "entity_type": "survey_number", "value": "124/3",
        })
        fake.tables.rows("extracted_entities").append({
            "id": "e2", "case_id": test_case, "document_id": doc2_id, "entity_type": "survey_number", "value": "124/2",
        })

        res = api_client.post(f"{API}/cases/{test_case}/compare-direct", json={
            "document_ids": [doc1_id, doc2_id],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["doc_a"]["id"] == doc1_id
        assert data["doc_b"]["id"] == doc2_id
        assert len(data["diff_chunks"]) > 0
        assert any(fc["field_name"] == "Survey Number" and fc["verdict"] == "MISMATCH" for fc in data["field_comparisons"])
