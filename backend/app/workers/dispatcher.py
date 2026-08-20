"""Job dispatcher: routes queued jobs from the database to worker tasks."""
from supabase import create_client

from app.config import get_settings

settings = get_settings()


def db():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


def dispatch_pending_jobs(limit: int = 10) -> int:
    """Claim QUEUED jobs and invoke the matching Celery task."""
    from app.workers.tasks import (
        run_ocr, run_extraction, run_embeddings, run_translation,
        run_ownership, run_comparison, run_risk_analysis, run_report, run_report_export,
    )

    TASK_MAP = {
        "ocr": run_ocr,
        "extraction": run_extraction,
        "embeddings": run_embeddings,
        "translation": run_translation,
        "ownership": run_ownership,
        "comparison": run_comparison,
        "risk_analysis": run_risk_analysis,
        "analysis": run_risk_analysis,
        "report": run_report,
        "report_export": run_report_export,
    }

    database = db()
    jobs = (
        database.table("jobs")
        .select("*")
        .eq("state", "QUEUED")
        .order("created_at")
        .limit(limit)
        .execute()
        .data
    )

    dispatched = 0
    for job in jobs:
        task = TASK_MAP.get(job["job_type"])
        if task is None:
            database.table("jobs").update({
                "state": "FAILED", "error_message": f"Unknown job type {job['job_type']}"
            }).eq("id", job["id"]).execute()
            continue

        # Optimistic claim: only dispatch if still QUEUED
        claimed = (
            database.table("jobs")
            .update({"state": "RUNNING", "attempts": job["attempts"] + 1, "progress": 5})
            .eq("id", job["id"])
            .eq("state", "QUEUED")
            .execute()
        )
        if claimed.data:
            task.delay(str(job["id"]))
            dispatched += 1

    return dispatched
