"""Case management API."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.audit import record_audit
from app.security.auth import AuthContext, get_auth_context, get_case_access, require_role

settings = get_settings()
router = APIRouter(prefix="/cases", tags=["cases"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    return create_client(url, key)


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    case_type: str = "PROPERTY"
    organization_id: str
    jurisdiction_state: Optional[str] = None
    jurisdiction_district: Optional[str] = None
    description: Optional[str] = None


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    case_type: Optional[str] = None
    status: Optional[str] = None
    jurisdiction_state: Optional[str] = None
    jurisdiction_district: Optional[str] = None
    description: Optional[str] = None


@router.post("")
async def create_case(body: CaseCreate, ctx: AuthContext = Depends(get_auth_context)):
    db = svc()
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    # Check caller has membership in the target organization
    membership = (
        db.table("memberships").select("role")
        .eq("organization_id", body.organization_id)
        .eq("user_id", ctx.user_id)
        .single()
        .execute()
    )
    if not membership or not membership.data:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    try:
        row = db.table("cases").insert({
            "organization_id": body.organization_id,
            "created_by": ctx.user_id,
            "name": body.name,
            "case_type": body.case_type,
            "jurisdiction_state": body.jurisdiction_state,
            "jurisdiction_district": body.jurisdiction_district,
            "description": body.description,
        }).execute()
        case = row.data[0]

        # Property cases get a property record
        if body.case_type == "PROPERTY":
            try:
                db.table("properties").insert({"case_id": case["id"], "name": body.name}).execute()
            except Exception:
                pass

        try:
            db.rpc("log_activity", {
                "p_case_id": case["id"],
                "p_event_type": "case.created",
                "p_description": f"Case '{body.name}' created",
            }).execute()
        except Exception:
            pass

        try:
            record_audit(
                action="case.created", actor_id=ctx.user_id,
                organization_id=body.organization_id, case_id=case["id"],
                resource_type="case", resource_id=case["id"],
            )
        except Exception:
            pass

        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_cases(
    organization_id: str = Query(...),
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    ctx: AuthContext = Depends(get_auth_context),
):
    db = svc()
    if not db:
        return {"items": [], "total": 0, "offset": offset, "limit": limit}

    # Verify membership
    membership = (
        db.table("memberships").select("role")
        .eq("organization_id", organization_id)
        .eq("user_id", ctx.user_id)
        .single()
        .execute()
    )
    if not membership or not membership.data:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    try:
        q = (
            db.table("cases").select("*")
            .eq("organization_id", organization_id)
            .order("updated_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status:
            q = q.eq("status", status)
        if case_type:
            q = q.eq("case_type", case_type)
        rows = q.execute().data

        total = (
            db.table("cases").select("id", count="exact")
            .eq("organization_id", organization_id).execute().count
        )
        return {"items": rows or [], "total": total or len(rows or []), "offset": offset, "limit": limit}
    except HTTPException:
        raise
    except Exception:
        return {"items": [], "total": 0, "offset": offset, "limit": limit}


@router.get("/{case_id}")
async def get_case(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return case


@router.patch("/{case_id}")
async def update_case(case_id: str, body: CaseUpdate, _=Depends(get_case_access)):
    ctx, case = _
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")
    row = svc().table("cases").update(updates).eq("id", case_id).execute()
    return row.data[0]


@router.delete("/{case_id}")
async def delete_case(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    if ctx.role not in ("OWNER", "ADMIN"):
        raise HTTPException(403, "Only OWNER or ADMIN can delete a case")
    svc().table("cases").delete().eq("id", case_id).execute()
    record_audit(
        action="case.deleted", actor_id=ctx.user_id,
        organization_id=case["organization_id"], case_id=case_id,
        resource_type="case", resource_id=case_id,
    )
    return {"deleted": True}


@router.get("/{case_id}/activity")
async def case_activity(case_id: str, limit: int = 50, _=Depends(get_case_access)):
    ctx, case = _
    rows = (
        svc().table("activity_events").select("*")
        .eq("case_id", case_id).order("created_at", desc=True)
        .limit(limit).execute().data
    )
    return rows


@router.get("/{case_id}/summary")
async def case_summary(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()

    doc_count = db.table("documents").select("id", count="exact").eq("case_id", case_id).execute().count
    processing = db.table("documents").select("id").eq("case_id", case_id).neq("status", "COMPLETED").execute().data
    raw_counts = db.rpc("get_risk_counts", {"p_case_id": case_id}).execute().data

    # Normalize the [{level, count}] RPC shape into the flat dict the UI expects
    summary_counts = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    for row in raw_counts or []:
        level = (row.get("level") or "").lower()
        n = int(row.get("count") or 0)
        if level in summary_counts:
            summary_counts[level] = n
        summary_counts["total"] += n

    return {
        "case": case,
        "document_count": doc_count,
        "processing_count": len(processing),
        "risk_summary": summary_counts,
    }
