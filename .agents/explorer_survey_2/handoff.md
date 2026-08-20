# Handoff Report: Internal Key Verification & Admin Management Architecture

**Agent**: Explorer 2  
**Date**: 2026-08-20  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

1. **Router Registration (`backend/app/main.py:62-116`)**:
   - `admin_router` is imported from `app.api.admin` and registered as:
     ```python
     app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
     ```
   - `settings.API_V1_PREFIX` is `"/api/v1"` (from `backend/app/config.py:12`).
   - `backend/app/api/admin.py:18` defines `router = APIRouter(prefix="/admin", tags=["admin"])`.
   - Admin routes therefore expose paths under `/api/v1/admin/...`.
   - `frontend/lib/api.ts:4` defines `const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";` and makes requests to `/admin/...` which resolve to `${API_URL}/admin/...`.

2. **Platform Admin Authorization (`backend/app/api/admin.py:30-43`)**:
   - Platform admin requirement is enforced via FastAPI dependency:
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

3. **Supabase & Database Query Pattern (`backend/app/api/admin.py:21-27` & throughout API files)**:
   - Database operations use `supabase.create_client(url, key)`:
     ```python
     def svc():
         url = settings.SUPABASE_URL or "https://placeholder.supabase.co"
         key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY or "placeholder-key"
         try:
             return create_client(url, key)
         except Exception:
             return None
     ```
   - There is no SQL ORM or async connection pool; queries are synchronous PostgREST builder calls (`db.table(...).select(...).execute()`).
   - Audit trail is recorded via `record_audit(action, actor_id, organization_id, resource_type, resource_id, metadata)` in `backend/app/security/audit.py:18-41`.

4. **Testing Infrastructure (`backend/tests/conftest.py:12-38`, `backend/tests/test_api.py:87-109`)**:
   - `conftest.py` declares `PATCH_TARGETS` list containing modules patched with `FakeSupabase()`.
   - `api_client` provides a client with a normal user context (`USER_ID`, `is_platform_admin: False`).
   - `admin_api_client` provides a client with admin context (`ADMIN_USER_ID`, `is_platform_admin: True`).
   - Existing admin guard tests in `backend/tests/test_api.py:87-109` verify 403 for non-admins and 200 for admins.

---

## 2. Logic Chain

1. **Routing Strategy**:
   - Based on Observation 1, creating `POST /internal/rajora/verify-key` requires mounting an internal router (e.g. `rajora_internal_router` with prefix `"/internal/rajora"`) in `backend/app/main.py` directly on `app`.
   - For backend health checking (`/api/rajora/health` / `/api/v1/rajora/health`), mounting `rajora_router` under `settings.API_V1_PREFIX` in `main.py` provides parity with other services like SSO, PII, and Analytics.

2. **Security & Authentication for Key Verification**:
   - Based on Observation 2 & Requirements R1/R3, key verification is an automated service-to-service call from the self-hosted inference gateway.
   - It cannot use user JWTs; it must use `X-Internal-Secret` matching `settings.RAJORA_INTERNAL_SECRET`.
   - Using `hmac.compare_digest` prevents timing side-channel attacks on the internal secret.
   - Incoming keys passed via `X-API-Key` (or body) must be hashed via SHA-256 (`hashlib.sha256(raw_key.encode()).hexdigest()`) and looked up against active rows in `rajora_llm_keys`.

3. **Admin Endpoints Security & Implementation**:
   - Based on Observation 2 and 3, `POST /api/admin/rajora-keys` and `POST /api/admin/rajora-keys/{id}/revoke` must be added to `backend/app/api/admin.py` gated with `Depends(require_platform_admin)`.
   - Generation: Generate raw key `rj_live_<48-hex>`, compute `key_prefix = raw_key[:12]`, store SHA-256 hash in `rajora_llm_keys`, and return `raw_key` once.
   - Revocation: Update `active = False` and `revoked_at = now()`.
   - Audit logging must be emitted for both actions via `record_audit(...)`.

4. **Test Fixtures & Harness Completeness**:
   - Based on Observation 4, when `backend/app/api/rajora.py` is introduced, `"app.api.rajora"` MUST be appended to `PATCH_TARGETS` in `backend/tests/conftest.py`.
   - The in-memory `FakeSupabase` query engine automatically supports `select`, `insert`, `update`, and `delete` on `rajora_llm_keys`.

---

## 3. Caveats

1. **Internal Secret Configuration**: `RAJORA_INTERNAL_SECRET` must be set in `backend/app/config.py` with a default in development, and empty/missing secrets in production must reject all internal verification requests.
2. **Key Prefix Length**: Requirement specifies 12-char prefix (e.g. `rj_live_abcd`). Implementer should ensure prefix extraction uses `raw_key[:12]`.
3. **Database Migration Dependency**: Key verification and admin endpoints rely on the `rajora_llm_keys` table defined in `supabase/migrations/014_rajora_llm_keys.sql` (handled by Milestone 9.2).

---

## 4. Conclusion

The architecture for internal key verification and admin management is straightforward and conforms seamlessly with the existing codebase patterns:
- Implement `POST /internal/rajora/verify-key` and health routes in `backend/app/api/rajora.py` and mount in `backend/app/main.py`.
- Implement `POST /api/admin/rajora-keys` and `POST /api/admin/rajora-keys/{id}/revoke` in `backend/app/api/admin.py` protected by `require_platform_admin`.
- Register `"app.api.rajora"` in `PATCH_TARGETS` in `backend/tests/conftest.py` and add full test coverage in `backend/tests/test_api.py` / `test_rajora_api.py`.

---

## 5. Verification Method

To independently verify these findings:
1. Inspect router declarations and mounts:
   - `backend/app/main.py` lines 62–116
   - `backend/app/api/admin.py` lines 18–43
2. Inspect admin and auth testing:
   - `backend/tests/conftest.py` lines 12–38 (`PATCH_TARGETS`) and lines 237–271 (`admin_api_client`)
   - `backend/tests/test_api.py` lines 87–109 (`TestAdminGuard`)
3. Invalidation conditions:
   - If admin routes are moved to an independent sub-application without `API_V1_PREFIX`.
   - If an ORM like SQLAlchemy is introduced to replace the Supabase PostgREST client.
