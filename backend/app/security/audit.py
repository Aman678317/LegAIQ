"""Security audit helper.

Writes to audit_events via the service-role client. Never logs API keys,
passwords, tokens, or document contents — only action, resource ids, and
small metadata. Audit failure must not break the user request.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from app.config import get_settings

settings = get_settings()


def record_audit(
    action: str,
    actor_id: str | None = None,
    organization_id: str | None = None,
    case_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget audit record; swallows errors so requests never fail on it."""
    try:
        db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        db.table("audit_events").insert({
            "actor_id": actor_id,
            "organization_id": organization_id,
            "case_id": case_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # audit is best-effort; never surface to callers


async def record_audit_async(**kwargs) -> None:
    """Async wrapper so endpoints can await without blocking the loop."""
    await asyncio.to_thread(record_audit, **kwargs)
