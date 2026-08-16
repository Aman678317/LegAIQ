"""Organization members management with server-side authorization.

Only OWNER/ADMIN of the organization may manage members. Every permission
change is audit-logged. The last OWNER cannot be removed or demoted.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.audit import record_audit
from app.security.auth import AuthContext, get_auth_context

settings = get_settings()
router = APIRouter(prefix="/orgs", tags=["organizations"])

VALID_ROLES = {"OWNER", "ADMIN", "LAWYER", "REVIEWER", "STAFF", "CLIENT"}
MANAGER_ROLES = {"OWNER", "ADMIN"}


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _require_manager(db, org_id: str, user_id: str) -> str:
    membership = (
        db.table("memberships").select("role")
        .eq("organization_id", org_id).eq("user_id", user_id)
        .single().execute()
    )
    if not membership.data:
        raise HTTPException(403, "Not a member of this organization")
    if membership.data["role"] not in MANAGER_ROLES:
        raise HTTPException(403, "Only OWNER or ADMIN can manage members")
    return membership.data["role"]


def _owner_count(db, org_id: str) -> int:
    rows = (
        db.table("memberships").select("id")
        .eq("organization_id", org_id).eq("role", "OWNER")
        .execute().data
    )
    return len(rows)


@router.get("/{org_id}/members")
async def list_members(org_id: str, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    _require_manager(db, org_id, ctx.user_id)
    rows = (
        db.table("memberships").select("*, profiles(email, full_name)")
        .eq("organization_id", org_id).order("created_at").execute().data
    )
    # Exclude the join key duplication; shape for the UI
    return [
        {
            "id": m["id"], "user_id": m["user_id"], "role": m["role"],
            "created_at": m["created_at"],
            "email": (m.get("profiles") or {}).get("email"),
            "full_name": (m.get("profiles") or {}).get("full_name"),
        }
        for m in rows
    ]


class MemberAdd(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: str = "LAWYER"


@router.post("/{org_id}/members")
async def add_member(org_id: str, body: MemberAdd, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    actor_role = _require_manager(db, org_id, ctx.user_id)
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Allowed: {', '.join(sorted(VALID_ROLES))}")
    if body.role == "OWNER" and actor_role != "OWNER":
        raise HTTPException(403, "Only an OWNER can grant the OWNER role")

    email = body.email.strip().lower()
    profile = db.table("profiles").select("id, email").ilike("email", email).single().execute()
    if not profile.data:
        raise HTTPException(404, "No account exists with that email. The person must sign up first.")

    user_id = profile.data["id"]
    existing = (
        db.table("memberships").select("id")
        .eq("organization_id", org_id).eq("user_id", user_id)
        .execute().data
    )
    if existing:
        raise HTTPException(409, "That person is already a member of this organization")

    row = db.table("memberships").insert({
        "organization_id": org_id, "user_id": user_id, "role": body.role,
    }).execute().data[0]

    record_audit(
        action="member.added",
        actor_id=ctx.user_id,
        organization_id=org_id,
        resource_type="membership",
        resource_id=row["id"],
        metadata={"added_user_id": user_id, "role": body.role},
    )
    return {**row, "email": profile.data["email"]}


class MemberRoleUpdate(BaseModel):
    role: str


@router.patch("/{org_id}/members/{user_id}")
async def update_member_role(
    org_id: str, user_id: str, body: MemberRoleUpdate,
    ctx: AuthContext = Depends(get_auth_context),
):
    db = svc()
    actor_role = _require_manager(db, org_id, ctx.user_id)
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Allowed: {', '.join(sorted(VALID_ROLES))}")
    if body.role == "OWNER" and actor_role != "OWNER":
        raise HTTPException(403, "Only an OWNER can grant the OWNER role")
    if user_id == ctx.user_id and body.role != "OWNER":
        raise HTTPException(400, "You cannot change your own role")

    membership = (
        db.table("memberships").select("id, role")
        .eq("organization_id", org_id).eq("user_id", user_id)
        .single().execute()
    )
    if not membership.data:
        raise HTTPException(404, "Member not found")

    if membership.data["role"] == "OWNER" and body.role != "OWNER" and _owner_count(db, org_id) <= 1:
        raise HTTPException(400, "Cannot demote the last OWNER of the organization")

    row = db.table("memberships").update({"role": body.role}).eq("id", membership.data["id"]).execute().data[0]
    record_audit(
        action="member.role_changed",
        actor_id=ctx.user_id,
        organization_id=org_id,
        resource_type="membership",
        resource_id=membership.data["id"],
        metadata={"target_user_id": user_id, "old_role": membership.data["role"], "new_role": body.role},
    )
    return row


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(org_id: str, user_id: str, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    _require_manager(db, org_id, ctx.user_id)
    if user_id == ctx.user_id:
        raise HTTPException(400, "You cannot remove yourself; transfer ownership first")

    membership = (
        db.table("memberships").select("id, role")
        .eq("organization_id", org_id).eq("user_id", user_id)
        .single().execute()
    )
    if not membership.data:
        raise HTTPException(404, "Member not found")
    if membership.data["role"] == "OWNER" and _owner_count(db, org_id) <= 1:
        raise HTTPException(400, "Cannot remove the last OWNER of the organization")

    db.table("memberships").delete().eq("id", membership.data["id"]).execute()
    record_audit(
        action="member.removed",
        actor_id=ctx.user_id,
        organization_id=org_id,
        resource_type="membership",
        resource_id=membership.data["id"],
        metadata={"removed_user_id": user_id},
    )
    return {"removed": True}
