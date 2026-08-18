"""API-layer tests: health, auth enforcement, case lifecycle, admin guard."""
from tests.conftest import ADMIN_USER_ID, ORG_ID, USER_ID

API = "/api/v1"


class TestHealth:
    def test_health_endpoint(self, api_client):
        res = api_client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


class TestAuthEnforcement:
    def test_missing_token_rejected(self, fake, fake_ocr):
        """No dependency override -> real auth path -> 401 without a token."""
        import asyncio

        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async def call():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(f"{API}/cases?organization_id={ORG_ID}")

        res = asyncio.run(call())
        assert res.status_code == 401


class TestCaseLifecycle:
    def test_create_case(self, api_client, fake):
        res = api_client.post(f"{API}/cases", json={
            "name": "Whitefield Sy 124/3", "case_type": "PROPERTY",
            "organization_id": ORG_ID, "jurisdiction_state": "Karnataka",
        })
        assert res.status_code == 200, res.text
        case = res.json()
        assert case["id"]
        assert case["case_type"] == "PROPERTY"
        assert case["status"] == "ACTIVE"

        # Property row auto-created for PROPERTY cases
        props = [p for p in fake.tables.rows("properties") if p["case_id"] == case["id"]]
        assert len(props) == 1

        # Creation audited
        audits = [a for a in fake.tables.rows("audit_events") if a["action"] == "case.created"]
        assert len(audits) == 1

    def test_membership_required_to_create(self, api_client, fake):
        res = api_client.post(f"{API}/cases", json={
            "name": "X", "organization_id": "11111111-1111-4111-8111-111111111111",
        })
        assert res.status_code == 403

    def test_list_and_get_case(self, api_client, fake):
        api_client.post(f"{API}/cases", json={
            "name": "Civil Matter", "case_type": "CIVIL", "organization_id": ORG_ID,
        })
        res = api_client.get(f"{API}/cases?organization_id={ORG_ID}")
        assert res.status_code == 200
        assert res.json()["total"] == 1

        case_id = res.json()["items"][0]["id"]
        res = api_client.get(f"{API}/cases/{case_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Civil Matter"

        # Unknown case -> 404 (single() on missing)
        res = api_client.get(f"{API}/cases/22222222-2222-4222-8222-222222222222")
        assert res.status_code == 404

    def test_update_and_activity(self, api_client, fake):
        case = api_client.post(f"{API}/cases", json={
            "name": "Old Name", "organization_id": ORG_ID,
        }).json()
        res = api_client.patch(f"{API}/cases/{case['id']}", json={"name": "New Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

        activity = api_client.get(f"{API}/cases/{case['id']}/activity")
        assert activity.status_code == 200
        assert any(e["event_type"] == "case.created" for e in activity.json())


class TestAdminGuard:
    def test_non_admin_gets_403(self, api_client):
        res = api_client.get(f"{API}/admin/overview")
        assert res.status_code == 403
        assert "administrator" in res.json()["detail"].lower()

    def test_admin_overview(self, admin_api_client, fake):
        api_client_like = admin_api_client
        res = api_client_like.get(f"{API}/admin/overview")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["counts"]["organizations"] == 1
        assert data["counts"]["users"] == 2
        assert "providers" in data and "openai" in data["providers"]

    def test_admin_cannot_revoke_own_flag(self, admin_api_client):
        res = admin_api_client.patch(
            f"{API}/admin/users/{ADMIN_USER_ID}/platform-admin",
            json={"is_platform_admin": False},
        )
        assert res.status_code == 400


class TestOrgMembers:
    def test_add_update_remove_member(self, api_client, fake):
        # Create a second user to add
        new_user_id = "00000000-0000-4000-8000-0000000000bb"
        fake.tables.rows("profiles").append({
            "id": new_user_id, "email": "associate@testfirm.com",
            "full_name": "Associate", "created_at": "2026-01-02T00:00:00+00:00",
            "updated_at": "2026-01-02T00:00:00+00:00", "is_platform_admin": False,
        })

        res = api_client.post(f"{API}/orgs/{ORG_ID}/members", json={
            "email": "associate@testfirm.com", "role": "LAWYER",
        })
        assert res.status_code == 200, res.text

        # Duplicate add -> 409
        res = api_client.post(f"{API}/orgs/{ORG_ID}/members", json={
            "email": "associate@testfirm.com", "role": "LAWYER",
        })
        assert res.status_code == 409

        # Unknown email -> 404
        res = api_client.post(f"{API}/orgs/{ORG_ID}/members", json={
            "email": "ghost@nowhere.com", "role": "LAWYER",
        })
        assert res.status_code == 404

        # Change role
        res = api_client.patch(f"{API}/orgs/{ORG_ID}/members/{new_user_id}", json={"role": "REVIEWER"})
        assert res.status_code == 200
        assert res.json()["role"] == "REVIEWER"

        # Remove
        res = api_client.delete(f"{API}/orgs/{ORG_ID}/members/{new_user_id}")
        assert res.status_code == 200

        # Permission changes audited: added + role_changed + removed
        actions = [a["action"] for a in fake.tables.rows("audit_events")]
        assert "member.added" in actions
        assert "member.role_changed" in actions
        assert "member.removed" in actions

    def test_last_owner_protection(self, api_client, fake):
        """Acting as the org ADMIN: the sole OWNER cannot be demoted or removed."""
        from app.main import app
        from app.security.auth import AuthContext, get_auth_context

        original = app.dependency_overrides[get_auth_context]
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            user_id=ADMIN_USER_ID, email="admin@jurisiva.ai"
        )
        try:
            res = api_client.patch(f"{API}/orgs/{ORG_ID}/members/{USER_ID}", json={"role": "ADMIN"})
            assert res.status_code == 400
            assert "last OWNER" in res.json()["detail"]

            res = api_client.delete(f"{API}/orgs/{ORG_ID}/members/{USER_ID}")
            assert res.status_code == 400
            assert "last OWNER" in res.json()["detail"]
        finally:
            app.dependency_overrides[get_auth_context] = original


class TestDocumentAndResearchEndpoints:
    def test_document_translation_post(self, api_client, fake):
        # Create case
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Deed Translation Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        # Insert doc and page in fake db
        doc_id = "doc-trans-1"
        fake.tables.rows("documents").append({
            "id": doc_id, "case_id": case_id, "file_name": "kannada_deed.pdf",
            "file_type": "application/pdf", "status": "COMPLETED", "uploaded_by": USER_ID,
        })
        fake.tables.rows("document_pages").append({
            "id": "page-trans-1", "document_id": doc_id, "page_number": 1,
            "text": "ಸರ್ವೆ ನಂ. 124/2 ರ ಪೈಕಿ ಪೂರ್ವ ಭಾಗದ 1 ಎಕರೆ 7 ಗುಂಟೆ ಜಮೀನು",
            "language": "kn", "confidence": 0.95,
        })

        # Test POST /cases/{case_id}/documents/{document_id}/translate
        res = api_client.post(f"{API}/cases/{case_id}/documents/{doc_id}/translate", json={
            "page": 1, "language": "hi",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "hi"
        assert data["page_number"] == 1
        assert data["status"] in ("COMPLETED", "QUEUED")

    def test_research_endpoint(self, api_client, fake):
        case_res = api_client.post(f"{API}/cases", json={
            "name": "Research Case", "case_type": "PROPERTY", "organization_id": ORG_ID,
        })
        case_id = case_res.json()["id"]

        res = api_client.post(f"{API}/cases/{case_id}/research", json={
            "question": "What is the limitation period for challenging a fraudulent sale deed?",
            "jurisdiction": "Karnataka",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["answer"]
        assert data["status"] == "COMPLETED"
