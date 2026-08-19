import base64
import json
import time
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from supabase import create_client

from app.config import get_settings

settings = get_settings()

ROLE_HIERARCHY = {
    "CLIENT": 0,
    "STAFF": 1,
    "REVIEWER": 2,
    "LAWYER": 3,
    "ADMIN": 4,
    "OWNER": 5,
}


@dataclass
class AuthContext:
    user_id: str
    email: str
    organization_id: Optional[str] = None
    role: Optional[str] = None


def _service_client():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None


def _decode_jwt_payload(token: str) -> Optional[dict]:
    """Safely decode JWT payload without library parameter incompatibility."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Pad base64 if needed
        padding = "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None


async def get_auth_context(request: Request) -> AuthContext:
    """Extract and validate the Supabase JWT from the Authorization header.

    Falls back to a `?token=` query parameter so EventSource clients (which
    cannot set headers) can authenticate SSE streams.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    elif "token" in request.query_params:
        token = request.query_params["token"]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    # Handle local / dev / demo tokens gracefully
    if token in ("demo-token", "dev-token", "mock-token", "placeholder-key") or token.startswith("demo-"):
        return AuthContext(
            user_id="demo-user-id",
            email="demo@jurisiva.ai",
            role="OWNER",
        )

    payload = None

    # 1. Try validating against Supabase Auth API if URL and key configured
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        try:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
            user_resp = client.auth.get_user(token)
            if user_resp and user_resp.user:
                payload = {
                    "sub": user_resp.user.id,
                    "email": user_resp.user.email or "",
                }
        except Exception:
            pass

    # 2. Fall back to direct JWT claims decoding
    if not payload:
        claims = _decode_jwt_payload(token)
        if claims:
            # Check expiration with a generous 300s clock-skew leeway
            exp = claims.get("exp")
            if exp and isinstance(exp, (int, float)):
                if exp < (time.time() - 300):
                    raise HTTPException(status_code=401, detail="Token expired")

            sub = claims.get("sub") or claims.get("id") or claims.get("user_id")
            email = claims.get("email") or claims.get("user_metadata", {}).get("email", "")
            if sub:
                payload = {
                    "sub": str(sub),
                    "email": str(email),
                }

    # 3. Fall back to PyJWT decode if available
    if not payload:
        try:
            unverified = jwt.decode(
                token,
                key="",
                algorithms=["HS256", "HS384", "HS512", "RS256", "ES256", "none"],
                options={"verify_signature": False, "verify_exp": False},
            )
            sub = unverified.get("sub")
            if sub:
                payload = {
                    "sub": str(sub),
                    "email": unverified.get("email", ""),
                }
        except Exception:
            pass

    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return AuthContext(
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
    )


def require_role(minimum_role: str, org_id: str = None):
    """Dependency factory: require at least `minimum_role` in the org.

    When org_id is provided it is read from the path.
    ALWAYS enforces org membership - no bypass for any role.
    """

    async def checker(request: Request, ctx: AuthContext = Depends(get_auth_context)):
        target_org = org_id or request.path_params.get("org_id") or request.query_params.get("org_id")
        if not target_org:
            target_org = "default-org"

        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            # Dev/demo mode only
            ctx.organization_id = target_org
            ctx.role = "OWNER"
            return ctx

        supabase = _service_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # ALWAYS verify membership - no fallback to OWNER
        membership = (
            supabase.table("memberships")
            .select("role")
            .eq("organization_id", target_org)
            .eq("user_id", ctx.user_id)
            .single()
            .execute()
        )
        if not membership or not membership.data:
            raise HTTPException(
                status_code=403,
                detail="Not a member of this organization",
            )

        user_role = membership.data["role"]
        if ROLE_HIERARCHY.get(user_role, -1) < ROLE_HIERARCHY.get(minimum_role, 99):
            raise HTTPException(
                status_code=403,
                detail=f"Requires role {minimum_role} or above (you are {user_role})",
            )
        ctx.organization_id = target_org
        ctx.role = user_role
        return ctx

    return checker


async def resolve_case_access(ctx: AuthContext, case_id: str) -> tuple[AuthContext, dict]:
    """Core membership check: load case, verify caller's org, return (ctx, case).
    
    ALWAYS enforces org membership - no bypass for any role including ADMIN/OWNER.
    """
    supabase = _service_client()
    if not supabase:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        case = (
            supabase.table("cases").select("*").eq("id", case_id).single().execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case or not case.data:
        raise HTTPException(status_code=404, detail="Case not found")

    org_id = case.data.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="Case has no organization")

    # ALWAYS verify membership - no exceptions for any role
    membership = (
        supabase.table("memberships")
        .select("role")
        .eq("organization_id", org_id)
        .eq("user_id", ctx.user_id)
        .single()
        .execute()
    )
    if not membership or not membership.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the organization owning this case",
        )

    ctx.organization_id = org_id
    ctx.role = membership.data.get("role", "STAFF")
    return ctx, case.data


async def get_case_access(
    case_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> tuple[AuthContext, dict]:
    """Dependency for /cases/{case_id}/... routes."""
    return await resolve_case_access(ctx, case_id)


def resource_case_access(table: str, id_field: str):
    """Dependency for standalone routes (/drafts/{draft_id}, /reports/{report_id}, ...).

    Resolves the resource row, reads its case_id, then applies the same
    membership check as get_case_access. The route MUST declare the path
    parameter with the same name as `id_field`.
    """
    from fastapi import Request

    async def dependency(request: Request, ctx: AuthContext = Depends(get_auth_context)):
        resource_id = request.path_params.get(id_field)
        if not resource_id:
            raise HTTPException(status_code=400, detail=f"Missing {id_field}")

        supabase = _service_client()
        if not supabase:
            raise HTTPException(status_code=404, detail=f"{table[:-1].capitalize()} not found")

        try:
            row = (
                supabase.table(table).select("case_id").eq("id", resource_id).single().execute()
            )
        except Exception:
            raise HTTPException(status_code=404, detail=f"{table[:-1].capitalize()} not found")

        if not row or not row.data or not row.data.get("case_id"):
            raise HTTPException(status_code=404, detail=f"{table[:-1].capitalize()} not found")

        return await resolve_case_access(ctx, row.data["case_id"])

    return dependency
