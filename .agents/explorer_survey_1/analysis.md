# Investigation Report: Backend Provider & Database Migration Architecture for Rajora AI Integration

**Target**: LegAIQ / Jurisiva AI Codebase  
**Date**: 2026-08-20  
**Investigator**: Explorer 1  
**Scope**: Backend LLM Provider abstraction, Supabase SQL migrations, RLS security policies, Admin & Verification API endpoints, and Backend Test Infrastructure.

---

## Executive Summary

The LegAIQ / Jurisiva AI platform currently implements a modular multi-provider AI architecture (`backend/app/ai/provider.py`), an asynchronous worker/API pipeline, and a tenancy model secured via Supabase Row-Level Security (RLS) policies.

To integrate **Rajora AI Private LLM (RAJORA-SOP-AI-2026-04)** as a first-class, sovereign, self-hosted LLM provider:
1. **Configuration**: Extend `backend/app/config.py` with 5 configuration settings (`RAJORA_BASE_URL`, `RAJORA_SERVICE_API_KEY`, `RAJORA_DEFAULT_MODEL`, `RAJORA_TIMEOUT_SECONDS`, `RAJORA_INTERNAL_SECRET`) and document them in `.env.example`.
2. **Provider Implementation**: Implement `RajoraProvider(BaseLLMProvider)` in `backend/app/ai/provider.py`, invoking `POST {RAJORA_BASE_URL}/generate` with header `X-API-Key: {RAJORA_SERVICE_API_KEY}`, body `{"prompt": ..., "max_tokens": ..., "temperature": ...}`, and mapping responses to `LLMResponse(provider="rajora", estimated_cost_usd=0.0)`. Register it in `_PROVIDERS`.
3. **Database Migration**: Create `supabase/migrations/014_rajora_llm_keys.sql` defining `public.rajora_llm_keys` with foreign keys to `public.organizations(id)` and `auth.users(id)`, partial index on `(key_hash) WHERE active = true`, and RLS policies using `public.can_manage_org(org_id)` and `auth.uid() = user_id`.
4. **Key Verification & Management**: Create `backend/app/api/rajora.py` (`POST /internal/rajora/verify-key` and `GET /api/rajora/health`), extend `backend/app/api/admin.py` for key generation/revocation, and register routers in `backend/app/main.py`.
5. **Test Infrastructure**: Leverage `backend/tests/conftest.py` with `FakeSupabase` and `unittest.mock.AsyncMock` on `httpx.AsyncClient` to test `is_configured()`, `complete()`, cost calculation, error mapping, and key verification.

---

## 1. Backend Configuration & Environment (`config.py` & `.env.example`)

### Current State
In `backend/app/config.py`:
- `Settings` inherits from `pydantic_settings.BaseSettings`.
- `model_config = {"env_file": _env_path, "extra": "ignore"}` points to `.env` in the project root.
- Existing AI provider keys:
  - `OPENAI_API_KEY: str = ""`
  - `ANTHROPIC_API_KEY: str = ""`
  - `GOOGLE_API_KEY: str = ""`
  - `GOOGLE_APPLICATION_CREDENTIALS: str = ""`
  - `NVIDIA_API_KEY: str = ""`
  - `NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"`
  - `NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"`
  - `OLLAMA_BASE_URL: str = "http://localhost:11434"`
  - `OLLAMA_MODEL: str = "llama3"`
  - `OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"`

### Required Additions
In `backend/app/config.py`:
```python
    # Rajora AI Private LLM (Self-Hosted / Sovereign Inference)
    RAJORA_BASE_URL: str = "http://localhost:8080"
    RAJORA_SERVICE_API_KEY: str = ""
    RAJORA_DEFAULT_MODEL: str = "rajora-legal-70b"
    RAJORA_TIMEOUT_SECONDS: int = 180
    RAJORA_INTERNAL_SECRET: str = ""
```

In `.env.example`:
```bash
# --- Rajora AI Private LLM (Self-Hosted / Sovereign Inference) ---
RAJORA_BASE_URL=http://localhost:8080
RAJORA_SERVICE_API_KEY=
RAJORA_DEFAULT_MODEL=rajora-legal-70b
RAJORA_TIMEOUT_SECONDS=180
RAJORA_INTERNAL_SECRET=
```

---

## 2. LLM Provider Architecture (`backend/app/ai/provider.py`)

### Current Abstraction
- `BaseLLMProvider(ABC)` declares:
  - `name: str = "base"`
  - `abstractmethod async def complete(self, request: LLMRequest) -> LLMResponse`
  - `abstractmethod def is_configured(self) -> bool`
  - `async def list_models(self) -> list[str]` (default returns `[]`)
- Data classes:
  - `LLMRequest(system: str, prompt: str, task: str = "reasoning", model: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.2, json_mode: bool = False)`
  - `LLMResponse(content: str, provider: str, model: str, latency_ms: int, prompt_tokens: int = 0, completion_tokens: int = 0, estimated_cost_usd: float = 0.0)`
- Provider Registry:
  `_PROVIDERS: dict[str, BaseLLMProvider]` registers singleton provider instances (`"nvidia"`, `"ollama"`, `"openai"`, `"anthropic"`, `"mock"`).
- Routing: `ModelRouter.resolve(task)` resolves to the optimal configured provider, with fallback cascading.

### Concrete Implementation Specification: `RajoraProvider`
```python
class RajoraProvider(BaseLLMProvider):
    """Rajora AI Private LLM provider for self-hosted inference per RAJORA-SOP-AI-2026-04."""

    name = "rajora"

    def is_configured(self) -> bool:
        return bool(settings.RAJORA_BASE_URL and settings.RAJORA_SERVICE_API_KEY)

    async def list_models(self) -> list[str]:
        return [
            settings.RAJORA_DEFAULT_MODEL or "rajora-legal-70b",
            "rajora-legal-8b",
        ]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or settings.RAJORA_DEFAULT_MODEL or "rajora-legal-70b"
        start = time.monotonic()
        base_url = (settings.RAJORA_BASE_URL or "http://localhost:8080").rstrip("/")
        
        # Combine system prompt with user prompt
        prompt_text = f"{request.system}\n\n{request.prompt}" if request.system else request.prompt
        
        headers = {
            "X-API-Key": settings.RAJORA_SERVICE_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt_text,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_mode:
            payload["json_mode"] = True

        timeout = float(settings.RAJORA_TIMEOUT_SECONDS or 180)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/generate",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Handle diverse response envelopes safely
        content = (
            data.get("text")
            or data.get("generated_text")
            or data.get("content")
            or data.get("response")
            or (data.get("choices", [{}])[0].get("message", {}).get("content", "") if "choices" in data else "")
            or ""
        )
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens") or data.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens") or data.get("completion_tokens", 0)

        return LLMResponse(
            content=content,
            provider=self.name,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=0.0,
        )
```

Registration in `_PROVIDERS`:
```python
_PROVIDERS: dict[str, BaseLLMProvider] = {
    "rajora": RajoraProvider(),
    "nvidia": NvidiaProvider(),
    "ollama": OllamaProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "mock": MockLLMProvider(),
}
```

---

## 3. Supabase Schema & Database Migrations

### Existing Database Patterns
- Migrations located in `supabase/migrations/` (current latest is `013_review_tables_and_contracts.sql`).
- Organization tenant isolation table: `public.organizations (id uuid primary key default gen_random_uuid(), name, slug, plan, created_at, updated_at)`.
- User profiles table: `public.profiles (id uuid primary key references auth.users(id) on delete cascade, email, full_name, default_org_id, is_platform_admin)`.
- Memberships table: `public.memberships (id uuid, organization_id uuid references public.organizations(id) on delete cascade, user_id uuid references auth.users(id) on delete cascade, role text check (role in ('OWNER', 'ADMIN', 'LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')))`.
- Key RLS Helper Functions (defined in `001_auth_and_orgs.sql`):
  - `public.is_org_member(org_id uuid)`
  - `public.can_manage_org(org_id uuid)`: returns true if current `auth.uid()` has role `OWNER` or `ADMIN` in the organization.
  - `public.is_platform_admin()`: returns boolean from `public.profiles.is_platform_admin`.

### New Migration: `supabase/migrations/014_rajora_llm_keys.sql`
```sql
-- ============================================================
-- 014: Rajora AI Private LLM Keys & Enterprise Access Control
-- ============================================================

create table if not exists public.rajora_llm_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  key_hash text not null unique,
  key_prefix text not null,
  label text default '',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Indexes for performance & security lookups
create index if not exists idx_rajora_llm_keys_org on public.rajora_llm_keys(org_id);
create index if not exists idx_rajora_llm_keys_user on public.rajora_llm_keys(user_id);
create index if not exists idx_rajora_llm_keys_hash_active on public.rajora_llm_keys(key_hash) where active = true;

-- Row-Level Security
alter table public.rajora_llm_keys enable row level security;

-- Policy 1: Users can view their own keys
create policy "users can read own keys" on public.rajora_llm_keys
  for select using (auth.uid() = user_id);

-- Policy 2: Org Admins / Owners can view and manage all keys within their org
create policy "org admins can manage keys" on public.rajora_llm_keys
  for all using (public.can_manage_org(org_id))
  with check (public.can_manage_org(org_id));
```

---

## 4. API Endpoints & Verification Architecture

### 1. Internal Key Verification (`backend/app/api/rajora.py`)
Exposes:
- `POST /internal/rajora/verify-key`:
  - Enforces `X-Internal-Secret: settings.RAJORA_INTERNAL_SECRET`. Returns `401 Unauthorized` if invalid.
  - Reads `X-API-Key` header (e.g. `rj_live_...`).
  - Computes `hashlib.sha256(raw_key.strip().encode()).hexdigest()`.
  - Queries `rajora_llm_keys` where `key_hash = hash` and `active = true`.
  - If match found: updates `last_used_at = now()` and returns `{"valid": True, "org_id": row["org_id"], "user_id": row["user_id"]}`.
  - If no match: returns `401 Unauthorized` with `{"error": "invalid_or_revoked_key"}`.
- `GET /api/rajora/health` (or `/api/v1/rajora/health`):
  - Checks if `settings.RAJORA_BASE_URL` is reachable and measures latency.
  - Returns `{"online": bool, "latency_ms": int, "base_url": str, "model": settings.RAJORA_DEFAULT_MODEL}`.

### 2. Admin Key Management (`backend/app/api/admin.py`)
Gated by `require_platform_admin` (or org manager):
- `POST /api/v1/admin/rajora-keys`:
  - Body: `{"org_id": str, "user_id": str, "label": Optional[str]}`
  - Generates `raw_key = f"rj_live_{secrets.token_urlsafe(32)}"`
  - Extracts `key_prefix = raw_key[:12]`
  - Computes `key_hash = hashlib.sha256(raw_key.encode()).hexdigest()`
  - Inserts row into `rajora_llm_keys`
  - Returns raw key **once** in response body: `{"id": row["id"], "raw_key": raw_key, "key_prefix": key_prefix, "label": label, "org_id": org_id, "user_id": user_id, "created_at": ...}`
  - Records audit event `admin.rajora_key_created`
- `POST /api/v1/admin/rajora-keys/{id}/revoke`:
  - Sets `active = false` and `revoked_at = now()`
  - Records audit event `admin.rajora_key_revoked`
  - Returns `{"revoked": True, "id": id}`
- `GET /api/v1/admin/rajora-keys`:
  - Lists keys with prefixes, labels, timestamps, active statuses (never revealing raw key or SHA-256 hash)

### 3. Application Router Registration (`backend/app/main.py`)
```python
from app.api.rajora import router as rajora_router

app.include_router(rajora_router)  # includes /internal/rajora and /api/rajora routes
```

---

## 5. Backend Test Infrastructure & Fixture Strategy

### Overview of Test Suite
- `backend/tests/conftest.py` provides:
  - `fake`: Instance of `FakeSupabase` replacing `create_client` in all modules listed in `PATCH_TARGETS`.
  - `api_client` / `admin_api_client`: ASGI test clients with mock auth context.
  - `drain`: Pipeline job runner.
- `backend/tests/fakes/fake_supabase.py`:
  - In-memory mock implementing tables (`cases`, `documents`, `profiles`, `organizations`, `memberships`, etc.) with `select`, `insert`, `update`, `delete`, `eq`, `filter`, `range`, `rpc`.

### Test Extensions for Rajora AI
1. **`PATCH_TARGETS` in `conftest.py`**:
   Add `"app.api.rajora"` to `PATCH_TARGETS` so `svc()` calls inside `rajora.py` use `FakeSupabase`.
2. **`FakeSupabase` Table Support**:
   `rajora_llm_keys` table operates natively with `FakeSupabase.table("rajora_llm_keys")`.
3. **Unit & Integration Tests (`backend/tests/test_rajora_provider.py`)**:
   - `test_rajora_provider_is_configured_true()`: When both `RAJORA_BASE_URL` and `RAJORA_SERVICE_API_KEY` are populated.
   - `test_rajora_provider_is_configured_false()`: When keys are empty.
   - `test_rajora_provider_complete_success()`: Mocking `httpx.AsyncClient.post` to return `{"text": "Response from Rajora", "usage": {"prompt_tokens": 15, "completion_tokens": 30}}`, asserting `LLMResponse(content="Response from Rajora", provider="rajora", estimated_cost_usd=0.0)`.
   - `test_rajora_provider_complete_http_error()`: Mocking HTTP 500 / 401 raises `HTTPStatusError`.
   - `test_internal_verify_key_success()`: Testing `POST /internal/rajora/verify-key` with valid internal secret and active key hash in database.
   - `test_internal_verify_key_invalid_secret()`: Returns 401 when internal secret is missing or incorrect.
   - `test_internal_verify_key_revoked()`: Returns 401 when key is revoked/inactive.
   - `test_admin_key_generation_and_revocation()`: Generating key via admin endpoint, verifying raw key format (`rj_live_...`), prefix match, database hash storage, and subsequent revocation.

---

## 6. Architecture Synthesis & Interoperability Summary

| Component | Responsibility | Interfaces | Safety / Zero-Regression Guardrail |
|:---|:---|:---|:---|
| `config.py` | Environment variable definitions | `Settings` singleton | Optional defaults prevent breaking deployments without Rajora |
| `provider.py` | `RajoraProvider` | `BaseLLMProvider`, `_PROVIDERS` | Isolated class; `_PROVIDERS["mock"]` fallback remains intact |
| `014_rajora_llm_keys.sql` | Storage & RLS for keys | Supabase `organizations`, `auth.users` | Multi-tenant isolation enforced by RLS and `can_manage_org` |
| `app/api/rajora.py` | Secret-gated key check & health | FastAPI route, `settings.RAJORA_INTERNAL_SECRET` | 401 on missing/mismatched secret or inactive key |
| `app/api/admin.py` | Key creation/revocation | Platform admin dependency, `audit_events` | Key hash stored; raw key only returned upon creation |
| `tests/` | Verification & automated regression test | Pytest, `FakeSupabase`, `AsyncMock` | Complete isolated coverage with zero network dependency |

This concludes the architectural investigation for backend provider and database migration aspects of the Rajora AI integration.
