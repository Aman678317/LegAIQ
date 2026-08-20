"""Tests for Dynamic Document Watermarking Engine (Milestone 6)."""
import pytest
from app.security.watermark import DocumentWatermarker, watermark_document_text


def test_generate_watermark_metadata():
    """Verify watermark metadata generation with audit hash."""
    meta = DocumentWatermarker.generate_watermark_metadata(
        viewer_email="partner@lawfirm.in",
        viewer_ip="192.168.1.50",
        organization_name="Jurisiva Legal",
    )
    assert meta["viewer_email"] == "partner@lawfirm.in"
    assert meta["viewer_ip"] == "192.168.1.50"
    assert "UTC" in meta["timestamp"]
    assert meta["watermark_code"].startswith("LEGAIQ-SEC-")
    assert len(meta["audit_hash"]) == 12


def test_apply_text_watermark():
    """Verify headers and footers stamped on text content."""
    original_text = "Clause 1: All conveyances must be registered with the SRO."
    watermarked = DocumentWatermarker.apply_text_watermark(
        content=original_text,
        viewer_email="associate@lawfirm.in",
        viewer_ip="10.0.0.1",
    )
    assert "CONFIDENTIAL & PROPRIETARY" in watermarked
    assert "associate@lawfirm.in" in watermarked
    assert "10.0.0.1" in watermarked
    assert "DPDP ACT 2023" in watermarked
    assert original_text in watermarked


def test_generate_svg_watermark():
    """Verify SVG watermark overlay output."""
    svg = DocumentWatermarker.generate_svg_watermark(
        viewer_email="client@corp.in",
        viewer_ip="172.16.0.4",
    )
    assert "<svg" in svg
    assert "client@corp.in" in svg
    assert "CONFIDENTIAL &amp; PRIVILEGED" in svg
