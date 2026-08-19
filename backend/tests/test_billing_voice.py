"""Billing service tests: metering, limits, honest 501s."""
import pytest
from fastapi import HTTPException

from tests.conftest import ORG_ID, USER_ID

API = "/api/v1"


def _seed_plans(fake):
    t = fake.tables
    t.rows("plans").append({
        "code": "FREE", "name": "Free", "price_inr": 0,
        "limits": {"pages_per_month": 25, "ai_runs_per_month": 50, "cases": 1},
        "sort_order": 1,
    })
    t.rows("plans").append({
        "code": "PROFESSIONAL", "name": "Professional", "price_inr": 4999,
        "limits": {"pages_per_month": 500, "ai_runs_per_month": 2000},
        "sort_order": 2,
    })
    t.rows("plans").append({
        "code": "ENTERPRISE", "name": "Enterprise", "price_inr": 0,
        "limits": {"pages_per_month": None, "ai_runs_per_month": None},
        "sort_order": 4,
    })


def _subscribe(fake, org_id=ORG_ID, plan="FREE", status="ACTIVE"):
    fake.tables.rows("subscriptions").append({
        "id": f"sub-{plan}", "organization_id": org_id,
        "plan_code": plan, "status": status,
        "current_period_start": "2026-08-01T00:00:00+00:00",
        "current_period_end": "2026-09-01T00:00:00+00:00",
    })
    # attach plan details the way the join returns them
    plan_row = next(p for p in fake.tables.rows("plans") if p["code"] == plan)
    for s in fake.tables.rows("subscriptions"):
        if s["id"] == f"sub-{plan}":
            s["plans"] = plan_row


class TestBillingService:
    def test_fail_open_without_subscription(self, fake):
        from app.services.billing import within_limit
        allowed, info = within_limit(fake, ORG_ID, "pages", 5)
        assert allowed is True
        assert info["reason"] == "no_subscription_record"

    def test_limit_enforced_with_subscription(self, fake):
        _seed_plans(fake)
        _subscribe(fake)
        from app.services.billing import record_usage, within_limit

        allowed, _ = within_limit(fake, ORG_ID, "pages", 25)
        assert allowed is True
        record_usage(ORG_ID, "pages", 25)
        allowed, info = within_limit(fake, ORG_ID, "pages", 1)
        assert allowed is False
        assert info["reason"] == "limit_exceeded"

    def test_unlimited_when_limit_null(self, fake):
        _seed_plans(fake)
        _subscribe(fake, plan="ENTERPRISE")
        from app.services.billing import record_usage, within_limit

        record_usage(ORG_ID, "pages", 100000)
        allowed, info = within_limit(fake, ORG_ID, "pages", 1)
        assert allowed is True
        assert info["reason"] == "unlimited"

    def test_canceled_subscription_blocks(self, fake):
        _seed_plans(fake)
        _subscribe(fake, status="CANCELED")
        from app.services.billing import within_limit
        allowed, info = within_limit(fake, ORG_ID, "pages", 1)
        assert allowed is False
        assert info["reason"] == "subscription_canceled"

    def test_record_usage_ignores_bad_input(self, fake):
        from app.services.billing import record_usage
        record_usage(None, "pages", 5)          # no org
        record_usage(ORG_ID, "bogus", 5)        # bad metric
        record_usage(ORG_ID, "pages", -1)       # negative
        assert fake.tables.rows("usage_events") == []


class TestBillingAPI:
    def test_get_billing(self, api_client, fake):
        _seed_plans(fake)
        _subscribe(fake)
        from app.services.billing import record_usage
        record_usage(ORG_ID, "pages", 12, case_id=None)
        record_usage(ORG_ID, "ai_runs", 3, case_id=None)

        res = api_client.get(f"{API}/orgs/{ORG_ID}/billing")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["plan"]["code"] == "FREE"
        assert body["usage"]["pages"] == 12
        assert body["usage"]["ai_runs"] == 3
        assert body["limits"]["pages_per_month"] == 25
        assert len(body["available_plans"]) == 3

    def test_non_member_blocked(self, api_client, fake):
        res = api_client.get(f"{API}/orgs/33333333-3333-4333-8333-333333333333/billing")
        assert res.status_code == 403

    def test_checkout_is_honest_501(self, api_client, fake):
        """No payment provider configured -> explicit 501, never a fake charge."""
        res = api_client.post(f"{API}/orgs/{ORG_ID}/billing/checkout")
        assert res.status_code == 501
        assert "not configured" in res.json()["detail"].lower()

    def test_paid_plan_change_501(self, api_client, fake):
        _seed_plans(fake)
        _subscribe(fake)
        res = api_client.post(f"{API}/orgs/{ORG_ID}/billing/plan", json={"plan_code": "PROFESSIONAL"})
        assert res.status_code == 501

    def test_unknown_plan_404(self, api_client, fake):
        _seed_plans(fake)
        res = api_client.post(f"{API}/orgs/{ORG_ID}/billing/plan", json={"plan_code": "DIAMOND"})
        assert res.status_code == 404


class TestVoiceProviderEndpoints:
    def _make_case(self, api_client) -> str:
        res = api_client.post(f"{API}/cases", json={"name": "Voice Case", "organization_id": ORG_ID})
        return res.json()["id"]

    def test_transcribe_unconfigured_is_503(self, api_client, fake, monkeypatch):
        """No STT key -> honest 503, never a fabricated transcript."""
        from app.ai import voice_providers
        monkeypatch.setattr(voice_providers, "stt_configured", lambda: False)
        case_id = self._make_case(api_client)
        res = api_client.post(
            f"{API}/cases/{case_id}/voice/transcribe",
            files={"audio": ("s.webm", b"fakeaudio", "audio/webm")},
        )
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()

    def test_speak_unconfigured_is_503(self, api_client, fake, monkeypatch):
        from app.ai import voice_providers
        monkeypatch.setattr(voice_providers, "tts_configured", lambda: False)
        case_id = self._make_case(api_client)
        res = api_client.post(
            f"{API}/cases/{case_id}/voice/speak",
            json={"text": "hello", "language": "en"},
        )
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()

    def test_transcribe_empty_audio_400(self, api_client, fake, monkeypatch):
        from app.ai import voice_providers
        monkeypatch.setattr(voice_providers, "stt_configured", lambda: True)
        case_id = self._make_case(api_client)
        res = api_client.post(
            f"{API}/cases/{case_id}/voice/transcribe",
            files={"audio": ("s.webm", b"", "audio/webm")},
        )
        assert res.status_code == 400
