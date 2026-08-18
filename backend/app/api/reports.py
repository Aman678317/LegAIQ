"""Report generation API — Property Due Diligence Report."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access, resource_case_access

settings = get_settings()
router = APIRouter(tags=["reports"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


@router.post("/cases/{case_id}/reports")
async def generate_report(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    db = svc()

    report = db.table("reports").insert({
        "case_id": case_id,
        "created_by": ctx.user_id,
        "report_type": "PROPERTY_DUE_DILIGENCE",
        "title": f"Property Due Diligence Report — {case['name']}",
        "status": "RUNNING",
    }).execute().data[0]

    db.table("jobs").insert({
        "case_id": case_id, "job_type": "report",
        "payload": {"report_id": report["id"]},
    }).execute()

    return report


@router.get("/cases/{case_id}/reports")
async def list_reports(case_id: str, _=Depends(get_case_access)):
    ctx, case = _
    return (
        svc().table("reports").select("*").eq("case_id", case_id)
        .order("created_at", desc=True).execute().data
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str, _=Depends(resource_case_access("reports", "report_id"))):
    ctx, case = _
    r = svc().table("reports").select("*").eq("id", report_id).single().execute()
    if not r.data or r.data["case_id"] != case["id"]:
        raise HTTPException(404, "Report not found in this case")
    return r.data


class ExportRequest(BaseModel):
    format: str = "pdf"  # pdf | docx


@router.post("/reports/{report_id}/export")
async def export_report(report_id: str, body: ExportRequest, _=Depends(resource_case_access("reports", "report_id"))):
    ctx, case = _
    if body.format not in ("pdf", "docx"):
        raise HTTPException(400, "format must be pdf or docx")
    job = svc().table("jobs").insert({
        "case_id": case["id"],
        "job_type": "report_export",
        "payload": {"report_id": report_id, "format": body.format},
    }).execute().data[0]
    return {"job_id": job["id"], "format": body.format, "status": "QUEUED"}
