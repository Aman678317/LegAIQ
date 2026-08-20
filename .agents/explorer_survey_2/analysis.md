# Rajora AI Integration — Architecture Investigation Report: Internal Key Verification & Admin Management

**Author**: Explorer 2  
**Date**: 2026-08-20  
**Scope**: Internal Key Verification (`POST /internal/rajora/verify-key`), Admin Key Management (`POST /api/admin/rajora-keys`, `POST /api/admin/rajora-keys/{id}/revoke`), Auth Guards, Database Querying Patterns, and Test Harness Integration.

---

## 1. Executive Summary

This investigation examines the architectural foundation for integrating the self-hosted Rajora AI Private LLM key verification and admin management into LegAIQ / Jurisiva AI.

Key findings:
1. **Routing & Mounting Architecture**: All standard API routers are registered in `backend/app/main.py` under `prefix=settings.API_V1_PREFIX` (`/api/v1`). The platform admin router is mounted with `prefix="/admin"` under `/api/v1` (i.e. `/api/v1/admin/...`). The internal verification route (`POST /internal/rajora/verify-key`) should be mounted at `/internal/rajora/verify-key` (and optionally aliased under `/api/v1/internal/rajora/verify-key` for consistency).
2. **Authentication & Access Control**: Platform admin endpoints strictly require `ctx: AuthContext = Depends(require_platform_admin)`, which verifies `profiles.is_platform_admin == True` via the service-role client. Internal endpoints are secured using pre-shared secret verification (`X-Internal-Secret` matching `settings.RAJORA_INTERNAL_SECRET`) using timing-safe comparison.
3. **Database Access Patterns**: The codebase uses the official Python `supabase` SDK (`create_client(url, key)`) without any direct SQL ORM. Service-role operations use the `svc()` client factory. All queries follow the synchronous PostgREST fluent query API (`table(...).select(...).eq(...).execute()`).
4. **Key Management Lifecycle**: Keys follow the `rj_live_<48-hex>` format. The raw key is returned exactly once upon generation. Only the SHA-256 hash (`key_hash`) and the 12-character prefix (`key_prefix`, e.g. `rj_live_1a2b`) are stored in `rajora_llm_keys`. Revocation sets `active = false` and `revoked_at = now()`. Every admin key operation is logged to `audit_events`.
5. **Testing Framework**: Backend tests use `pytest` with `httpx.AsyncClient` / `ASGITransport` and an in-memory `FakeSupabase` client. Any new API module (e.g. `app.api.rajora`) must be added to `PATCH_TARGETS` in `backend/tests/conftest.py` so that `create_client` is mocked during test runs.

---

## 2. Codebase Routing & Mounting Analysis

### 2.1 Main Router Registration (`backend/app/main.py`)

In `backend/app/main.py`:
- `settings = get_settings()` defines `API_V1_PREFIX = "/api/v1"`.
- Routers are imported and attached to the `FastAPI` application instance:
  ```python
  from app.api.admin import router as admin_router
  # ...
  app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
  ```
- In `backend/app/api/admin.py`:
  ```python
  router = APIRouter(prefix="/admin", tags=["admin"])
  ```
  Resulting URL for admin endpoints: `/api/v1/admin/...`.
- Frontend calls admin endpoints via `frontend/lib/api.ts` which prepends `NEXT_PUBLIC_API_URL` (`http://localhost:8000/api/v1`), so `request("/admin/...")` maps directly to `/api/v1/admin/...`.

### 2.2 Mounting `rajora.py`

To satisfy Requirement R3 (`POST /internal/rajora/verify-key`) and Requirement R4 backend health route (`/api/rajora/health`):
- Create `backend/app/api/rajora.py` with:
  - `internal_router = APIRouter(prefix="/internal/rajora", tags=["internal-rajora"])` (or `router = APIRouter(...)`)
  - `api_router = APIRouter(prefix="/rajora", tags=["rajora"])`
- In `backend/app/main.py`:
  - Mount internal router at root level: `app.include_router(rajora_internal_router)` -> exposes `POST /internal/rajora/verify-key`.
  - Mount API router under `API_V1_PREFIX`: `app.include_router(rajora_router, prefix=settings.API_V1_PREFIX)` -> exposes `GET /api/v1/rajora/health` and `POST /api/v1/internal/rajora/verify-key`.
  - Also provide root-level `@app.get("/api/rajora/health")` or route matching `frontend/app/api/rajora/health/route.ts` target.

---

## 3. Authentication, Role Verification & Security Architecture

### 3.1 AuthContext & Token Validation (`backend/app/security/auth.py`)

- `AuthContext`:
  ```python
  @dataclass
  class AuthContext:
      user_id: str
      email: str = "lawyer@example.com"
      organization_id: Optional[str] = None
      role: Optional[str] = None
  ```
- `get_auth_context(request: Request)` extracts the Bearer token or `?token=` parameter, validates Supabase JWT, and resolves `user_id` and `email`.

### 3.2 Platform Admin Authorization (`backend/app/api/admin.py`)

- Platform admin guard:
  ```python
  async def require_platform_admin(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
      db = svc()
      if not db:
          raise HTTPException(status_code=403, detail="Platform administrator access required")
      try:
          profile = db.table("profiles").select("is_platform_admin").eq("id", ctx.user_id).single().execute()
          if profile and profile.data and profile.data.get("is_platform_admin"):
              return ctx
      except HTTPException:
          raise
      except Exception:
          pass
      raise HTTPException(status_code=403, detail="Platform administrator access required")
  ```
- This check is applied as a FastAPI dependency to all routes in `admin.py`.

### 3.3 Internal Secret Verification

For `POST /internal/rajora/verify-key`:
- The caller is the self-hosted Rajora inference gateway (external to normal user JWT sessions).
- Verification relies on the `X-Internal-Secret` header matching `settings.RAJORA_INTERNAL_SECRET`.
- Timing attack mitigation: Use `hmac.compare_digest(provided_secret, expected_secret)`.
- If `settings.RAJORA_INTERNAL_SECRET` is unset/empty or the header is missing/incorrect, return `HTTPException(status_code=401, detail="Unauthorized internal request")`.

### 3.4 Audit Trail Integration (`backend/app/security/audit.py`)

All key creation and revocation events must call `record_audit(...)`:
- Action strings: `"admin.rajora_key_created"`, `"admin.rajora_key_revoked"`.
- Resource type: `"rajora_key"`.
- `metadata` MUST only contain non-secret info: `{"key_prefix": key_prefix, "label": label, "user_id": user_id}`.
- NEVER record the raw API key or full SHA-256 hash in audit metadata.

---

## 4. Database Schema & Query Patterns

### 4.1 `rajora_llm_keys` Table Schema (Migration 014)

```sql
create table if not exists public.rajora_llm_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  key_hash text not null unique,
  key_prefix text not null,
  label text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

create index if not exists idx_rajora_llm_keys_org on public.rajora_llm_keys(org_id);
create index if not exists idx_rajora_llm_keys_user on public.rajora_llm_keys(user_id);
create index if not exists idx_rajora_llm_keys_hash on public.rajora_llm_keys(key_hash) where active = true;

alter table public.rajora_llm_keys enable row level security;

create policy "users read own keys" on public.rajora_llm_keys
  for select using (auth.uid() = user_id);

create policy "org admins manage keys" on public.rajora_llm_keys
  for all using (public.can_manage_org(org_id))
  with check (public.can_manage_org(org_id));
```

### 4.2 DB Interaction Pattern

The backend uses `supabase-py` synchronous PostgREST client:
```python
def svc():
    url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
    try:
        return create_client(url, key)
    except Exception:
        return None
```

---

## 5. Detailed Endpoint Implementation Specifications

### 5.1 Endpoint: `POST /internal/rajora/verify-key`

- **Location**: `backend/app/api/rajora.py`
- **Request Headers**:
  - `X-Internal-Secret`: String (checked against `settings.RAJORA_INTERNAL_SECRET`)
  - `X-API-Key`: String (the raw Rajora API key)
- **Request Body (Alternative/Optional fallback)**: `{"api_key": "..."}`
- **Processing Logic**:
  1. Validate `X-Internal-Secret` using `hmac.compare_digest`. If invalid -> HTTP 401.
  2. Extract raw key from `X-API-Key` header (or body). If empty -> HTTP 401.
  3. Compute SHA-256 hash: `key_hash = hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()`.
  4. Query `rajora_llm_keys`:
     ```python
     db = svc()
     res = db.table("rajora_llm_keys").select("id, org_id, user_id, active").eq("key_hash", key_hash).eq("active", True).single().execute()
     ```
  5. If no record found or `not res.data` or `res.data.get("active") is not True` -> HTTP 401 ("Invalid or revoked API key").
  6. Update `last_used_at`:
     ```python
     now_iso = datetime.now(timezone.utc).isoformat()
     db.table("rajora_llm_keys").update({"last_used_at": now_iso}).eq("id", res.data["id"]).execute()
     ```
  7. Return HTTP 200 with JSON payload:
     ```json
     {
       "valid": true,
       "org_id": "<uuid>",
       "user_id": "<uuid>",
       "key_id": "<uuid>"
     }
     ```

### 5.2 Endpoint: `POST /api/admin/rajora-keys` (Generate Key)

- **Location**: `backend/app/api/admin.py`
- **Access Guard**: `ctx: AuthContext = Depends(require_platform_admin)`
- **Request Schema**:
  ```python
  class RajoraKeyCreate(BaseModel):
      org_id: str
      user_id: Optional[str] = None
      label: Optional[str] = "Default Rajora Key"
  ```
- **Processing Logic**:
  1. Generate random key: `raw_key = f"rj_live_{secrets.token_hex(24)}"` (total length 56 chars).
  2. Compute prefix: `key_prefix = raw_key[:12]` (e.g. `rj_live_a1b2`).
  3. Compute hash: `key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()`.
  4. Target `user_id = body.user_id or ctx.user_id`.
  5. Insert into `rajora_llm_keys`:
     ```python
     db = svc()
     res = db.table("rajora_llm_keys").insert({
         "org_id": body.org_id,
         "user_id": target_user_id,
         "key_hash": key_hash,
         "key_prefix": key_prefix,
         "label": body.label,
         "active": True,
     }).execute()
     row = res.data[0]
     ```
  6. Record audit:
     ```python
     record_audit(
         action="admin.rajora_key_created",
         actor_id=ctx.user_id,
         organization_id=body.org_id,
         resource_type="rajora_key",
         resource_id=row["id"],
         metadata={"key_prefix": key_prefix, "label": body.label, "user_id": target_user_id},
     )
     ```
  7. Return HTTP 200 with `raw_key` (only returned once):
     ```json
     {
       "id": "<uuid>",
       "org_id": "<uuid>",
       "user_id": "<uuid>",
       "key_prefix": "rj_live_...",
       "label": "Default Rajora Key",
       "active": true,
       "created_at": "...",
       "raw_key": "rj_live_..."
     }
     ```

### 5.3 Endpoint: `POST /api/admin/rajora-keys/{id}/revoke`

- **Location**: `backend/app/api/admin.py`
- **Access Guard**: `ctx: AuthContext = Depends(require_platform_admin)`
- **Processing Logic**:
  1. Lookup key by `id` via `svc()`. If not found -> HTTP 404.
  2. Update record:
     ```python
     now_iso = datetime.now(timezone.utc).isoformat()
     res = db.table("rajora_llm_keys").update({
         "active": False,
         "revoked_at": now_iso,
     }).eq("id", key_id).execute()
     ```
  3. Record audit: `action="admin.rajora_key_revoked"`.
  4. Return HTTP 200:
     ```json
     {
       "id": "<uuid>",
       "active": false,
       "revoked_at": "..."
     }
     ```

### 5.4 Endpoint: `GET /api/admin/rajora-keys` (List Keys)

- **Location**: `backend/app/api/admin.py`
- **Access Guard**: `ctx: AuthContext = Depends(require_platform_admin)`
- **Query Params**: `org_id: Optional[str] = None`, `limit: int = 50`, `offset: int = 0`.
- Returns key metadata list excluding `key_hash`.

---

## 6. Testing Strategy & Harness Requirements

### 6.1 `backend/tests/conftest.py` Updates
- `PATCH_TARGETS` must include `"app.api.rajora"`:
  ```python
  PATCH_TARGETS = [
      # ...
      "app.api.admin",
      "app.api.rajora",
      # ...
  ]
  ```

### 6.2 Test Cases to Implement in `backend/tests/test_api.py` (or `test_rajora_api.py`)

| Test Case | Description | Expected Outcome |
|---|---|---|
| `test_verify_key_success` | Valid `X-Internal-Secret` and valid `X-API-Key` matching active key hash | HTTP 200, returns `{org_id, user_id}`, touches `last_used_at` |
| `test_verify_key_invalid_secret` | Missing or invalid `X-Internal-Secret` | HTTP 401 |
| `test_verify_key_invalid_key` | Unregistered API key | HTTP 401 |
| `test_verify_key_revoked_key` | API key with `active = false` | HTTP 401 |
| `test_admin_create_rajora_key` | Platform admin creates key for org | HTTP 200, `raw_key` returned, SHA-256 in DB, audit log written |
| `test_admin_create_rajora_key_forbidden` | Non-admin user attempts key creation | HTTP 403 |
| `test_admin_revoke_rajora_key` | Platform admin revokes key by ID | HTTP 200, `active=false`, subsequent verification returns 401 |
| `test_admin_revoke_rajora_key_forbidden` | Non-admin user attempts key revocation | HTTP 403 |
| `test_admin_revoke_unknown_key` | Revoking non-existent key ID | HTTP 404 |

---

## 7. Next Steps for Implementer

1. Create `supabase/migrations/014_rajora_llm_keys.sql` (handled by Milestone 9.2).
2. Create `backend/app/api/rajora.py` implementing `POST /internal/rajora/verify-key` and `GET /health`.
3. Add key generation and revocation endpoints to `backend/app/api/admin.py`.
4. Register `rajora` routers in `backend/app/main.py`.
5. Add `"app.api.rajora"` to `PATCH_TARGETS` in `backend/tests/conftest.py`.
6. Write unit and integration tests covering verification, key creation, revocation, and security guards.
