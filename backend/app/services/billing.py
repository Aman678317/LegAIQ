"""Billing service: metering and plan limits.

No payment processing happens here — usage is metered honestly and limits
are enforced fail-open when plan data is unavailable (so a missing billing
setup never blocks legitimate work). Checkout remains a 501 until a payment
provider is chosen, per the no-fake-transactions rule.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import create_client

from app.config import get_settings

settings = get_settings()

METRICS = ("pages", "ai_runs", "voice_minutes", "storage_bytes")


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _period_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Calendar-month billing window."""
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def record_usage(
    organization_id: str | None,
    metric: str,
    quantity: int = 1,
    case_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Append a usage event. Best-effort: metering never breaks the feature."""
    if not organization_id or metric not in METRICS or quantity <= 0:
        return
    try:
        _db().table("usage_events").insert({
            "organization_id": organization_id,
            "case_id": case_id,
            "metric": metric,
            "quantity": quantity,
            "metadata": metadata,
        }).execute()
    except Exception:
        pass


def _sum_usage(db, organization_id: str, start_iso: str) -> dict[str, int]:
    rows = (
        db.table("usage_events")
        .select("metric, quantity")
        .eq("organization_id", organization_id)
        .gte("created_at", start_iso)
        .limit(10000)
        .execute()
        .data
    ) or []
    totals = {m: 0 for m in METRICS}
    for r in rows:
        totals[r["metric"]] = totals.get(r["metric"], 0) + int(r.get("quantity") or 0)
    return totals


def get_billing(db, organization_id: str) -> dict[str, Any]:
    """Full billing picture: plan, limits, usage this period."""
    start, end = _period_bounds()
    start_iso = start.isoformat()

    sub = (
        db.table("subscriptions").select("*, plans(code, name, price_inr, limits)")
        .eq("organization_id", organization_id)
        .single().execute().data
    )
    usage = _sum_usage(db, organization_id, start_iso)

    if not sub:
        # Fail-open default: FREE-equivalent, no enforced limits
        return {
            "plan": {"code": "FREE", "name": "Free", "price_inr": 0, "limits": {}},
            "status": "ACTIVE",
            "period": {"start": start_iso, "end": end.isoformat()},
            "usage": usage,
            "limits": {},
            "enforced": False,
        }

    plan = sub.get("plans") or {"code": "FREE", "name": "Free", "price_inr": 0, "limits": {}}
    limits = plan.get("limits") or {}
    return {
        "plan": plan,
        "status": sub["status"],
        "period": {"start": start_iso, "end": end.isoformat()},
        "usage": usage,
        "limits": limits,
        "enforced": True,
    }


def within_limit(db, organization_id: str, metric: str, additional: int = 0) -> tuple[bool, dict]:
    """Check whether using `additional` more of `metric` is allowed.

    Returns (allowed, context). Fail-open when plan/limits are missing or
    the limit is null (unlimited). Canceled subscriptions block new usage.
    """
    info = get_billing(db, organization_id)

    if not info["enforced"]:
        return True, {**info, "reason": "no_subscription_record"}
    if info["status"] in ("CANCELED", "PAST_DUE"):
        return False, {**info, "reason": f"subscription_{info['status'].lower()}"}

    limit = (info["limits"] or {}).get(f"{metric}_per_month", None)
    if metric == "cases":
        limit = (info["limits"] or {}).get("cases", None)

    if limit is None:
        return True, {**info, "reason": "unlimited"}

    used = info["usage"].get(metric, 0)
    allowed = (used + additional) <= int(limit)
    return allowed, {**info, "reason": None if allowed else "limit_exceeded"}


def monthly_case_count(db, organization_id: str) -> int:
    """Open cases created in the current period (for the cases limit)."""
    start_iso = _period_bounds()[0].isoformat()
    rows = (
        db.table("cases").select("id")
        .eq("organization_id", organization_id)
        .gte("created_at", start_iso)
        .limit(10000)
        .execute().data
    ) or []
    return len(rows)
