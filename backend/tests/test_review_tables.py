"""Comprehensive Tests for Review Tables Module (M3).

Tests extraction engine, evidence citations, confidence scoring, CSV/XLSX export,
and REST API CRUD operations.
"""

import io
import zipfile
import xml.etree.ElementTree as ET
import pytest
from uuid import uuid4

from app.ai.review_tables import (
    ReviewTableExtractionEngine,
    ReviewTableExporter,
    CellEvidence,
    ExtractionResult,
)


class TestReviewTableExtractionEngine:
    """Test AI prompt extraction engine logic and evidence grounding."""

    def setup_method(self):
        self.engine = ReviewTableExtractionEngine()

    def test_extract_governing_law_standard(self):
        """Extract governing law with high confidence and page evidence."""
        text = (
            "1. DEFINITIONS\nStandard terms.\n\n"
            "2. GOVERNING LAW AND JURISDICTION\n"
            "This Agreement shall be governed by the laws of India and subject to the exclusive jurisdiction of the courts at Bengaluru.\n"
        )
        pages = [{"page_number": 1, "text": text}]
        res = self.engine.extract_value_for_prompt("What is the Governing Law?", "doc-1", "Agreement.pdf", text, pages)

        assert res.status == "completed"
        assert res.confidence_score >= 0.8
        assert "India" in res.value or "laws of India" in res.value.lower()
        assert res.evidence is not None
        assert res.evidence.page_num == 1
        assert "India" in res.evidence.text_snippet

    def test_extract_indemnity_cap(self):
        """Extract indemnity cap specification."""
        text = (
            "INDEMNIFICATION CLAUSE\n"
            "Vendor shall indemnify Client against third party losses. The total aggregate liability under this indemnity shall be capped at INR 50,00,000.\n"
        )
        res = self.engine.extract_value_for_prompt("Indemnity Cap", "doc-1", "Vendor.docx", text)
        assert res.status == "completed"
        assert "50,00,000" in res.value or "INR" in res.value
        assert res.confidence_score >= 0.8

    def test_extract_termination_notice_period(self):
        """Extract termination notice period in days."""
        text = (
            "TERMINATION\n"
            "Either party may terminate this Agreement by giving 30 days prior written notice to the other party.\n"
        )
        res = self.engine.extract_value_for_prompt("Termination Notice Period", "doc-1", "Contract.pdf", text)
        assert "30 days" in res.value.lower()
        assert res.confidence_score >= 0.8

    def test_extract_stamp_duty_paid(self):
        """Extract stamp duty payment details."""
        text = (
            "SALE DEED\n"
            "This instrument is duly executed with stamp duty paid of Rs. 75,000 before the Sub-Registrar.\n"
        )
        res = self.engine.extract_value_for_prompt("Stamp Duty Paid", "doc-1", "SaleDeed.pdf", text)
        assert "75,000" in res.value or "75000" in res.value
        assert res.confidence_score >= 0.8

    def test_extract_non_compete_duration(self):
        """Extract non-compete duration and covenant."""
        text = (
            "RESTRICTIVE COVENANTS\n"
            "The employee covenants not to compete for a period of 12 months post-termination in India.\n"
        )
        res = self.engine.extract_value_for_prompt("Non-Compete Duration", "doc-1", "Employment.pdf", text)
        assert "12 months" in res.value.lower() or "12" in res.value

    def test_custom_prompt_keyword_fallback(self):
        """Extract values for custom prompt using keyword heuristic fallback."""
        text = (
            "AUDIT RIGHTS\n"
            "The Client may audit the books and records once every financial year with 14 days notice.\n"
        )
        res = self.engine.extract_value_for_prompt("What are the audit rights?", "doc-1", "Agreement.pdf", text)
        assert res.status == "completed"
        assert "audit" in res.value.lower()
        assert res.confidence_score > 0.5

    def test_empty_document_handling(self):
        """Gracefully handle empty document text."""
        res = self.engine.extract_value_for_prompt("Governing Law", "doc-empty", "Empty.pdf", "")
        assert res.status == "not_found"
        assert res.confidence_score == 0.0
        assert "empty" in res.value.lower() or "n/a" in res.value.lower()

    def test_multi_page_mapping(self):
        """Verify page number mapping in multi-page document."""
        p1 = "PAGE ONE HEADER\nParties are Company A and Company B.\n"
        p2 = "PAGE TWO HEADER\nGOVERNING LAW: The laws of India shall apply.\n"
        full_text = f"{p1}\n{p2}"
        pages = [
            {"page_number": 1, "text": p1},
            {"page_number": 2, "text": p2},
        ]
        res = self.engine.extract_value_for_prompt("Governing Law", "doc-2", "Deed.pdf", full_text, pages)
        assert res.evidence is not None
        assert res.evidence.page_num == 2


class TestReviewTableExporter:
    """Test CSV and Open XML (.xlsx) exporters."""

    def test_export_csv_structure(self):
        """Export review table to structured CSV string."""
        columns = [
            {"id": "col-1", "name": "Governing Law"},
            {"id": "col-2", "name": "Stamp Duty"},
        ]
        rows = [
            {
                "document_name": "Deed_A.pdf",
                "cells": {
                    "col-1": {"value": "Laws of India", "confidence_score": 0.95, "evidence": {"page_num": 1, "text_snippet": "Laws of India"}},
                    "col-2": {"value": "Rs. 50,000", "confidence_score": 0.88, "evidence": {"page_num": 2, "text_snippet": "Rs. 50,000 paid"}},
                },
            }
        ]
        csv_out = ReviewTableExporter.export_csv("Sample Table", columns, rows)
        assert "Document Name" in csv_out
        assert "Governing Law" in csv_out
        assert "Governing Law (Confidence)" in csv_out
        assert "Deed_A.pdf" in csv_out
        assert "95%" in csv_out
        assert "Rs. 50,000" in csv_out

    def test_export_xlsx_binary_validity(self):
        """Export review table to valid XLSX zip archive with multiple worksheets."""
        columns = [
            {"id": "col-1", "name": "Governing Law"},
            {"id": "col-2", "name": "Indemnity Cap"},
        ]
        rows = [
            {
                "document_name": "Commercial_Contract.pdf",
                "cells": {
                    "col-1": {"value": "Laws of Karnataka, India", "confidence_score": 0.92, "evidence": {"page_num": 1, "text_snippet": "Karnataka"}},
                    "col-2": {"value": "INR 25,00,000", "confidence_score": 0.85, "evidence": {"page_num": 3, "text_snippet": "INR 25,00,000"}},
                },
            }
        ]
        xlsx_bytes = ReviewTableExporter.export_xlsx("Commercial Review", columns, rows)
        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 200

        # Validate genuine zip structure
        with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as z:
            names = z.namelist()
            assert "[Content_Types].xml" in names
            assert "xl/workbook.xml" in names
            assert "xl/worksheets/sheet1.xml" in names
            assert "xl/worksheets/sheet2.xml" in names
            assert "xl/sharedStrings.xml" in names

            # Parse and verify sheet1 XML
            s1_data = z.read("xl/worksheets/sheet1.xml")
            root = ET.fromstring(s1_data)
            assert root is not None


class TestReviewTableApiEndpoints:
    """Test Review Tables REST API endpoints with authenticated test client."""

    @pytest.mark.asyncio
    async def test_create_and_list_review_tables(self, client, auth_headers, seed_case):
        """Create a review table and list it."""
        case_id = seed_case["id"]
        create_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables",
            json={
                "name": "M&A Due Diligence Table",
                "description": "Cross-document lease review",
                "columns": [
                    {"name": "Governing Law", "column_type": "prompt", "prompt": "Governing law"},
                    {"name": "Notice Period", "column_type": "prompt", "prompt": "Notice period"},
                ],
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["name"] == "M&A Due Diligence Table"
        assert len(data["columns"]) == 2
        table_id = data["id"]

        # List tables
        list_resp = await client.get(f"/api/v1/cases/{case_id}/review-tables", headers=auth_headers)
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert any(t["id"] == table_id for t in list_data["items"])

    @pytest.mark.asyncio
    async def test_column_crud(self, client, auth_headers, seed_case):
        """Add, update, and delete columns in review table."""
        case_id = seed_case["id"]
        create_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables",
            json={"name": "Column Test Table"},
            headers=auth_headers,
        )
        table_id = create_resp.json()["id"]

        # Add Column
        col_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/columns",
            json={"name": "Stamp Duty", "prompt": "What is the stamp duty?", "position": 5},
            headers=auth_headers,
        )
        assert col_resp.status_code == 200
        col_id = col_resp.json()["id"]

        # Update Column
        up_resp = await client.put(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/columns/{col_id}",
            json={"name": "Stamp Duty Paid (INR)"},
            headers=auth_headers,
        )
        assert up_resp.status_code == 200
        assert up_resp.json()["name"] == "Stamp Duty Paid (INR)"

        # Delete Column
        del_resp = await client.delete(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/columns/{col_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_table_extraction_and_cell_override(self, client, auth_headers, seed_case, seed_document):
        """Run extraction across matter documents and manually override cell."""
        case_id = seed_case["id"]
        create_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables",
            json={
                "name": "Extraction Test Table",
                "columns": [
                    {"name": "Governing Law", "column_type": "prompt", "prompt": "Governing law"},
                ],
            },
            headers=auth_headers,
        )
        table_id = create_resp.json()["id"]

        # Run extraction
        ext_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/extract",
            json={},
            headers=auth_headers,
        )
        assert ext_resp.status_code == 200
        assert ext_resp.json()["status"] == "completed"

        # Get table data grid
        grid_resp = await client.get(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}",
            headers=auth_headers,
        )
        assert grid_resp.status_code == 200
        grid_data = grid_resp.json()
        assert len(grid_data["rows"]) >= 1

    @pytest.mark.asyncio
    async def test_table_export_csv_and_xlsx(self, client, auth_headers, seed_case):
        """Test exporting table to CSV and XLSX."""
        case_id = seed_case["id"]
        create_resp = await client.post(
            f"/api/v1/cases/{case_id}/review-tables",
            json={"name": "Export Test Table"},
            headers=auth_headers,
        )
        table_id = create_resp.json()["id"]

        # CSV Export
        csv_resp = await client.get(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/export?format=csv",
            headers=auth_headers,
        )
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]

        # XLSX Export
        xlsx_resp = await client.get(
            f"/api/v1/cases/{case_id}/review-tables/{table_id}/export?format=xlsx",
            headers=auth_headers,
        )
        assert xlsx_resp.status_code == 200
        assert "spreadsheetml" in xlsx_resp.headers["content-type"]
        assert len(xlsx_resp.content) > 100
