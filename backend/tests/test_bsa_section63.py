"""Tests for Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 API & Engine (Milestone 7)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security.auth import AuthContext, get_auth_context, get_case_access


@pytest.fixture
def auth_override():
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id="test-lawyer-1",
        organization_id="test-org-1",
        role="LAWYER",
    )
    app.dependency_overrides[get_case_access] = lambda: (
        AuthContext(user_id="test-lawyer-1", organization_id="test-org-1", role="LAWYER"),
        {"id": "case-test-101", "name": "Brigade Meadows Sy 124 Title Search"},
    )
    yield
    app.dependency_overrides.pop(get_auth_context, None)
    app.dependency_overrides.pop(get_case_access, None)


@pytest.mark.asyncio
async def test_generate_and_download_bsa_certificate(auth_override):
    """Test generating Section 63 certificate and downloading printable HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Generate Section 63 Certificate
        payload = {
            "case_id": "case-test-101",
            "custodian_name": "Advocate S. R. Rao",
            "custodian_designation": "Lead Title Counsel",
            "organization_name": "Jurisiva & Partners",
            "include_legacy_65b": True,
        }
        res_cert = await ac.post("/api/v1/bsa/cases/case-test-101/certificate", json=payload)
        assert res_cert.status_code == 200
        cert = res_cert.json()
        assert cert["certificate_id"].startswith("BSA-SEC63-")
        assert cert["statutory_framework"]["primary_act"] == "Bharatiya Sakshya Adhiniyam, 2023 (Act No. 47 of 2023)"
        assert cert["statutory_framework"]["primary_section"] == "Section 63 (Admissibility of electronic records)"
        assert len(cert["master_audit_hash"]) == 64  # SHA-256 length
        assert len(cert["certified_documents"]) >= 1

        cert_id = cert["certificate_id"]

        # 2. Download Printable HTML Certificate
        res_html = await ac.get(f"/api/v1/bsa/certificate/{cert_id}/download")
        assert res_html.status_code == 200
        assert "text/html" in res_html.headers["content-type"]
        assert "Bharatiya Sakshya Adhiniyam, 2023" in res_html.text
        assert cert_id in res_html.text
        assert "Advocate S. R. Rao" in res_html.text
