# Handoff Report: Backend Provider & Database Migration for Rajora AI

**Agent Folder**: `.agents/explorer_survey_1/`  
**Handoff Type**: Hard (Investigation Complete)  
**Date**: 2026-08-20  

---

## 1. Observation

1. **`backend/app/config.py` (lines 53–66)**:
   Existing provider settings are defined via Pydantic `BaseSettings`:
   - `OPENAI_API_KEY: str = ""`
   - `ANTHROPIC_API_KEY: str = ""`
   - `NVIDIA_API_KEY: str = ""`
   - `NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"`
   - `NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"`
   - `OLLAMA_BASE_URL: str = "http://localhost:11434"`
   - `OLLAMA_MODEL: str = "llama3"`
   - `OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"`

2. **`backend/app/ai/provider.py` (lines 64–76, 346–352)**:
   - `BaseLLMProvider` defines abstract methods `complete(request: LLMRequest) -> LLMResponse` and `is_configured() -> bool`.
   - `_PROVIDERS` registry dictionary at line 346 currently contains:
     ```python
     _PROVIDERS: dict[str, BaseLLMProvider] = {
         "nvidia": NvidiaProvider(),
         "ollama": OllamaProvider(),
         "openai": OpenAIProvider(),
         "anthropic": AnthropicProvider(),
         "mock": MockLLMProvider(),
     }
     ```
   - `LLMResponse` accepts fields `content`, `provider`, `model`, `latency_ms`, `prompt_tokens`, `completion_tokens`, and `estimated_cost_usd`.

3. **`supabase/migrations/` (migrations `001_auth_and_orgs.sql` through `013_review_tables_and_contracts.sql`)**:
   - `001_auth_and_orgs.sql`: Defines `organizations(id uuid pk)`, `profiles(id uuid pk fk->auth.users(id))`, and `memberships(id uuid, organization_id uuid fk->organizations, user_id uuid fk->auth.users, role text check (role in ('OWNER', 'ADMIN', 'LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')))`.
   - Helper function `public.can_manage_org(org_id uuid)` checks membership where `role in ('OWNER', 'ADMIN')`.
   - Next available sequence number is `014_rajora_llm_keys.sql`.

4. **`backend/app/api/admin.py` (lines 1–43)**:
   - Uses dependency `require_platform_admin` which checks `profiles.is_platform_admin`.
   - Admin audit logging helper `record_audit(action, actor_id, ...)` is standard across admin endpoints.

5. **`backend/tests/conftest.py` & `backend/tests/fakes/fake_supabase.py`**:
   - `conftest.py` declares `PATCH_TARGETS` list of modules where `create_client` is mocked with `FakeSupabase`.
   - `FakeSupabase` supports `select`, `insert`, `update`, `delete`, `eq`, `filter`, `range`, `order`, `single`, `count="exact"`, and table defaults.

---

## 2. Logic Chain

1. **Configuring Rajora Settings**:
   - *Observation 1* shows how external API services (NVIDIA, Ollama, OpenAI) are declared in `Settings(BaseSettings)`.
   - Adding `RAJORA_BASE_URL`, `RAJORA_SERVICE_API_KEY`, `RAJORA_DEFAULT_MODEL`, `RAJORA_TIMEOUT_SECONDS`, and `RAJORA_INTERNAL_SECRET` to `Settings` in `config.py` and `.env.example` allows seamless environment-based parameter loading.

2. **Implementing `RajoraProvider` in Provider Hierarchy**:
   - *Observation 2* defines `BaseLLMProvider` contracts and the `_PROVIDERS` map.
   - Creating `RajoraProvider(BaseLLMProvider)` with `name = "rajora"` and calling `POST {base_url}/generate` with header `X-API-Key` and body `{"prompt": ..., "max_tokens": ..., "temperature": ...}` fulfills the integration requirement without altering existing providers.
   - Returning `LLMResponse(provider="rajora", estimated_cost_usd=0.0)` guarantees cost isolation.
   - Adding `"rajora": RajoraProvider()` to `_PROVIDERS` exposes it across `ModelRouter` and API endpoints.

3. **Designing Database Migration `014_rajora_llm_keys.sql`**:
   - *Observation 3* establishes the foreign key structure (`organizations.id`, `auth.users.id`) and helper `public.can_manage_org(org_id)`.
   - Designing `public.rajora_llm_keys` with foreign keys to `organizations(id)` and `auth.users(id)`, a partial index `ON public.rajora_llm_keys(key_hash) WHERE active = true`, and RLS policies for `user_id = auth.uid()` and `public.can_manage_org(org_id)` matches platform standards.

4. **Internal Verification & Admin Key Management Endpoints**:
   - *Observation 4* demonstrates how admin security and audit tracking operate.
   - Exposing `POST /internal/rajora/verify-key` (validating `X-Internal-Secret`, hashing `X-API-Key` with SHA-256, querying active keys in `rajora_llm_keys`, and updating `last_used_at`) provides the required verification mechanism.
   - Adding key generation (`POST /api/v1/admin/rajora-keys`) and revocation (`POST /api/v1/admin/rajora-keys/{id}/revoke`) in `admin.py` allows administrators to issue `rj_live_...` keys and store only prefixes + hashes.

5. **Test Strategy**:
   - *Observation 5* indicates `PATCH_TARGETS` in `conftest.py` must include `app.api.rajora`.
   - Creating `backend/tests/test_rajora_provider.py` with mock HTTP fixtures (`AsyncMock` on `httpx.AsyncClient.post`) provides 100% hermetic test execution for `is_configured()`, `complete()`, error handling, and key verification.

---

## 3. Caveats

1. **Live Rajora Instance**: Live self-hosted Rajora inference server was not executed locally during this read-only survey. Unit tests must use mock `httpx` responses matching the JSON specification (`{"text": str, "usage": {"prompt_tokens": int, "completion_tokens": int}}`).
2. **Key Prefix Length**: Requirement specifies 12-character prefix (e.g. `rj_live_abc1`). Generation format must strictly produce `rj_live_` prefixed keys.
3. **No Caveats on Database or Codebase Compatibility**: The schema and provider abstraction are entirely modular and backwards-compatible.

---

## 4. Conclusion

The architecture for Rajora AI integration is completely clear, well-isolated, and ready for phased implementation:
- **Phase 1**: Add 5 settings to `backend/app/config.py` and `.env.example`. Implement `RajoraProvider` in `backend/app/ai/provider.py` and register in `_PROVIDERS`.
- **Phase 2**: Create `supabase/migrations/014_rajora_llm_keys.sql` with table, indexes, and RLS policies.
- **Phase 3 & 4**: Implement `backend/app/api/rajora.py` (`POST /internal/rajora/verify-key`, `GET /api/rajora/health`), mount router in `backend/app/main.py`, and add admin key management endpoints in `backend/app/api/admin.py`.
- **Phase 5 & 6**: Extend test suite in `backend/tests/test_rajora_provider.py` and add `"app.api.rajora"` to `conftest.py` `PATCH_TARGETS`.

---

## 5. Verification Method

1. **Codebase Inspection**:
   - Verify `backend/app/config.py` defines `RAJORA_BASE_URL`, `RAJORA_SERVICE_API_KEY`, `RAJORA_DEFAULT_MODEL`, `RAJORA_TIMEOUT_SECONDS`, `RAJORA_INTERNAL_SECRET`.
   - Verify `backend/app/ai/provider.py` contains `RajoraProvider` and registers `"rajora"` in `_PROVIDERS`.
   - Verify `supabase/migrations/014_rajora_llm_keys.sql` exists with RLS policies and table structure.
   - Verify `backend/app/api/rajora.py` exists with `/internal/rajora/verify-key` and is mounted in `backend/app/main.py`.
2. **Automated Test Execution**:
   - Run `pytest backend/tests/test_rajora_provider.py` to test provider methods, status handling, and key verification.
   - Run `pytest backend/tests` to verify zero regressions across existing test suites.
3. **Invalidation Conditions**:
   - If `BaseLLMProvider.complete` interface signature changes.
   - If `can_manage_org` function definition in `001_auth_and_orgs.sql` is altered.
