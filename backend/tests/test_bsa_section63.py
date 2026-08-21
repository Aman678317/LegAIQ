"""Tests for Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 API & Engine (Milestone 7 & 10 Hardening)."""
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException

from app.main import app
from app.security.auth import AuthContext, get_auth_context, get_case_access
from tests.conftest import USER_ID, ORG_ID


@pytest.fixture
def auth_override(fake, seed_case):
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="LAWYER",
    )
    app.dependency_overrides[get_case_access] = lambda: (
        AuthContext(user_id=USER_ID, organization_id=ORG_ID, role="LAWYER"),
        {"id": "case-test-101", "name": "Brigade Meadows Sy 124 Title Search", "organization_id": ORG_ID},
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
        hex_part = cert["certificate_id"].removeprefix("BSA-SEC63-")
        assert len(hex_part) == 16  # 16-hex character entropy
        assert cert["statutory_framework"]["primary_act"] == "Bharatiya Sakshya Adhiniyam, 2023 (Act No. 47 of 2023)"
        assert cert["statutory_framework"]["primary_section"] == "Section 63 (Admissibility of electronic records)"
        assert len(cert["master_audit_hash"]) == 64  # SHA-256 length
        assert len(cert["certified_documents"]) >= 1

        cert_id = cert["certificate_id"]

        # 2. Get Certificate by ID (Authorized)
        res_get = await ac.get(f"/api/v1/bsa/certificate/{cert_id}")
        assert res_get.status_code == 200
        assert res_get.json()["certificate_id"] == cert_id

        # 3. Download Printable HTML Certificate (Authorized)
        res_html = await ac.get(f"/api/v1/bsa/certificate/{cert_id}/download")
        assert res_html.status_code == 200
        assert "text/html" in res_html.headers["content-type"]
        assert "Bharatiya Sakshya Adhiniyam, 2023" in res_html.text
        assert cert_id in res_html.text
        assert "Advocate S. R. Rao" in res_html.text

        # 4. List Case Certificates (verifies get_case_access dependency)
        res_list = await ac.get("/api/v1/bsa/cases/case-test-101/certificates")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["case_id"] == "case-test-101"
        assert len(list_data["certificates"]) >= 1


@pytest.mark.asyncio
async def test_cross_tenant_bsa_certificate_access_rejected(fake, seed_case):
    """Ensure users from foreign tenant organizations cannot read or download BSA certificates."""
    cert_id = "BSA-SEC63-A1B2C3D4E5F67890"
    from app.api.bsa import _BSA_CERTIFICATES
    _BSA_CERTIFICATES[cert_id] = {
        "certificate_id": cert_id,
        "case_id": "case-test-101",
        "case_name": "Brigade Meadows Sy 124 Title Search",
        "issued_at": "2026-08-20T00:00:00Z",
        "custodian": {"name": "Advocate Rao", "designation": "Counsel", "organization": "Firm A"},
        "master_audit_hash": "a" * 64,
        "certified_documents": [],
        "statutory_declaration": "I declare...",
    }

    # Foreign user identity not associated with ORG_ID owning case-test-101
    foreign_user_id = "00000000-0000-4000-8000-0000000000bb"
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id=foreign_user_id,
        organization_id="foreign-org-id",
        role="LAWYER",
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Foreign user attempts to read certificate metadata
            res_get = await ac.get(f"/api/v1/bsa/certificate/{cert_id}")
            assert res_get.status_code == 403

            # Foreign user attempts to download HTML certificate
            res_download = await ac.get(f"/api/v1/bsa/certificate/{cert_id}/download")
            assert res_download.status_code == 403
    finally:
        app.dependency_overrides.pop(get_auth_context, None)


@pytest.mark.asyncio
async def test_unauthenticated_bsa_download_rejected():
    """Ensure unauthenticated requests to download or get BSA certificates are rejected with 401."""
    app.dependency_overrides.pop(get_auth_context, None)
    app.dependency_overrides.pop(get_case_access, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_get = await ac.get("/api/v1/bsa/certificate/BSA-SEC63-UNKNOWN123456")
        assert res_get.status_code == 401

        res_download = await ac.get("/api/v1/bsa/certificate/BSA-SEC63-UNKNOWN123456/download")
        assert res_download.status_code == 401
