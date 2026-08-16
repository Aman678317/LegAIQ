# Jurisiva AI — Implementation Audit

**Date:** 2026-08-16
**Status:** Phases 1–20 complete — 67 backend tests + 10 Playwright browser tests, all passing

## Starting State

The repository was effectively empty (one OneNote URL shortcut). This is a
greenfield implementation of the Jurisiva AI platform per the 100-Page Master
Blueprint, with Harvey.ai as the design reference for the landing page.

## Current Architecture

```
┌────────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Next.js 16 (App   │────▶│  FastAPI (Python    │────▶│  Supabase        │
│  Router) Frontend  │     │  3.12) API          │     │  PostgreSQL      │
│  - Landing page    │     │  - /api/v1/*        │     │  + RLS          │
│  - Auth pages      │     │  - JWT validation   │     │  + pgvector     │
│  - Case workspace  │     │  - RBAC (6 roles)   │     │  + Auth         │
│    (12 modules)    │     │  - SSRF guard       │     │  + Storage      │
└────────────────────┘     └─────────┬───────────┘     └──────────────────┘
                                     │
                           ┌─────────▼───────────┐
                           │  Celery Workers     │
                           │  + Redis queue      │
                           │  OCR → Extraction → │
                           │  Embeddings →       │
                           │  Ownership → Risks  │
                           └─────────────────────┘
```

## Working Components

### Frontend (17 routes, builds clean)
- Landing page: hero, product, how-it-works, 8 capability cards, enterprise
  section, 4-tier pricing, FAQ, CTA, footer (Harvey.ai-inspired dark theme)
- Auth: signup, login, password reset request, PKCE email callback
- App shell: sidebar with case-scoped navigation, org switcher, sign-out
- Dashboard: case list, create-case form (9 case types, Indian states)
- Case workspace: 12 modules — home, documents (+viewer with OCR text,
  per-page translation, document explanation), analysis (entities + findings),
  property (field-level verification badges), ownership chain (evidence-linked
  edges), timeline, comparison (multi-select, MATCH/MISMATCH verdicts),
  risks (severity dashboard, resolve), research (citations with source links),
  questions (RAG chat with citations), drafting studio (12 draft types,
  versioning), reports (due diligence, PDF export)

### Backend (13 API routers, all compile)
- JWT auth + server-side RBAC (frontend role never trusted); SSE streams
  authenticate via short-lived `?token=` (EventSource cannot send headers)
- Case CRUD + activity feed + summaries
- Document upload with MIME/size validation → private storage → job queue
- SSRF guard for web research (blocks localhost/private/metadata IPs)
- LLM router: OpenAI + Anthropic + clearly-labelled mock fallback
- OCR abstraction: Tesseract (11 Indian language packs in Docker) + mock
- Extraction: LLM with regex fallback; every entity carries source text,
  page, confidence, verification status
- RAG: pgvector similarity + Postgres full-text hybrid search, case-scoped
- Ownership graph, timeline, comparison, risk engine (evidence-required)
- Research agent: Tavily search → SSRF-validated fetch → grounded synthesis
- Drafting agent: facts from verified extraction only, [VERIFY:] placeholders,
  followed by a mandatory Verification Agent pass (fact-check + citation check)
- Reports: compiled by the budgeted ReportAgent; dependency-free PDF export
- AI run tracking (provider, model, tokens, latency) — no chain-of-thought

### Agent System (Phase 13)
- `BaseAgent` with per-run budgets: max LLM calls, prompt/completion tokens,
  cost (USD estimate), wall-clock time, and iteration cap (loop prevention)
- `ToolRegistry` — 7 tools (document/entity/graph/comparison/risk search,
  web search, citation check), each declaring JSON schema, required
  permission, timeout, and per-run rate limit; every call audited to
  `agent_tool_calls` (params truncated, never document content)
- Permission model: agents can only call tools their context grants;
  violations raise before execution
- Concrete agents: RiskAgent (evidence-anchored risk phrasing; deterministic
  evidence scan always runs as the floor), ReportAgent, VerificationAgent
  (draft fact-check: placeholders, unverified numbers, semantic checks),
  VoiceAgent (short speakable answers, language matching, budget-capped)
- All runs recorded in `agent_runs` with usage, cost, latency, outcome

### Real-time (SSE)
- `GET /api/v1/cases/{id}/events` — Server-Sent Events streaming job and
  document status diffs, 15s heartbeats, initial full-state sync
- Frontend `useCaseEvents` hook: EventSource with automatic fallback to
  5s polling if the stream drops; UI shows honest Live/Polling/Synced badges
- Documents page and Case Home update statuses live without manual refresh

### Database (10 migrations, idempotent)
- 29 tables covering organizations → cases → documents → pages → entities →
  graph → risks → research → drafts → reports → agents → voice → audit
- Row-level security on every table, case-scoped policies via helper functions
- Storage buckets (private) with path-scoped access policies
- RPC functions: vector match, keyword search, risk counts

### Voice Assistant (Phase 16)
- `POST /cases/{id}/voice/session` → session per case with language
- `POST /cases/{id}/voice/message` — transcript → VoiceAgent (case-grounded
  RAG, speakable answers, language matching) → answer + citations
- VoicePanel UI: browser Web Speech API STT (en/hi/kn/ta/te/ml/mr/bn/gu/pa/ur
  with Indian locales) + speechSynthesis TTS with mute; citations link to
  the source document page; explicit "AI assistant, not a human lawyer" notice
- Every turn persisted to `voice_turns` with STT/TTS provider attribution

### Admin Panel + Audit (Phase 17)
- `profiles.is_platform_admin` flag (migration 011) — promote via one SQL line;
  enforced server-side on every /admin route, UI guard is cosmetic only
- Admin API: overview (counts, job states, provider status as booleans only —
  keys never exposed), organizations, users (+ platform-admin grant/revoke with
  self-revocation protection), cases, jobs, agent runs (+ tool-call details),
  AI usage aggregated by workflow/agent (tokens, cost, failures), audit events
  (+ action filter)
- Audit trail: case created/deleted, document uploaded/downloaded, member
  added/role-changed/removed, platform-admin changes — all via
  `record_audit()` (best-effort; never logs content or secrets)
- Org members management API (`/orgs/{id}/members`): OWNER/ADMIN gated,
  last-OWNER protection, duplicate/unknown-email handling — with a Settings
  page UI for member roles
- Admin UI (8 pages) + Settings page; "Admin Panel" sidebar entry appears
  only for platform admins

### Test Suite (Phase 18) — 54 tests, all passing
- **Harness:** `tests/fakes/fake_supabase.py` — in-memory Supabase REST
  emulator (chained queries, filters, order/range/limit, count, upsert with
  conflict keys, table defaults, nested-select joins, rpc for keyword search
  / risk counts / log_activity, storage buckets) so the ENTIRE pipeline runs
  with no database, network, or external services
- **Unit:** SSRF guard (public allowed; file/ftp/localhost/private/link-local/
  metadata/reserved blocked; DNS-rebinding to private IPs blocked), RAG
  chunker (coverage, overlap, thresholds), regex extraction (survey/hissa/
  khata/amount/date/parties; no false positives), agent budgets (LLM-call,
  token, cost caps), loop prevention, tool governance (permission denied,
  rate limit per run, timeout, JSON-schema validation)
- **API:** health, 401 without token, case lifecycle (create/list/get/update/
  404/activity), admin 403 for non-admins, self-revocation guard, member
  add/duplicate/unknown-email/role-change/remove, last-OWNER protection
- **E2E pipeline:** create case → upload 2 documents → queued OCR → page-by-page
  OCR (originals untouched) → regex extraction with evidence → chunking →
  ownership graph (person/property nodes, evidenced edges) → comparison
  (survey-number MISMATCH) → HIGH/BOUNDARY risk with evidence → case summary
  → budgeted ReportAgent → PDF export (valid %PDF header) → drafting with
  auto verification block → grounded chat with real citations → every job
  COMPLETED, none FAILED; bad MIME/empty uploads rejected
- Bugs the tests caught and fixed: `has_permission` on wrong class (agent
  tools would crash at runtime), tool-registry rate limiter defeated by its
  own cleanup, missing `SEARCH_API_KEY` setting, risk-summary shape mismatch
  between RPC and UI, standalone routes 422ing (`/drafts/{id}` etc. resolved
  via `resource_case_access` factory)
- Run: `cd backend && python -m pytest tests/ -q` (deps: requirements-dev.txt)

### Infrastructure
- docker-compose.yml (Postgres, Redis, MinIO, backend, worker, frontend)
- render.yaml (web + worker + beat + Redis + frontend, all wired)
- Dockerfile with tesseract-ocr + 11 Indian language packs

## Known Limitations / Not Yet Implemented

1. **Google Vision OCR** — provider stub raises NotImplementedError; use tesseract
2. **DOCX export** — PDF only (dependency-free implementation)
3. **Billing go-live** — Razorpay/Stripe adapters are implemented and tested but
   inert until keys + webhook URLs are configured (per spec: no fake transactions)
4. **Research in-request** — runs inline in the API rather than via the worker
   queue (fine at current scale; dispatch scaffolding exists)
5. **Agent cost budgets** — estimated from listed prices; no hard provider-side cap
6. **Deployment** — render.yaml is complete but not yet provisioned; CI is ready
   and gates every push once the repo is on GitHub

## Risks

- Supabase service-role key must stay server-side (enforced by .env usage)
- Embeddings require OPENAI_API_KEY; without it, keyword search still works
- OCR quality on damaged documents depends on tesseract; confidence shown per page
- Mock LLM provider clearly labels unconfigured state rather than faking results

### CI/CD + Browser E2E + Voice Providers + Billing (Phases 16–20, final)

**GitHub Actions** (`.github/workflows/ci.yml`) — three jobs on every push/PR:
backend (compileall + 67 pytest tests), frontend (tsc + production build),
and Playwright E2E (Chromium, trace artifacts uploaded on failure).

**Playwright browser E2E** (10 tests, ~54s) — real Next.js production build
(`npm run build && npm run start` as the Playwright webServer; dev-mode
on-demand compilation exceeded test timeouts) in Chromium against a
page-route mock layer (`frontend/e2e/mocks.ts`): Supabase auth token/user,
PostgREST (memberships/profiles/cases/documents/jobs), and the FastAPI
surface incl. an SSE stream — seeded via the `sb-*-auth-token` cookie.
Journey coverage: landing → login (incl. label-associated inputs — fixed a
real a11y gap the tests caught) → dashboard empty state → create property
case → case home stats → upload deed → COMPLETED + OCR stats → risks page
with evidence + recommended action → cited Q&A → sidebar module visibility.
Zero network: the fake hosts (`e2efake.supabase.co`, `localhost:8000`) are
intercepted at the browser network layer.

**Provider STT/TTS** — `POST /voice/transcribe` (multipart audio → OpenAI
Whisper via `app/ai/voice_providers.py`; honest 503 "Not configured"
without keys) and `POST /voice/speak` (text → TTS audio). VoicePanel now
detects Web Speech support and falls back to MediaRecorder capture +
server transcription for Safari/Firefox, with browser/server TTS modes.

**Billing architecture** (no fake transactions) — migration 012
(subscriptions, usage counters, invoices), usage metering hooked into real
events (document pages, AI runs, voice), plan limits with soft enforcement,
Razorpay/Stripe adapters activated only when keys are configured,
`/billing/{checkout,plan}` endpoints, and a Settings plan & usage card
with progress bars. All unit-tested (webhook signature verification,
limit arithmetic) in `tests/test_billing_voice.py`.

## Recommended Next Order

The platform is feature-complete through Phase 20. Remaining work is
operational, not functional:

1. Provision Supabase + Render from `render.yaml`, apply migrations
   001–012, set env vars from `.env.example`, promote your first platform
   admin — then push to GitHub; CI gates every change from there.
2. Load/tune workers (Celery concurrency, OCR queue depth) once real
   document volumes are known.
3. Razorpay/Stripe go-live when the payment provider is chosen (adapters
   are ready; only keys + webhook URLs remain).
