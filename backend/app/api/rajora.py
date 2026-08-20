"""Rajora AI Private LLM endpoints (Health & Internal Key Verification).

Secured internal endpoint verifies private LLM API keys for self-hosted instances.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
import httpx
from supabase import create_client

from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/rajora", tags=["rajora"])
internal_router = APIRouter(prefix="/internal/rajora", tags=["internal-rajora"])


def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


@router.get("/health")
async def rajora_health():
    """Check connectivity and health of the self-hosted Rajora LLM service."""
    start = time.monotonic()
    base_url = (settings.RAJORA_BASE_URL or "").rstrip("/")
    api_key = settings.RAJORA_SERVICE_API_KEY or ""
    model = settings.RAJORA_DEFAULT_MODEL or "rajora-private-v1"

    if not base_url or not api_key:
        return {
            "online": False,
            "status": "unconfigured",
            "provider": "rajora",
            "model": model,
            "latency_ms": 0,
        }

    try:
        timeout = min(getattr(settings, "RAJORA_TIMEOUT_SECONDS", 5) or 5, 5)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"{base_url}/health",
                headers={"X-API-Key": api_key},
            )
            online = resp.status_code == 200
            status = "healthy" if online else f"http_{resp.status_code}"
            latency = int((time.monotonic() - start) * 1000)
            return {
                "online": online,
                "status": status,
                "provider": "rajora",
                "model": model,
                "latency_ms": latency,
            }
    except Exception:
        latency = int((time.monotonic() - start) * 1000)
        return {
            "online": False,
            "status": "unreachable",
            "provider": "rajora",
            "model": model,
            "latency_ms": latency,
        }


@internal_router.post("/verify-key")
async def verify_rajora_key(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Verify raw API key from self-hosted Rajora LLM proxy using internal secret."""
    expected_secret = settings.RAJORA_INTERNAL_SECRET
    if not expected_secret or not x_internal_secret:
        raise HTTPException(status_code=401, detail="Unauthorized: missing or invalid internal secret")

    if not hmac.compare_digest(x_internal_secret.encode("utf-8"), expected_secret.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Unauthorized: invalid internal secret")

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    db = svc()
    if not db:
        raise HTTPException(status_code=500, detail="Database service unavailable")

    res = db.table("rajora_llm_keys").select("*").eq("key_hash", key_hash).eq("active", True).execute()
    rows = res.data if res else []
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    key_record = rows[0]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Update last_used_at timestamp
    db.table("rajora_llm_keys").update({"last_used_at": now_iso}).eq("id", key_record["id"]).execute()

    return {
        "valid": True,
        "active": True,
        "org_id": key_record.get("org_id"),
        "user_id": key_record.get("user_id"),
        "key_prefix": key_record.get("key_prefix"),
        "label": key_record.get("label"),
        "last_used_at": now_iso,
    }
