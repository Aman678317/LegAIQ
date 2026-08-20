"""Matter Shared Spaces API with expiring access links, password protection, and role permissions."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel, Field
from supabase import create_client

from app.config import get_settings
from app.security.auth import AuthContext, get_auth_context, get_case_access, require_role
from app.security.watermark import DocumentWatermarker

settings = get_settings()
router = APIRouter(prefix="/shared-spaces", tags=["shared-spaces"])

# In-memory store for shared spaces when Supabase is running mock/local
_SHARED_SPACES_STORE: Dict[str, Dict[str, Any]] = {}


def _db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def hash_passcode(passcode: str) -> str:
    """Hash passcode using SHA-256 with salt."""
    return hashlib.sha256(f"legaiq_salt_{passcode}".encode()).hexdigest()


class SharedRole(str, Enum):
    VIEWER = "VIEWER"
    REVIEWER = "REVIEWER"
    COLLABORATOR = "COLLABORATOR"


class ExpiryDuration(str, Enum):
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"


class CreateSharedSpaceRequest(BaseModel):
    case_id: str
    name: str = Field(default="Client Review Room", max_length=100)
    recipient_email: str = Field(description="Client/Collaborator email")
    recipient_name: Optional[str] = None
    role: SharedRole = SharedRole.VIEWER
    duration: ExpiryDuration = ExpiryDuration.TWENTY_FOUR_HOURS
    passcode: Optional[str] = Field(None, min_length=4, max_length=50, description="Optional passcode")
    document_ids: Optional[List[str]] = Field(default_factory=list, description="Specific document IDs to share")
    allow_download: bool = True
    watermark_enabled: bool = True


class VerifyPasscodeRequest(BaseModel):
    passcode: str


# ==================== Endpoints ====================

@router.post("/cases/{case_id}/create")
async def create_case_shared_space(
    case_id: str,
    body: CreateSharedSpaceRequest,
    ctx: AuthContext = Depends(require_role("LAWYER")),
):
    """Create an expiring shared space link for external collaborators."""
    # Verify lawyer has access to the case
    _, case = await get_case_access(case_id, ctx)

    share_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)

    # Calculate expiration datetime
    duration_map = {
        ExpiryDuration.ONE_HOUR: timedelta(hours=1),
        ExpiryDuration.TWENTY_FOUR_HOURS: timedelta(hours=24),
        ExpiryDuration.SEVEN_DAYS: timedelta(days=7),
        ExpiryDuration.THIRTY_DAYS: timedelta(days=30),
    }
    expires_at = datetime.now(timezone.utc) + duration_map.get(body.duration, timedelta(hours=24))

    record = {
        "id": share_id,
        "token": token,
        "case_id": case_id,
        "case_name": case.get("name", "Legal Case"),
        "name": body.name,
        "recipient_email": body.recipient_email,
        "recipient_name": body.recipient_name or body.recipient_email.split("@")[0],
        "role": body.role.value,
        "duration": body.duration.value,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": ctx.user_id,
        "is_active": True,
        "has_passcode": bool(body.passcode),
        "passcode_hash": hash_passcode(body.passcode) if body.passcode else None,
        "document_ids": body.document_ids or [],
        "allow_download": body.allow_download,
        "watermark_enabled": body.watermark_enabled,
        "access_count": 0,
        "failed_attempts": 0,
        "last_failed_at": None,
        "last_accessed_at": None,
    }

    _SHARED_SPACES_STORE[share_id] = record
    _SHARED_SPACES_STORE[token] = record

    db = _db()
    try:
        db.table("shared_spaces").insert(record).execute()
    except Exception:
        pass

    share_url = f"/shared/{token}"
    return {
        "share_id": share_id,
        "token": token,
        "share_url": share_url,
        "expires_at": record["expires_at"],
        "recipient_email": record["recipient_email"],
        "role": record["role"],
        "has_passcode": record["has_passcode"],
    }


@router.get("/cases/{case_id}")
async def list_case_shared_spaces(
    case_id: str,
    ctx: AuthContext = Depends(require_role("STAFF")),
):
    """List all shared spaces created for a matter."""
    _, case = await get_case_access(case_id, ctx)

    db = _db()
    spaces = []
    try:
        res = db.table("shared_spaces").select("*").eq("case_id", case_id).execute().data or []
        spaces.extend(res)
    except Exception:
        pass

    # Include in-memory
    mem_spaces = [v for k, v in _SHARED_SPACES_STORE.items() if len(k) == 36 and v.get("case_id") == case_id]
    for m in mem_spaces:
        if not any(s.get("id") == m["id"] for s in spaces):
            spaces.append(m)

    # Sanitize passcode_hash
    now = datetime.now(timezone.utc)
    for s in spaces:
        s.pop("passcode_hash", None)
        exp = datetime.fromisoformat(s["expires_at"].replace("Z", "+00:00")) if isinstance(s.get("expires_at"), str) else s.get("expires_at")
        s["is_expired"] = now > exp if exp else False

    return {"case_id": case_id, "shared_spaces": spaces}


@router.get("/access/{token}")
async def get_public_shared_space(
    token: str,
    request: Request,
):
    """Get metadata for a shared space link (called by client before passcode unlock)."""
    record = _SHARED_SPACES_STORE.get(token)
    if not record:
        db = _db()
        try:
            res = db.table("shared_spaces").select("*").eq("token", token).single().execute().data
            if res:
                record = res
                _SHARED_SPACES_STORE[token] = record
        except Exception:
            pass

    if not record or not record.get("is_active"):
        raise HTTPException(404, "Shared space not found or has been revoked")

    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(410, "This shared space link has expired")

    return {
        "share_id": record["id"],
        "name": record["name"],
        "case_name": record.get("case_name", "Legal Matter"),
        "recipient_email": record["recipient_email"],
        "recipient_name": record.get("recipient_name"),
        "role": record["role"],
        "has_passcode": record["has_passcode"],
        "expires_at": record["expires_at"],
        "watermark_enabled": record["watermark_enabled"],
        "allow_download": record["allow_download"],
    }


@router.post("/access/{token}/verify")
async def verify_shared_space_passcode(
    token: str,
    body: VerifyPasscodeRequest,
    request: Request,
):
    """Verify passcode and return access session for the shared space."""
    record = _SHARED_SPACES_STORE.get(token)
    if not record:
        raise HTTPException(404, "Shared space not found")

    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(410, "Shared space has expired")

    if record.get("has_passcode"):
        expected_hash = record.get("passcode_hash") or ""
        provided_hash = hash_passcode(body.passcode)

        failed_attempts = record.get("failed_attempts", 0)
        last_failed = record.get("last_failed_at")
        if failed_attempts >= 5 and last_failed:
            lockout_end = datetime.fromisoformat(last_failed.replace("Z", "+00:00")) + timedelta(minutes=15)
            if datetime.now(timezone.utc) < lockout_end:
                raise HTTPException(429, "Too many failed passcode attempts. Locked for 15 minutes.")
            else:
                record["failed_attempts"] = 0

        if not hmac.compare_digest(provided_hash.encode("utf-8"), expected_hash.encode("utf-8")):
            record["failed_attempts"] = record.get("failed_attempts", 0) + 1
            record["last_failed_at"] = datetime.now(timezone.utc).isoformat()
            raise HTTPException(401, "Invalid passcode")

        # Reset failed attempts counter upon successful verification
        record["failed_attempts"] = 0

    # Update access stats
    record["access_count"] = record.get("access_count", 0) + 1
    record["last_accessed_at"] = datetime.now(timezone.utc).isoformat()

    db = _db()
    try:
        db.table("shared_spaces").update({
            "access_count": record["access_count"],
            "last_accessed_at": record["last_accessed_at"],
        }).eq("id", record["id"]).execute()
    except Exception:
        pass

    # Retrieve documents
    case_id = record["case_id"]
    doc_ids = record.get("document_ids", [])
    
    docs = []
    try:
        q = db.table("documents").select("id, file_name, file_type, file_size, page_count, created_at, content").eq("case_id", case_id)
        if doc_ids:
            q = q.in_("id", doc_ids)
        docs = q.execute().data or []
    except Exception:
        pass

    client_ip = request.client.host if request.client else "127.0.0.1"

    # Watermark documents if enabled
    watermarked_docs = []
    for d in docs:
        content = d.get("content", "")
        if record.get("watermark_enabled") and content:
            watermarked_text = DocumentWatermarker.apply_text_watermark(
                content,
                viewer_email=record["recipient_email"],
                viewer_ip=client_ip,
            )
        else:
            watermarked_text = content

        watermarked_docs.append({
            "id": d["id"],
            "file_name": d["file_name"],
            "file_type": d.get("file_type", "pdf"),
            "file_size": d.get("file_size", 0),
            "page_count": d.get("page_count", 1),
            "content": watermarked_text,
            "watermark_active": record.get("watermark_enabled", True),
        })

    svg_watermark = DocumentWatermarker.generate_svg_watermark(
        viewer_email=record["recipient_email"],
        viewer_ip=client_ip,
    )

    return {
        "authenticated": True,
        "share_id": record["id"],
        "role": record["role"],
        "case_id": case_id,
        "recipient_email": record["recipient_email"],
        "documents": watermarked_docs,
        "svg_watermark": svg_watermark,
        "expires_at": record["expires_at"],
    }


@router.delete("/{share_id}")
async def revoke_shared_space(
    share_id: str,
    ctx: AuthContext = Depends(require_role("LAWYER")),
):
    """Revoke and invalidate a shared space link immediately."""
    if share_id in _SHARED_SPACES_STORE:
        _SHARED_SPACES_STORE[share_id]["is_active"] = False
    
    db = _db()
    try:
        db.table("shared_spaces").update({"is_active": False}).eq("id", share_id).execute()
    except Exception:
        pass

    return {"status": "revoked", "share_id": share_id}
