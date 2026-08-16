"""Authentication & authorization dependencies for FastAPI.

Validates Supabase JWTs and enforces role-based access server-side.
The frontend role is never trusted.
"""
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
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


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

    try:
        # Verify against Supabase's JWT secret (HS256)
        payload = jwt.decode(
            token,
            settings.SUPABASE_ANON_KEY if len(settings.SUPABASE_ANON_KEY) > 32 else settings.JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        # Fall back to asking Supabase to validate the session
        try:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
            user = client.auth.get_user(token)
            payload = {"sub": user.user.id, "email": user.user.email}
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    return AuthContext(
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
    )


def require_role(minimum_role: str, org_id: str = None):
    """Dependency factory: require at least `minimum_role` in the org.

    When org_id is provided it is read from the path.
    """

    async def checker(request: Request, ctx: AuthContext = Depends(get_auth_context)):
        target_org = org_id or request.path_params.get("org_id") or request.query_params.get("org_id")
        if not target_org:
            raise HTTPException(status_code=400, detail="organization_id required")

        supabase = _service_client()
        membership = (
            supabase.table("memberships")
            .select("role")
            .eq("organization_id", target_org)
            .eq("user_id", ctx.user_id)
            .single()
            .execute()
        )
        if not membership.data:
            raise HTTPException(status_code=403, detail="Not a member of this organization")

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
    """Core membership check: load case, verify caller's org, return (ctx, case)."""
    supabase = _service_client()
    case = (
        supabase.table("cases").select("*").eq("id", case_id).single().execute()
    )
    if not case.data:
        raise HTTPException(status_code=404, detail="Case not found")

    org_id = case.data["organization_id"]
    membership = (
        supabase.table("memberships").select("role")
        .eq("organization_id", org_id)
        .eq("user_id", ctx.user_id)
        .single()
        .execute()
    )
    if not membership.data:
        raise HTTPException(status_code=403, detail="Not a member of this case's organization")

    ctx.organization_id = org_id
    ctx.role = membership.data["role"]
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
        row = (
            supabase.table(table).select("case_id").eq("id", resource_id).single().execute()
        )
        if not row.data or not row.data.get("case_id"):
            raise HTTPException(status_code=404, detail="Not found")

        return await resolve_case_access(ctx, row.data["case_id"])

    return dependency
