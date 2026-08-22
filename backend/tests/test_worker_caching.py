"""Tests for Celery Worker Redis and in-memory caching layer."""

import pytest
from app.workers.caching import WorkerCache, cache


def test_ocr_caching_and_retrieval():
    """Test caching and retrieving OCR results."""
    case_id = "test-case-123"
    doc_id = "test-doc-456"
    sample_ocr = {
        "document_id": doc_id,
        "provider": "tesseract",
        "document_type": "7_12_extract",
        "full_text": "Sample Maharashtra 7/12 Extract Text",
        "mean_confidence": 0.94,
    }

    key = cache.cache_ocr_result(case_id, doc_id, sample_ocr)
    assert key.startswith("legaiq:worker:test-case-123:test-doc-456:ocr:")

    retrieved = cache.get_ocr_result(case_id, doc_id, provider="tesseract", document_type="7_12_extract")
    assert retrieved is not None
    assert retrieved["full_text"] == "Sample Maharashtra 7/12 Extract Text"
    assert retrieved["mean_confidence"] == 0.94


def test_extraction_caching_and_invalidation():
    """Test caching extraction results and invalidation."""
    case_id = "test-case-789"
    doc_id = "test-doc-999"
    extraction_data = {
        "document_id": doc_id,
        "parties": ["Ramesh Kumar", "Suresh Sharma"],
        "consideration": 5000000,
    }

    cache.cache_extraction_result(case_id, doc_id, extraction_data)
    cached = cache.get_extraction_result(case_id, doc_id)
    assert cached is not None
    assert cached["parties"] == ["Ramesh Kumar", "Suresh Sharma"]

    # Invalidate cache
    deleted = cache.invalidate_cache(case_id, doc_id)
    assert deleted >= 1
    assert cache.get_extraction_result(case_id, doc_id) is None
