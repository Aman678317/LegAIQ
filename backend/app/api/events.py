"""Server-Sent Events for real-time case updates.

Streams job state changes and document status changes for a case.
The client sees 'completed' only when the backend row actually says so.
"""
import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from supabase import create_client

from app.config import get_settings
from app.security.auth import get_case_access

settings = get_settings()
router = APIRouter(tags=["events"])

POLL_INTERVAL = 2.0  # seconds between DB polls
HEARTBEAT = 15.0     # keep-alive comment frames


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _snapshot(case_id: str) -> dict:
    """Current visible state: jobs + documents keyed for change detection."""
    db = _db()
    jobs = db.table("jobs").select(
        "id, job_type, state, progress, document_id, error_message, updated_at"
    ).eq("case_id", case_id).order("updated_at", desc=True).limit(40).execute().data

    docs = db.table("documents").select(
        "id, file_name, status, page_count, ocr_confidence, error_message, updated_at"
    ).eq("case_id", case_id).order("updated_at", desc=True).limit(60).execute().data

    return {
        "jobs": {j["id"]: j for j in jobs},
        "documents": {d["id"]: d for d in docs},
    }


@router.get("/cases/{case_id}/events")
async def case_events(request: Request, case_id: str, _=Depends(get_case_access)):
    ctx, case = _

    async def generator():
        last_state: dict = {}
        last_beat = 0.0
        # Send an initial full state so newly connected clients sync immediately
        state = _snapshot(case_id)
        yield {
            "event": "state",
            "data": json.dumps({"jobs": list(state["jobs"].values()),
                                "documents": list(state["documents"].values())}),
        }
        last_state = state

        while True:
            if await request.is_disconnected():
                break

            now = asyncio.get_event_loop().time()
            if now - last_beat >= HEARTBEAT:
                yield {"event": "ping", "data": str(int(now))}
                last_beat = now

            await asyncio.sleep(POLL_INTERVAL)
            try:
                state = _snapshot(case_id)
            except Exception:
                continue  # transient DB error: keep the stream alive

            # Diff jobs
            for jid, job in state["jobs"].items():
                prev = last_state["jobs"].get(jid)
                if not prev or any(prev.get(k) != job.get(k) for k in ("state", "progress", "error_message")):
                    yield {"event": "job", "data": json.dumps(job)}

            # Diff documents
            for did, doc in state["documents"].items():
                prev = last_state["documents"].get(did)
                if not prev or any(prev.get(k) != doc.get(k) for k in ("status", "page_count", "ocr_confidence", "error_message")):
                    yield {"event": "document", "data": json.dumps(doc)}

            last_state = state

    return EventSourceResponse(
        generator(),
        ping=None,  # we send our own heartbeats
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
