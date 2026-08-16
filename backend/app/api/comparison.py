"""Multi-document comparison API."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access

settings = get_settings()
router = APIRouter(tags=["comparison"])


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class CompareRequest(BaseModel):
    document_ids: List[str] = Field(min_length=2, max_length=6)


@router.post("/cases/{case_id}/compare")
async def compare_documents(case_id: str, body: CompareRequest, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()

    # Verify all documents belong to this case
    docs = db.table("documents").select("id, file_name").eq("case_id", case_id).in_(
        "id", body.document_ids
    ).execute().data
    if len(docs) < 2:
        raise HTTPException(400, "At least 2 documents from this case are required")

    job = db.table("jobs").insert({
        "case_id": case_id,
        "job_type": "comparison",
        "payload": {"document_ids": body.document_ids},
    }).execute().data[0]
    return {"job_id": job["id"], "status": "QUEUED"}


@router.get("/cases/{case_id}/comparison")
async def get_comparison_results(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("comparison_results").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).execute().data
    )
