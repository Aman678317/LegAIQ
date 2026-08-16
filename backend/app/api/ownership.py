"""Ownership graph and timeline API."""
from fastapi import APIRouter, Depends
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access

settings = get_settings()
router = APIRouter(tags=["ownership"])


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("/cases/{case_id}/ownership")
async def get_ownership_graph(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()
    nodes = db.table("ownership_nodes").select("*").eq("case_id", case_id).execute().data
    edges = db.table("ownership_edges").select("*").eq("case_id", case_id).execute().data
    return {"nodes": nodes, "edges": edges}


@router.post("/cases/{case_id}/ownership/rebuild")
async def rebuild_ownership(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    job = svc().table("jobs").insert({
        "case_id": case_id, "job_type": "ownership", "payload": {},
    }).execute().data[0]
    return {"job_id": job["id"], "status": "QUEUED"}


@router.get("/cases/{case_id}/timeline")
async def get_timeline(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("timeline_events").select(
            "*, documents(file_name)"
        ).eq("case_id", case_id).order("sort_date", desc=False, nullsfirst=False).execute().data
    )
