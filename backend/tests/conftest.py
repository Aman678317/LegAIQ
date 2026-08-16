"""Shared fixtures: fake Supabase, fake OCR, auth overrides, ASGI client."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on sys.path

from tests.fakes.fake_supabase import FakeSupabase  # noqa: E402

# Modules that import `create_client` at module level and call it via svc()/db()/_db()
PATCH_TARGETS = [
    "app.api.cases",
    "app.api.documents",
    "app.api.analysis",
    "app.api.ownership",
    "app.api.comparison",
    "app.api.risks",
    "app.api.drafts",
    "app.api.reports",
    "app.api.properties",
    "app.api.jobs",
    "app.api.admin",
    "app.api.org",
    "app.api.billing",
    "app.api.voice",
    "app.workers.tasks",
    "app.workers.dispatcher",
    "app.ai.agents.base",
    "app.ai.agents.tools",
    "app.ai.agents.registry",
    "app.security.audit",
    "app.security.auth",
    "app.services.billing",
]

# Fixed identities used across tests
ORG_ID = "00000000-0000-4000-8000-000000000001"
USER_ID = "00000000-0000-4000-8000-0000000000aa"
ADMIN_USER_ID = "00000000-0000-4000-8000-0000000000ff"


class FakeOCRProvider:
    """Deterministic OCR provider with realistic Indian deed text.

    Supports a queue of page-sets: enqueue_pages() before each upload to
    control what the worker OCRs for that specific document.
    """

    name = "fake_tesseract"

    DEFAULT_PAGES = [
        (
            "THIS SALE DEED is executed on this 12th day of March 1987 at Bengaluru. "
            "WHEREAS Venkatarama Reddy S/o Late Krishnappa is the absolute owner of "
            "the schedule property bearing Sy. No. 124/3 of Whitefield Hobli, "
            "Bangalore South Taluk, Bengaluru District, Khata No. 456, measuring "
            "2 Acres 14 Guntas, NOW the vendor sells the property to Lakshmamma "
            "W/o Late Narayana Rao for a consideration of Rs. 45,000 (Rupees Forty "
            "Five Thousand only). Registered as Doc No. 789/1987-88 before the "
            "Sub-Registrar Whitefield on 15/03/1987. Witnesses: 1) Rama Rao 2) Gopal."
        ),
        (
            "SCHEDULE: All that piece and parcel of land bearing Survey Number 124/3 "
            "Hissa 2, situated at Varthur Village, Whitefield Hobli, Bangalore South "
            "Taluk, Bengaluru District, bounded on the North by Sy. No. 124/2, on the "
            "South by village road, East by Sy. No. 125/1, West by Sy. No. 123/4."
        ),
    ]

    def __init__(self, pages: list[str] | None = None):
        self.pages = pages or list(self.DEFAULT_PAGES)
        self._by_marker: dict[bytes, list[str]] = {}

    def enqueue_for(self, marker: bytes, pages: list[str]):
        """Serve `pages` when OCR processes a file whose bytes equal `marker`."""
        self._by_marker[marker] = pages

    def is_configured(self):
        return True

    async def process(self, file_bytes: bytes, file_type: str):
        from app.ai.ocr import OCRDocumentResult, OCRPageResult

        pages = self._by_marker.get(file_bytes, self.pages)
        return OCRDocumentResult(
            pages=[
                OCRPageResult(page_number=i + 1, text=text, language="en", confidence=0.93)
                for i, text in enumerate(pages)
            ],
            provider=self.name,
        )


def seed(fake: FakeSupabase):
    """Seed organizations, profiles, memberships, and the platform admin."""
    t = fake.tables
    t.rows("organizations").append({
        "id": ORG_ID, "name": "Test Law Firm", "slug": "test-law-firm",
        "plan": "FREE", "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    t.rows("profiles").append({
        "id": USER_ID, "email": "lawyer@testfirm.com", "full_name": "Test Lawyer",
        "avatar_url": None, "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00", "is_platform_admin": False,
    })
    t.rows("profiles").append({
        "id": ADMIN_USER_ID, "email": "admin@jurisiva.ai", "full_name": "Platform Admin",
        "avatar_url": None, "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00", "is_platform_admin": True,
    })
    t.rows("memberships").append({
        "id": "00000000-0000-4000-8000-0000000000m1",
        "organization_id": ORG_ID, "user_id": USER_ID, "role": "OWNER",
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    t.rows("memberships").append({
        "id": "00000000-0000-4000-8000-0000000000m2",
        "organization_id": ORG_ID, "user_id": ADMIN_USER_ID, "role": "ADMIN",
        "created_at": "2026-01-01T00:00:00+00:00",
    })


@pytest.fixture
def fake(monkeypatch):
    """Fake Supabase wired into every backend module + seeded base data."""
    fake = FakeSupabase()
    seed(fake)
    import importlib

    for target in PATCH_TARGETS:
        try:
            module = importlib.import_module(target)
            monkeypatch.setattr(module, "create_client", lambda *a, **k: fake, raising=False)
        except ModuleNotFoundError:
            pass
    return fake


@pytest.fixture
def fake_ocr(monkeypatch):
    provider = FakeOCRProvider()
    import app.ai.ocr as ocr_module
    monkeypatch.setattr(ocr_module, "get_ocr_provider", lambda: provider)
    return provider


def drain_jobs(fake: FakeSupabase, max_rounds: int = 30):
    """Run the worker pipeline synchronously until no QUEUED jobs remain.

    Replaces Celery's .delay with a direct call, then uses the real
    dispatcher to claim and route jobs — the same path production uses.
    """
    from app.workers import tasks as tasks_module
    from app.workers.dispatcher import dispatch_pending_jobs

    # Make task.delay run inline
    task_funcs = {
        "run_ocr": tasks_module.run_ocr,
        "run_extraction": tasks_module.run_extraction,
        "run_embeddings": tasks_module.run_embeddings,
        "run_translation": tasks_module.run_translation,
        "run_ownership": tasks_module.run_ownership,
        "run_comparison": tasks_module.run_comparison,
        "run_risk_analysis": tasks_module.run_risk_analysis,
        "run_report": tasks_module.run_report,
        "run_report_export": tasks_module.run_report_export,
    }
    originals = {}
    for name, task in task_funcs.items():
        originals[name] = task.delay
        task.delay = lambda job_id, _t=task: _t.run(job_id)
    try:
        for _ in range(max_rounds):
            dispatched = dispatch_pending_jobs()
            if dispatched == 0:
                queued = [
                    j for j in fake.tables.rows("jobs")
                    if j.get("state") in ("QUEUED", "RUNNING")
                ]
                if not queued:
                    return
        raise AssertionError("Pipeline did not drain — possible loop or stuck job")
    finally:
        for name, task in task_funcs.items():
            task.delay = originals[name]


@pytest.fixture
def drain(fake):
    return lambda: drain_jobs(fake)


@pytest.fixture
def api_client(fake, fake_ocr, monkeypatch):
    """Authenticated AsyncClient against the FastAPI app (service-role faked)."""
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.security.auth import AuthContext, get_auth_context

    def override():
        return AuthContext(user_id=USER_ID, email="lawyer@testfirm.com")

    app.dependency_overrides[get_auth_context] = override
    transport = ASGITransport(app=app)

    class SyncWrapper:
        def __init__(self):
            self._client = AsyncClient(transport=transport, base_url="http://test")

        def _run(self, coro):
            return asyncio.run(coro)

        def get(self, *a, **k):
            return self._run(self._client.get(*a, **k))

        def post(self, *a, **k):
            return self._run(self._client.post(*a, **k))

        def patch(self, *a, **k):
            return self._run(self._client.patch(*a, **k))

        def delete(self, *a, **k):
            return self._run(self._client.delete(*a, **k))

    yield SyncWrapper()
    app.dependency_overrides.pop(get_auth_context, None)


@pytest.fixture
def admin_api_client(fake, fake_ocr, monkeypatch):
    """AsyncClient authenticated as the platform admin."""
    import asyncio

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.security.auth import AuthContext, get_auth_context

    def override():
        return AuthContext(user_id=ADMIN_USER_ID, email="admin@jurisiva.ai")

    app.dependency_overrides[get_auth_context] = override
    transport = ASGITransport(app=app)

    class SyncWrapper:
        def __init__(self):
            self._client = AsyncClient(transport=transport, base_url="http://test")

        def _run(self, coro):
            return asyncio.run(coro)

        def get(self, *a, **k):
            return self._run(self._client.get(*a, **k))

        def post(self, *a, **k):
            return self._run(self._client.post(*a, **k))

        def patch(self, *a, **k):
            return self._run(self._client.patch(*a, **k))

    yield SyncWrapper()
    app.dependency_overrides.pop(get_auth_context, None)
