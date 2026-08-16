"""Platform admin API (Phase 17).

Every endpoint requires profiles.is_platform_admin, enforced server-side via
the service-role client. Secret values (API keys) are NEVER returned — only
boolean configured/not-configured status.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.audit import record_audit
from app.security.auth import AuthContext, get_auth_context

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def require_platform_admin(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    profile = svc().table("profiles").select("is_platform_admin").eq("id", ctx.user_id).single().execute()
    if not profile.data or not profile.data.get("is_platform_admin"):
        raise HTTPException(status_code=403, detail="Platform administrator access required")
    return ctx


@router.get("/overview")
async def overview(ctx: AuthContext = Depends(require_platform_admin)):
    db = svc()

    orgs = db.table("organizations").select("id", count="exact").execute().count or 0
    users = db.table("profiles").select("id", count="exact").execute().count or 0
    cases = db.table("cases").select("id", count="exact").execute().count or 0
    documents = db.table("documents").select("id", count="exact").execute().count or 0
    documents_bytes = db.table("documents").select("file_size").limit(10000).execute().data
    storage_bytes = sum(d.get("file_size") or 0 for d in documents_bytes or [])

    jobs = db.table("jobs").select("state").limit(10000).execute().data or []
    job_states: dict[str, int] = {}
    for j in jobs:
        job_states[j["state"]] = job_states.get(j["state"], 0) + 1

    recent_jobs = db.table("jobs").select(
        "id, job_type, state, progress, error_message, created_at"
    ).order("created_at", desc=True).limit(10).execute().data

    # Provider status: booleans only — never expose key material
    providers = {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "web_search": bool(settings.SEARCH_API_KEY),
        "ocr_provider": settings.OCR_PROVIDER,
        "stt": "browser+server" if settings.STT_API_KEY else "browser-only",
        "tts": "browser+server" if settings.TTS_API_KEY else "browser-only",
    }

    # Worker heartbeat: age of the most recent job touch
    worker_healthy = True
    stuck_running = db.table("jobs").select("id, updated_at").eq("state", "RUNNING").limit(1).execute().data

    return {
        "counts": {"organizations": orgs, "users": users, "cases": cases, "documents": documents},
        "storage_bytes": storage_bytes,
        "job_states": job_states,
        "recent_jobs": recent_jobs,
        "providers": providers,
        "worker": {"stuck_running_jobs": len(stuck_running), "healthy": worker_healthy},
        "database": {"connected": True},
    }


@router.get("/organizations")
async def list_organizations(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    orgs = db.table("organizations").select("*").order("created_at", desc=True).range(offset, offset + limit - 1).execute().data
    total = db.table("organizations").select("id", count="exact").execute().count or 0

    memberships = db.table("memberships").select("organization_id, role").limit(10000).execute().data or []
    cases = db.table("cases").select("organization_id").limit(10000).execute().data or []
    member_counts: dict[str, int] = {}
    for m in memberships:
        member_counts[m["organization_id"]] = member_counts.get(m["organization_id"], 0) + 1
    case_counts: dict[str, int] = {}
    for c in cases:
        case_counts[c["organization_id"]] = case_counts.get(c["organization_id"], 0) + 1

    items = [
        {
            **org,
            "member_count": member_counts.get(org["id"], 0),
            "case_count": case_counts.get(org["id"], 0),
        }
        for org in orgs
    ]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/users")
async def list_users(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    q: Optional[str] = None,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    query = db.table("profiles").select("*").order("created_at", desc=True)
    if q:
        query = query.ilike("email", f"%{q}%")
    profiles = query.range(offset, offset + limit - 1).execute().data
    total = db.table("profiles").select("id", count="exact").execute().count or 0

    memberships = db.table("memberships").select(
        "organization_id, role, organizations(name)"
    ).limit(10000).execute().data or []
    by_user: dict[str, list] = {}
    for m in memberships:
        by_user.setdefault(m.get("user_id", ""), []).append(m)

    items = []
    for p in profiles:
        p = dict(p)
        p["is_platform_admin"] = bool(p.get("is_platform_admin"))
        items.append(p)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


class PlatformAdminFlag(BaseModel):
    is_platform_admin: bool


@router.patch("/users/{user_id}/platform-admin")
async def set_platform_admin(
    user_id: str,
    body: PlatformAdminFlag,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    profile = db.table("profiles").select("email").eq("id", user_id).single().execute()
    if not profile.data:
        raise HTTPException(404, "User not found")
    if user_id == ctx.user_id and not body.is_platform_admin:
        raise HTTPException(400, "You cannot revoke your own platform admin access")

    updated = db.table("profiles").update(
        {"is_platform_admin": body.is_platform_admin}
    ).eq("id", user_id).execute().data[0]

    record_audit(
        action="admin.platform_admin_changed",
        actor_id=ctx.user_id,
        resource_type="profile",
        resource_id=user_id,
        metadata={"is_platform_admin": body.is_platform_admin},
    )
    return {"id": updated["id"], "email": updated["email"], "is_platform_admin": body.is_platform_admin}


@router.get("/cases")
async def list_all_cases(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    status: Optional[str] = None,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    query = db.table("cases").select("*").order("updated_at", desc=True)
    if status:
        query = query.eq("status", status)
    rows = query.range(offset, offset + limit - 1).execute().data
    total = db.table("cases").select("id", count="exact").execute().count or 0

    docs = db.table("documents").select("case_id").limit(10000).execute().data or []
    doc_counts: dict[str, int] = {}
    for d in docs:
        doc_counts[d["case_id"]] = doc_counts.get(d["case_id"], 0) + 1

    items = [{**c, "document_count": doc_counts.get(c["id"], 0)} for c in rows]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/jobs")
async def list_all_jobs(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    state: Optional[str] = None,
    job_type: Optional[str] = None,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    query = db.table("jobs").select("*").order("created_at", desc=True)
    if state:
        query = query.eq("state", state)
    if job_type:
        query = query.eq("job_type", job_type)
    rows = query.range(offset, offset + limit - 1).execute().data
    total = db.table("jobs").select("id", count="exact").execute().count or 0
    return {"items": rows, "total": total, "offset": offset, "limit": limit}


@router.get("/agent-runs")
async def list_agent_runs(
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    case_id: Optional[str] = None,
    status: Optional[str] = None,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    query = db.table("agent_runs").select("*").order("started_at", desc=True)
    if case_id:
        query = query.eq("case_id", case_id)
    if status:
        query = query.eq("status", status)
    rows = query.range(offset, offset + limit - 1).execute().data
    total = db.table("agent_runs").select("id", count="exact").execute().count or 0

    run_ids = [r["id"] for r in rows]
    tool_calls = []
    if run_ids:
        tool_calls = db.table("agent_tool_calls").select(
            "agent_run_id, tool_name, status, duration_ms"
        ).in_("agent_run_id", run_ids).limit(1000).execute().data or []
    by_run: dict[str, list] = {}
    for tc in tool_calls:
        by_run.setdefault(tc["agent_run_id"], []).append(tc)

    items = [{**r, "tool_calls": by_run.get(r["id"], [])} for r in rows]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/ai-usage")
async def ai_usage(ctx: AuthContext = Depends(require_platform_admin)):
    db = svc()

    ai_runs = db.table("ai_runs").select(
        "workflow, provider, model, prompt_tokens, completion_tokens, estimated_cost_usd, status"
    ).limit(50000).execute().data or []
    agent_runs = db.table("agent_runs").select(
        "agent_name, status, llm_calls, prompt_tokens, completion_tokens, estimated_cost_usd, elapsed_seconds"
    ).limit(50000).execute().data or []

    def agg(rows, key_field):
        out: dict[str, dict] = {}
        for r in rows:
            key = r.get(key_field) or "unknown"
            slot = out.setdefault(key, {
                "count": 0, "failed": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "estimated_cost_usd": 0.0,
            })
            slot["count"] += 1
            if r.get("status") == "FAILED":
                slot["failed"] += 1
            slot["prompt_tokens"] += r.get("prompt_tokens") or 0
            slot["completion_tokens"] += r.get("completion_tokens") or 0
            slot["estimated_cost_usd"] += float(r.get("estimated_cost_usd") or 0)
        return out

    by_workflow = agg(ai_runs, "workflow")
    by_agent = agg(agent_runs, "agent_name")

    return {
        "totals": {
            "ai_runs": len(ai_runs),
            "agent_runs": len(agent_runs),
            "prompt_tokens": sum(r.get("prompt_tokens") or 0 for r in ai_runs + agent_runs),
            "completion_tokens": sum(r.get("completion_tokens") or 0 for r in ai_runs + agent_runs),
            "estimated_cost_usd": round(
                sum(float(r.get("estimated_cost_usd") or 0) for r in ai_runs + agent_runs), 6
            ),
        },
        "by_workflow": by_workflow,
        "by_agent": by_agent,
    }


@router.get("/audit-events")
async def list_audit_events(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    action: Optional[str] = None,
    organization_id: Optional[str] = None,
    ctx: AuthContext = Depends(require_platform_admin),
):
    db = svc()
    query = db.table("audit_events").select("*").order("created_at", desc=True)
    if action:
        query = query.eq("action", action)
    if organization_id:
        query = query.eq("organization_id", organization_id)
    rows = query.range(offset, offset + limit - 1).execute().data
    total = db.table("audit_events").select("id", count="exact").execute().count or 0
    return {"items": rows, "total": total, "offset": offset, "limit": limit}


@router.get("/audit-events/actions")
async def audit_action_types(ctx: AuthContext = Depends(require_platform_admin)):
    rows = svc().table("audit_events").select("action").limit(50000).execute().data or []
    return {"actions": sorted({r["action"] for r in rows})}
