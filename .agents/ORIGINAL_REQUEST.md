# Original User Request

## 2026-08-20T15:53:42Z

Integrate the Rajora AI Private LLM (self-hosted inference per RAJORA-SOP-AI-2026-04) into LegAIQ / Jurisiva AI as a first-class provider across backend, Supabase database, admin API, and Next.js frontend without breaking existing providers.

Working directory: c:\Users\acer\OneDrive\inga legal
Integrity mode: development

## Requirements

### R1. Backend Provider Implementation (Phase 1)
- Extend `backend/app/config.py` with `RAJORA_BASE_URL`, `RAJORA_SERVICE_API_KEY`, `RAJORA_DEFAULT_MODEL`, `RAJORA_TIMEOUT_SECONDS`, and `RAJORA_INTERNAL_SECRET`.
- Implement `RajoraProvider(BaseLLMProvider)` in `backend/app/ai/provider.py` implementing `is_configured()` and `complete()`.
- Send requests to `POST {RAJORA_BASE_URL}/generate` with `X-API-Key: {RAJORA_SERVICE_API_KEY}` header and body `{"prompt": str, "max_tokens": int, "temperature": float}`.
- Map errors to raised exceptions. Set `estimated_cost_usd=0.0` and `provider="rajora"` on `LLMResponse`.
- Register `rajora` in `_PROVIDERS` registry.
- Update `.env.example` with matching configuration keys and comments.

### R2. Database Schema & Row-Level Security Migration (Phase 2)
- Create `supabase/migrations/014_rajora_llm_keys.sql` creating `rajora_llm_keys` (`id uuid pk`, `org_id uuid fk->organizations`, `user_id uuid fk->auth.users`, `key_hash text unique`, `key_prefix text`, `label text`, `active boolean default true`, `created_at`, `last_used_at`, `revoked_at`).
- Add indexes on `org_id`, `user_id`, and `key_hash where active`.
- Enable RLS with a policy for users to select their own keys (`user_id = auth.uid()`) and org admins to manage keys (using `public.can_manage_org(org_id)` or checking `memberships` with role in `('OWNER', 'ADMIN')` matching the schema in `001_auth_and_orgs.sql`).

### R3. Internal Key-Verification Endpoint & Admin Key Management (Phases 3 & 4)
- Create `backend/app/api/rajora.py` exposing `POST /internal/rajora/verify-key`, secured by header `X-Internal-Secret` matching `settings.RAJORA_INTERNAL_SECRET`.
- Hash incoming `X-API-Key` with SHA-256 and look up active key in `rajora_llm_keys`; touch `last_used_at` and return `{org_id, user_id}` on hit, 401 on miss. Register router in `backend/app/main.py`.
- In `backend/app/api/admin.py`, implement admin-role-gated endpoints:
  - `POST /api/admin/rajora-keys`: generate raw key (`rj_live_...`), store SHA-256 hash + 12-char prefix + org/user IDs, and return raw key once in response body.
  - `POST /api/admin/rajora-keys/{id}/revoke`: set `active = false` and `revoked_at = now()`.

### R4. Frontend Client, Health Proxy & Model Selection UI (Phase 5)
- Implement `frontend/lib/rajora.ts` with `checkRajoraStatus()` returning `{online, latency_ms}`.
- Create `frontend/app/api/rajora/health/route.ts` proxying to `${process.env.BACKEND_URL}/api/rajora/health` (with backend health route).
- Add `rajora-private` ("Rajora Private LLM", provider: "rajora", badge: "Private · Zero Third-Party") to model selectors in `frontend/lib/aiEngine.ts` and relevant chat/drafting selectors.
- Update `frontend/app/(app)/settings/page.tsx` with a read-only status card showing Rajora connection state and admin link.

### R5. Documentation & Project Tracking (Phase 6)
- Update `PROJECT.md` feature table with the private-LLM provider milestone marked as DONE.
- Document deployment notes and manual infra setup steps outside the repo.

## Acceptance Criteria

### Automated Backend Tests
- [ ] `pytest backend/tests -k rajora` passes with tests for `is_configured()`, mocked httpx success response mapping to `LLMResponse`, and error status handling.
- [ ] Full backend test suite passes with zero regressions.

### Automated Frontend Tests
- [ ] `frontend/lib/rajora.test.ts` passes for online and offline cases.
- [ ] Model selector tests verify `rajora-private` entry presence and proper request payload generation with `provider: "rajora"`.
- [ ] Frontend test suite (`vitest` / unit tests) passes with zero regressions.

### Security & Integrity Guardrails
- [ ] No API keys, secrets, or raw employee keys are hardcoded in source files or committed fixtures.
- [ ] All database RLS policies enforce tenant isolation based on `organization_id` and `auth.uid()`.
- [ ] Existing provider behavior (NVIDIA, Ollama, OpenAI, Anthropic, Mock) remains fully intact and unmodified.
