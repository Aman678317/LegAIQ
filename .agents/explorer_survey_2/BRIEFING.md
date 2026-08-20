# BRIEFING — 2026-08-20T16:00:00Z

## Mission
Investigate the Internal Key Verification & Admin Management architecture for Rajora AI integration.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, analyzer, synthesizer
- Working directory: c:\Users\acer\OneDrive\inga legal\.agents\explorer_survey_2
- Original parent: e3bd4989-9fab-4d09-bd11-f966c3b5047e
- Milestone: rajora_internal_admin_investigation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Produce self-contained analysis.md and handoff.md in .agents/explorer_survey_2

## Current Parent
- Conversation ID: e3bd4989-9fab-4d09-bd11-f966c3b5047e
- Updated: 2026-08-20T16:00:00Z

## Investigation State
- **Explored paths**:
  - `backend/app/main.py`
  - `backend/app/config.py`
  - `backend/app/api/admin.py`
  - `backend/app/api/org.py`
  - `backend/app/api/cases.py`
  - `backend/app/api/billing.py`
  - `backend/app/api/ai.py`
  - `backend/app/security/auth.py`
  - `backend/app/security/audit.py`
  - `supabase/migrations/001_auth_and_orgs.sql`
  - `supabase/migrations/007_rls_policies.sql`
  - `supabase/migrations/011_admin.sql`
  - `backend/tests/conftest.py`
  - `backend/tests/test_api.py`
  - `backend/tests/fakes/fake_supabase.py`
  - `frontend/lib/api.ts`
- **Key findings**:
  - Router mounting: `admin_router` mounted under `API_V1_PREFIX` (`/api/v1`). Internal endpoint `POST /internal/rajora/verify-key` needs direct mounting on `app` or alias under `/api/v1`.
  - Auth: `require_platform_admin` checks `profiles.is_platform_admin`. Internal endpoint secured via `X-Internal-Secret` matching `settings.RAJORA_INTERNAL_SECRET` using `hmac.compare_digest`.
  - DB: Synchronous PostgREST queries using `svc()` (`create_client`), with audit logging via `record_audit`.
  - Keys: Format `rj_live_<48-hex>`, prefix 12 chars, hash SHA-256 in `rajora_llm_keys`. Raw key returned once upon creation.
  - Tests: `PATCH_TARGETS` in `conftest.py` must include `"app.api.rajora"`. `FakeSupabase` handles in-memory query operations.
- **Unexplored areas**: None for this milestone.

## Key Decisions Made
- Confirmed timing-safe secret comparison `hmac.compare_digest` for internal secret.
- Confirmed `PATCH_TARGETS` addition in `conftest.py` is required for testing `app.api.rajora`.

## Artifact Index
- `DISPATCH.md` — Dispatch logs
- `BRIEFING.md` — Situational awareness
- `progress.md` — Liveness tracker
- `analysis.md` — Detailed analysis report
- `handoff.md` — 5-component handoff report
