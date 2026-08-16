"""Job status polling API (real-time processing updates)."""
from fastapi import APIRouter, Depends, Query
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access, resource_case_access

settings = get_settings()
router = APIRouter(tags=["jobs"])


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("/cases/{case_id}/jobs")
async def list_jobs(
    case_id: str,
    state: str = Query(default=None),
    document_id: str = Query(default=None),
    limit: int = 50,
    _=Depends(get_case_access),
):
    ctx, case = _
    q = (
        svc().table("jobs").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).limit(limit)
    )
    if state:
        q = q.eq("state", state)
    if document_id:
        q = q.eq("document_id", document_id)
    return q.execute().data


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, _=Depends(resource_case_access("jobs", "job_id"))):
    ctx, case = _
    job = svc().table("jobs").select("*").eq("id", job_id).single().execute()
    if not job.data or job.data.get("case_id") != case["id"]:
        from fastapi import HTTPException
        raise HTTPException(404, "Job not found in this case")
    return job.data
