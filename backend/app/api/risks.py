"""Risk register API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access, resource_case_access

settings = get_settings()
router = APIRouter(tags=["risks"])


def svc():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("/cases/{case_id}/risks")
async def get_risks(case_id: str, resolved: bool = False, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("risks").select("*").eq("case_id", case_id)
        .eq("resolved", resolved).order("created_at", desc=True).execute().data
    )


@router.get("/cases/{case_id}/risks/summary")
async def risk_summary(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    rows = svc().table("risks").select("level").eq("case_id", case_id).eq("resolved", False).execute().data
    counts = {"total": len(rows), "critical": 0, "high": 0, "medium": 0, "low": 0}
    for r in rows:
        counts[r["level"].lower()] = counts.get(r["level"].lower(), 0) + 1
    return counts


class RiskResolve(BaseModel):
    resolved: bool


@router.patch("/risks/{risk_id}")
async def update_risk(risk_id: str, body: RiskResolve, _=Depends(resource_case_access("risks", "risk_id"))):
    ctx, case = _
    db = svc()
    risk = db.table("risks").select("case_id").eq("id", risk_id).single().execute()
    if not risk.data or risk.data["case_id"] != case["id"]:
        from fastapi import HTTPException
        raise HTTPException(404, "Risk not found in this case")
    return db.table("risks").update({"resolved": body.resolved}).eq("id", risk_id).execute().data[0]
