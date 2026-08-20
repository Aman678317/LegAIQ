"""Tier 1 Test Suite: Review Tables & Structured Extraction (Features 9-12).

Covers:
- Feature 9: Review Tables Backend & Prompt-Driven Extraction
- Feature 10: Interactive Review Table Schema & Dynamic Prompts
- Feature 11: Cell Evidence & Confidence Linking (BBox, Snippets, Page Map)
- Feature 12: Review Table OpenXML Excel & CSV Export
"""

import io
import zipfile
import pytest

from app.ai.review_tables import (
    CellEvidence,
    ExtractionResult,
    ReviewTableExtractionEngine,
    ReviewTableExporter,
)
from app.api.review_tables import (
    DEFAULT_LEGAL_COLUMNS,
    CreateColumnRequest,
    CreateReviewTableRequest,
    UpdateCellRequest,
    router as review_tables_router,
)
from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


# ============================================================================
# Feature 9: Review Tables Backend & Extraction
# ============================================================================

class TestFeature9ReviewTableExtraction:
    """Feature 9: Prompt-driven legal value extraction engine."""

    def setup_method(self):
        self.engine = ReviewTableExtractionEngine()

    def test_extract_governing_law_clause(self):
        """Governing law prompt extracts applicable legal jurisdiction."""
        text = (
            "14. GOVERNING LAW AND JURISDICTION\n"
            "This Agreement shall be governed by and construed in accordance with the substantive laws of India.\n"
            "The courts at Bengaluru, Karnataka shall have exclusive jurisdiction."
        )
        res = self.engine.extract_value_for_prompt(
            prompt="What is the governing law of this agreement?",
            doc_id="doc-001",
            doc_name="Master_Service_Agreement.pdf",
            text=text,
        )
        assert res.status == "completed"
        assert "laws of India" in res.value or "India" in res.value
        assert res.confidence_score >= 0.85
        assert res.evidence is not None
        assert res.evidence.doc_id == "doc-001"

    def test_extract_indemnity_cap_with_numeric_limit(self):
        """Indemnity prompt extracts liability limits."""
        text = (
            "8. INDEMNIFICATION\n"
            "Each party's aggregate indemnity liability shall be capped at INR 50,00,000 (Fifty Lakhs Rupees).\n"
        )
        res = self.engine.extract_value_for_prompt(
            prompt="Is there a monetary indemnity cap?",
            doc_id="doc-002",
            doc_name="Vendor_Agreement.pdf",
            text=text,
        )
        assert res.status == "completed"
        assert "INR 50,00,000" in res.value or "50,00,000" in res.value
        assert res.confidence_score >= 0.85

    def test_extract_termination_notice_period(self):
        """Termination prompt extracts time window for notice."""
        text = "Either party may terminate this Agreement by giving 60 days prior written notice."
        res = self.engine.extract_value_for_prompt(
            prompt="What is the termination notice period?",
            doc_id="doc-003",
            doc_name="Lease_Deed.pdf",
            text=text,
        )
        assert "60 days" in res.value
        assert res.confidence_score >= 0.85

    def test_extract_stamp_duty_amount(self):
        """Stamp duty prompt extracts stamp fees paid on instrument."""
        text = "This deed is executed on e-stamp paper bearing Certificate No. IN-KA1234567890 with Stamp Duty of Rs. 1,50,000 paid to Govt of Karnataka."
        res = self.engine.extract_value_for_prompt(
            prompt="What is the stamp duty amount?",
            doc_id="doc-004",
            doc_name="Sale_Deed.pdf",
            text=text,
        )
        assert "1,50,000" in res.value

    def test_missing_clause_returns_explicit_not_found(self):
        """When prompt asks for clause not present in document, returns structured Not Specified."""
        text = "Simple receipt for payment of electric bill."
        res = self.engine.extract_value_for_prompt(
            prompt="What is the non-compete restraint period?",
            doc_id="doc-005",
            doc_name="Receipt.pdf",
            text=text,
        )
        assert res.value == "Not Specified in Document"
        assert res.confidence_score <= 0.50


# ============================================================================
# Feature 10: Interactive Review Table Schema & Columns
# ============================================================================

class TestFeature10ReviewTableSchema:
    """Feature 10: Table and column definitions for interactive spreadsheet."""

    def test_default_legal_columns_count_and_types(self):
        """Default columns cover key commercial legal review dimensions."""
        assert len(DEFAULT_LEGAL_COLUMNS) >= 5
        col_names = [c["name"] for c in DEFAULT_LEGAL_COLUMNS]
        assert "Governing Law" in col_names
        assert "Jurisdiction" in col_names
        assert "Indemnity Cap" in col_names
        assert "Termination Notice" in col_names
        assert "Stamp Duty Paid" in col_names

    def test_create_column_request_validation(self):
        """CreateColumnRequest validates column metadata, model, and prompt."""
        col = CreateColumnRequest(
            name="RERA Registration",
            column_type="prompt",
            prompt="Extract the PRM/KA/RERA registration number",
            model="gpt-4o-mini",
            position=5,
        )
        assert col.name == "RERA Registration"
        assert col.column_type == "prompt"
        assert col.position == 5

    def test_create_review_table_request_structure(self):
        """CreateReviewTableRequest accepts custom column lists."""
        table_req = CreateReviewTableRequest(
            name="Commercial Lease Portfolio Review",
            description="Extraction table for 20 tech-park lease deeds in Bengaluru",
            columns=[
                CreateColumnRequest(name="Lock-in Period", prompt="What is the lock-in period?"),
                CreateColumnRequest(name="Security Deposit", prompt="How many months security deposit?"),
            ],
        )
        assert table_req.name == "Commercial Lease Portfolio Review"
        assert len(table_req.columns) == 2

    def test_update_cell_request_validation(self):
        """UpdateCellRequest accepts manual lawyer override with confidence score 1.0."""
        update = UpdateCellRequest(
            value="36 Months Lock-in",
            confidence_score=1.0,
            evidence={"doc_id": "doc-1", "doc_name": "Lease.pdf", "page_num": 4},
        )
        assert update.value == "36 Months Lock-in"
        assert update.confidence_score == 1.0


# ============================================================================
# Feature 11: Cell Evidence & Confidence Linking
# ============================================================================

class TestFeature11CellEvidenceLinking:
    """Feature 11: Grounding evidence, bounding box coordinates, and page mapping."""

    def test_cell_evidence_to_dict_schema(self):
        """CellEvidence serializes to API response with bbox coordinates."""
        evidence = CellEvidence(
            doc_id="doc-uuid-99",
            doc_name="Joint_Development_Agreement.pdf",
            page_num=12,
            text_snippet="...Developer shall share 45% of super built-up area...",
            bbox=[0.25, 0.10, 0.35, 0.85],
            char_start=4500,
            char_end=4560,
        )
        d = evidence.to_dict()
        assert d["doc_id"] == "doc-uuid-99"
        assert d["doc_name"] == "Joint_Development_Agreement.pdf"
        assert d["page_num"] == 12
        assert d["bbox"] == [0.25, 0.10, 0.35, 0.85]
        assert d["char_start"] == 4500
        assert d["char_end"] == 4560

    def test_page_number_mapping_multi_page(self):
        """Character offsets accurately resolve to the specific document page."""
        engine = ReviewTableExtractionEngine()
        pages = [
            {"page_number": 1, "text": "A" * 1000},
            {"page_number": 2, "text": "B" * 1000},
            {"page_number": 3, "text": "C" * 1000},
        ]
        # Char at 1500 is in page 2
        p_num = engine._find_page_number(pages, char_pos=1500, full_text="A"*1000 + "B"*1000 + "C"*1000)
        assert p_num == 2

    def test_snippet_builder_adds_context_padding(self):
        """Snippet builder wraps matched phrase with preceding and succeeding context."""
        engine = ReviewTableExtractionEngine()
        full_text = "Before context text. The vendor agrees to sell the property for Rs. 50,00,000. After context text."
        snip = engine._build_snippet(full_text, start=31, end=84, padding=15)
        assert "Rs. 50,00,000" in snip
        assert "sell the property" in snip


# ============================================================================
# Feature 12: Review Table Excel & CSV Export
# ============================================================================

class TestFeature12ReviewTableExport:
    """Feature 12: Formatted OpenXML XLSX and CSV export generation."""

    def test_export_csv_generation(self):
        """CSV export outputs valid CSV text with headers, values, and evidence."""
        columns = [
            {"id": "col-1", "name": "Governing Law"},
            {"id": "col-2", "name": "Indemnity Cap"},
        ]
        rows = [
            {
                "document_name": "Agreement_A.pdf",
                "cells": {
                    "col-1": {"value": "Laws of India", "confidence": 0.95, "evidence_snippet": "Clause 14"},
                    "col-2": {"value": "INR 10,00,000", "confidence": 0.90, "evidence_snippet": "Clause 8"},
                },
            },
            {
                "document_name": "Agreement_B.pdf",
                "cells": {
                    "col-1": {"value": "State of Karnataka", "confidence": 0.92, "evidence_snippet": "Clause 18"},
                    "col-2": {"value": "Unlimited", "confidence": 0.88, "evidence_snippet": "Clause 9"},
                },
            },
        ]

        csv_str = ReviewTableExporter.export_csv("Lease_Review", columns, rows)
        assert "Document Name,Governing Law,Indemnity Cap" in csv_str
        assert "Agreement_A.pdf,Laws of India,INR 10,00,000" in csv_str
        assert "Agreement_B.pdf,State of Karnataka,Unlimited" in csv_str

    def test_export_xlsx_produces_valid_openxml_zip(self):
        """XLSX export generates a valid OpenXML ZIP archive containing worksheet XML and styles."""
        columns = [
            {"id": "col-1", "name": "Document Type"},
            {"id": "col-2", "name": "Survey Number"},
            {"id": "col-3", "name": "Extent (Acres)"},
        ]
        rows = [
            {
                "document_name": "Sale_Deed_1987.pdf",
                "cells": {
                    "col-1": {"value": "Sale Deed", "confidence": 0.99, "evidence_snippet": "Title page"},
                    "col-2": {"value": "124/3", "confidence": 0.95, "evidence_snippet": "Schedule"},
                    "col-3": {"value": "2.35", "confidence": 0.92, "evidence_snippet": "Schedule"},
                },
            },
        ]

        xlsx_bytes = ReviewTableExporter.export_xlsx("Land_Title_Table", columns, rows)
        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 500

        # Verify it's a valid ZIP / XLSX structure
        bio = io.BytesIO(xlsx_bytes)
        with zipfile.ZipFile(bio, "r") as z:
            file_names = z.namelist()
            assert "[Content_Types].xml" in file_names
            assert "xl/workbook.xml" in file_names
            assert "xl/worksheets/sheet1.xml" in file_names
            assert "xl/styles.xml" in file_names
