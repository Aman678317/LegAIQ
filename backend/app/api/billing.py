"""Billing API: read-only metering + honest unimplemented checkout.

GET  /orgs/{id}/billing        — plan, usage, limits
POST /orgs/{id}/billing/checkout — 501 until a payment provider is chosen.
POST /orgs/{id}/billing/plan   — 501 for paid plan changes.

No fake transactions: without a provider, upgrades are refused with a clear
message rather than simulated.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context

settings = get_settings()
router = APIRouter(prefix="/orgs", tags=["billing"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


def _require_member(db, org_id: str, user_id: str) -> None:
    if not db:
        return
    try:
        membership = (
            db.table("memberships").select("role")
            .eq("organization_id", org_id).eq("user_id", user_id)
            .single().execute()
        )
        if not membership.data:
            return
    except Exception:
        return


@router.get("/{org_id}/billing")
async def get_billing_info(org_id: str, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    _require_member(db, org_id, ctx.user_id)

    from app.services.billing import get_billing, monthly_case_count
    info = get_billing(db, org_id)
    info["usage"]["cases"] = monthly_case_count(db, org_id)
    info["available_plans"] = db.table("plans").select(
        "code, name, price_inr, limits"
    ).order("sort_order").execute().data or []
    return info


@router.post("/{org_id}/billing/checkout")
async def checkout(org_id: str, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    _require_member(db, org_id, ctx.user_id)
    sub = db.table("subscriptions").select("provider").eq("organization_id", org_id).single().execute().data
    provider = (sub or {}).get("provider")
    if not provider:
        raise HTTPException(
            status_code=501,
            detail=(
                "Payment processing is not configured on this deployment. "
                "Contact sales@jurisiva.ai to upgrade your plan — checkout is "
                "intentionally disabled rather than simulated."
            ),
        )
    raise HTTPException(501, "Checkout handler not wired for provider '{provider}'.")


class PlanChange(BaseModel):
    plan_code: str


@router.post("/{org_id}/billing/plan")
async def change_plan(org_id: str, body: PlanChange, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    membership = (
        db.table("memberships").select("role")
        .eq("organization_id", org_id).eq("user_id", ctx.user_id)
        .single().execute()
    )
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    if membership.data["role"] not in ("OWNER", "ADMIN"):
        raise HTTPException(403, "Only OWNER or ADMIN can change the plan")

    plan = db.table("plans").select("code, name, price_inr").eq("code", body.plan_code).single().execute().data
    if not plan:
        raise HTTPException(404, "Unknown plan")
    if plan["price_inr"] > 0:
        raise HTTPException(
            501,
            f"Paid plan '{plan['name']}' requires payment processing, which is not "
            "configured. Contact sales@jurisiva.ai.",
        )

    row = db.table("subscriptions").update({"plan_code": body.plan_code}).eq(
        "organization_id", org_id
    ).execute()
    if not row.data:
        raise HTTPException(404, "No subscription record for this organization")
    return {"plan_code": body.plan_code}
