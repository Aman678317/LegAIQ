# Project: LegAIQ / Jurisiva AI Comprehensive Production Hardening

## Architecture
- **Frontend**: Next.js 16.3.1 (App Router), React 19.2.8, Tailwind CSS v4, Zustand 5, Supabase SSR client, Vitest 4 test harness.
- **Backend**: FastAPI (Python 3.11+), Pydantic v2, unified AI `ModelRouter` (Rajora, Nvidia, Ollama, OpenAI, Anthropic, Mock), Celery / sync worker, LangGraph multi-agent DAG engine, hermetic Pytest test harness (`FakeSupabase`, `FakeOCRProvider`).
- **Database & Storage**: Supabase PostgreSQL migrations (001–015), `pgvector` (1536-dim IVFFlat + GIN FTS indexes), PostgreSQL RPCs, multi-tenant RLS with `WITH CHECK` integrity.
- **Security & Compliance**: Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 certificates, Verhoeff-verified Indian PII redaction (15+ identifiers), dual-layer SSRF protection with DNS rebinding defense, timing-safe auth via `hmac.compare_digest`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Multi-Tenant Org & Auth | Supabase Auth + RLS policies isolating by `organization_id` & `auth.uid()` | M1, M3 | survey |
| 2 | Case Management & Matter Workspace | Dynamic case routing, metadata, state management, search | M1, M2 | survey |
| 3 | Document Ingestion & Storage | Multi-format upload, deduplication, storage bucket isolation | M1, M2 | survey |
| 4 | Indic & Multi-Language OCR | 13 Indian languages, dual-pass OCR, CLAHE/deskew restoration | M1, M2 | survey |
| 5 | Semantic & Hybrid Search | 1536-dim pgvector cosine similarity + GIN full-text search ts_rank | M1, M4 | survey |
| 6 | Interactive Chat & Legal Assistant | Ask/Analyze/Draft modes, citations grounded in uploaded documents | M1, M2 | survey |
| 7 | Document Comparison & Redlining | Direct side-by-side comparison, structural diffing | M1, M2 | survey |
| 8 | Spreadsheet Review Tables | Dynamic columns, cell editing, confidence chips, CSV/JSON export | M1, M2 | survey |
| 9 | Clause Extraction & Library | 29+ legal clause extraction, risk assessment, standard clause repo | M1, M2 | survey |
| 10 | Contract Playbook Evaluation | Deviation scoring, unacceptable terms flag, redline suggestions | M1, M2 | survey |
| 11 | Multi-Agent Orchestration | DAG execution, cycle detection, topological sorting, state persistence | M1, M4 | survey |
| 12 | Specialist Legal Agents | 6 First-Class Agents (Due Diligence, Title Examiner, Risk Auditor, Litigation Strategist, Contract Reviewer, BSA Compliance) | M1, M4 | survey |
| 13 | Rajora LLM Private Engine | Self-hosted zero-cost LLM inference, failover, timeout, internal auth | M1, M4 | survey |
| 14 | Multi-Provider AI Routing | Nvidia NIM, Ollama local, OpenAI, Anthropic, deterministic Mock | M1, M4 | survey |
| 15 | BSA 2023 Evidence Certification | Section 63 electronic evidence certificate with SHA-256 tamper-evident sealing | M1, M3 | survey |
| 16 | Property Title Due Diligence | 13–30 year chain analysis, mutation gap detection, encumbrance search | M1, M4 | survey |
| 17 | Legal Risk Categorization | 9-category risk taxonomy, severity scoring, mitigation recommendations | M1, M4 | survey |
| 18 | Litigation Strategy & Limitation | CPC/BNS causes of action, limitation period calculations | M1, M4 | survey |
| 19 | External Shared Spaces | Client collaboration rooms, passcode protection, expiration, watermarking | M1, M3 | survey |
| 20 | Single Sign-On (SSO) | SAML/OIDC configuration, admin-only access control | M1, M3 | survey |
| 21 | Indian PII Redaction Engine | 15+ Indian identifiers, Verhoeff Aadhaar validation, 5 redaction strategies | M1, M3 | survey |
| 22 | SSRF Protection | DNS rebinding prevention, private IP / cloud metadata blocking | M1, M3 | survey |
| 23 | Voice Agent & Audio Intake | Indic audio intake, transcription pipeline | M1, M2 | survey |
| 24 | Timeline & Chronology Builder | Interactive event timeline extraction from case records | M1, M2 | survey |
| 25 | Legal Research & Citations | Indian case law, statutes, acts citation verification | M1, M4 | survey |
| 26 | Analytics & Audit Trail | Usage telemetry, token accounting, security audit logs | M1, M3 | survey |
| 27 | Background Task Queue | Celery / Redis background worker, synchronous test runner fallback | M1, M4 | survey |
| 28 | Statutory Export Engine | PDF, DOCX, CSV, Excel reports | M1, M2 | survey |
| 29 | PWA & Offline Database | IndexedDB offline cache, Service Worker | M2, M4 | survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Backend Hardening & API Hermeticity | Fix duplicate router mount in `main.py`, update `conftest.py` `PATCH_TARGETS`, clean unused backend dependencies | none | DONE |
| 2 | Frontend Dependency & Type Verification | Clean unused frontend dependencies, verify zero type errors, verify all 5 Vitest suites pass | none | DONE |
| 3 | Security, RLS & Secret Guardrail Hardening | Verify zero committed secrets, validate multi-tenant RLS isolation across 001-015, validate SSRF, PII, BSA 2023 | M1 | DONE |
| 4 | Final E2E Suite, Adversarial Testing & Forensic Audit | Run full 550+ backend pytest suite, all Vitest suites, challenger adversarial testing, and forensic integrity audit | M1, M2, M3 | DONE |

## Interface Contracts
### Frontend ↔ Backend API
- Base URL: `/api/v1` (with `/api` compatibility for SSR/health proxies)
- Authentication: Bearer JWT token in `Authorization` header
- Content Type: `application/json` (or `multipart/form-data` for uploads)
- Error Response Format: `{"detail": str, "error_code": Optional[str], "status_code": int}`

### Backend ↔ Supabase Database
- PostgreSQL with `pgvector` extension
- Authentication & Auth UID: `auth.uid()` via JWT claims
- Tenant Isolation: Scoped by `organization_id` (`is_org_member`) or `case_id` (`is_case_member`)

### Backend ↔ AI Providers
- `BaseLLMProvider.generate(prompt, options) -> LLMResponse`
- Rajora Provider: `http://localhost:8000/generate` (or configured host), zero cost invariant
- Fallback: Deterministic Mock provider when offline/testing

## Code Layout
- `backend/app/api/`: 28 FastAPI routers
- `backend/app/ai/`: ModelRouter, Providers (Rajora, Nvidia, Ollama, OpenAI, Anthropic, Mock), Multi-Agent Orchestrator, Specialist Agents
- `backend/app/security/`: Auth, PII redaction, SSRF filtering, Permissions
- `backend/app/services/`: OCR, Ingestion, Documents, Search, Export, Billing
- `backend/tests/`: 40 pytest test files, hermetic test harness `conftest.py`
- `frontend/app/`: Next.js App Router pages and API routes
- `frontend/components/`: Reusable UI components and modals
- `frontend/lib/`: API client, Rajora utilities, stores, Vitest tests (`rajora.test.ts`, `tier_comprehensive.test.ts`, `mockStore.test.ts`, `utils.test.ts`, `m1_m2_features.test.ts`)
- `supabase/migrations/`: Migrations `001_...` through `015_...`
