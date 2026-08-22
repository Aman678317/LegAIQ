"""Tests for JSON Schema Validation Middleware and Repository."""

import pytest
from app.middleware.schema_validation import SchemaValidator, validator


def test_document_schema_validation():
    """Test validating valid document against document.json schema."""
    valid_doc = {
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "case_id": "550e8400-e29b-41d4-a716-446655440001",
        "filename": "SaleDeed_2023.pdf",
        "file_type": "application/pdf",
        "status": "UPLOADED",
    }
    assert validator.validate_request(valid_doc, "document", "v1") is True


def test_ocr_result_schema_validation():
    """Test validating OCR results against ocr_result.json schema."""
    valid_ocr = {
        "document_id": "550e8400-e29b-41d4-a716-446655440000",
        "pages": [
            {
                "page_number": 1,
                "text": "Registration Deed content",
                "language": "en",
                "confidence": 0.95,
            }
        ],
        "provider": "tesseract",
        "document_type": "sale_deed",
        "detected_languages": ["en"],
    }
    assert validator.validate_request(valid_ocr, "ocr_result", "v1") is True
