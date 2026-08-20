# Architecture & Test Infrastructure Comprehensive Analysis Report

**Platform:** LegAIQ / Jurisiva AI (India-First Legal Intelligence Platform)  
**Date:** 2026-08-20  
**Author:** teamwork_preview_explorer (Architecture & Test Infrastructure)  
**Integrity Mode:** Development  

---

## 1. Executive Summary & System Overview

LegAIQ / Jurisiva AI is an evidence-first, multi-tenant legal artificial intelligence platform architected specifically for Indian jurisprudence and property law, designed to achieve competitive parity with global platforms (such as Harvey AI) while establishing unassailable domain moats across India's 28+ state land registries, 12+ Indic languages, 15+ regional deed formats, and the Bharatiya Sakshya Adhiniyam (BSA) 2023 evidence framework.

### Architecture Summary

```
                       ┌──────────────────────────────────────────────────────────┐
                       │                     Frontend Client                      │
                       │           (Next.js 16 + React 19 + Tailwind v4)          │
                       │  - Workspace / Dashboard / Case Hub                      │
                       │  - Unified Assistant (Ask / Analyze / Draft)             │
                       │  - Review Tables Workspace (Spreadsheet Extraction)      │
                       │  - Contract Intelligence & Redline Diff Viewer           │
                       │  - Visual Workflow Builder & Agent Telemetry             │
                       │  - PWA Offline Engine (IndexedDB + Service Worker)       │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │ REST / SSE / WebSockets
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │                    FastAPI Gateway                       │
                       │               (Python 3.12+ / Uvicorn)                   │
                       │  - Auth & RBAC Middleware (Supabase JWT + SSO SAML/OIDC) │
                       │  - Rate Limiter (SlowAPI) + Audit Logger                 │
                       │  - SSRF & Prompt Injection Defense + AI Kill Switch      │
                       │  - 20+ API Routers (Cases, Vault, Review, Agents, etc.)  │
                       └────────────┬─────────────────────────────┬───────────────┘
                                    │                             │
                     Async Tasks    │                             │ Data Persistence
                     (Redis Queue)  ▼                             ▼
       ┌────────────────────────────────────────┐  ┌───────────────────────────────┐
       │             Celery Workers             │  │       PostgreSQL 15 (Supabase)│
       │  - Dual-Pass Indic OCR (PaddleOCR/Tess)│  │  - Row-Level Security (RLS)   │
       │  - Historical Deed Preprocessing       │  │  - pgvector Document Chunks  │
       │  - Multi-Agent Orchestrator (LangGraph)│  │  - Ownership Graph (Nodes/Edge)│
       │  - Contract Analyzer & Redline Diff    │  │  - Audit Logs & Agent Runs    │
       │  - PII Detection & Redaction (Presidio)│  │  - Review Tables & Playbooks  │
       │  - PDF/DOCX Report Exporters           │  │  - S3 / MinIO Document Storage│
       └────────────────────────────────────────┘  └───────────────────────────────┘
```

---

## 2. Root Structure, Build Systems & Configuration Analysis

### 2.1 Workspace Root Structure
```
c:\Users\acer\OneDrive\inga legal\
├── .agents/                      # Teamwork agent metadata, dispatch, and reports
├── .env.example / .env           # Environment credentials and service configurations
├── docker-compose.yml            # Local orchestration (PostgreSQL, Studio, Auth, Storage, MinIO, Redis, Backend, Worker, Frontend)
├── render.yaml                   # Production deployment specification (API, Worker, Beat, Redis, Frontend)
├── README.md / GAP_ANALYSIS...   # Architectural and competitive gap documentation
├── backend/                      # FastAPI service and Celery worker application
│   ├── app/                      # Main application package
│   │   ├── ai/                   # AI logic: agents, indic_ocr, contract_intelligence, bharatiya_sakshya, state_portals, etc.
│   │   ├── api/                  # FastAPI routers (20 mounted modules in main.py)
│   │   ├── security/             # Auth, SSO (SAML/OIDC), PII, SSRF, audit logging
│   │   ├── services/             # Domain business services (billing, etc.)
│   │   ├── workers/              # Celery app, tasks, dispatcher
│   │   ├── config.py             # Pydantic BaseSettings configuration
│   │   └── main.py               # FastAPI entry point, CORS, and router assembly
│   ├── tests/                    # Pytest suite with in-memory test doubles
│   │   ├── fakes/                # FakeSupabase in-memory database & storage engine
│   │   ├── conftest.py           # Pytest fixtures and mock OCR providers
│   │   └── test_*.py             # 16 test modules with 250+ assertions
│   ├── Dockerfile                # Backend container image build
│   ├── pytest.ini                # Pytest configuration (asyncio_mode=auto, testpaths=tests)
│   ├── requirements.txt          # Production dependencies
│   └── requirements-dev.txt      # Development & testing dependencies
├── frontend/                     # Next.js 16 React 19 Frontend application
│   ├── app/                      # App router directory
│   │   ├── (app)/                # Authenticated application shell
│   │   │   ├── cases/[caseId]/   # Case workspace submodules (documents, risks, ownership, etc.)
│   │   │   ├── dashboard/        # Case listing and creation
│   │   │   ├── chat/             # AI assistant and Ollama workspace
│   │   │   ├── admin/            # Admin console (ai-usage, agent-runs, audit, jobs, orgs, users)
│   │   │   └── settings/         # Organization settings
│   │   └── layout.tsx / page.tsx # Root landing and authentication routes
│   ├── components/               # Reusable UI component library (Tailwind v4)
│   ├── lib/                      # Client SDKs, API client (api.ts), mockStore.ts, universalAi.ts, ollama.ts, pwa.ts
│   ├── e2e/                      # Playwright end-to-end browser test suite (mocks.ts, case-journey.spec.ts, auth.spec.ts)
│   ├── package.json              # Next.js, React 19, Lucide, Tailwind, Playwright, Vitest
│   ├── playwright.config.ts      # Playwright browser testing configuration
│   ├── vitest.config.mjs         # Vitest unit test configuration
│   └── vitest.setup.ts           # Vitest DOM matchers and mocks setup
├── shared/                       # TypeScript schemas and definitions (types.ts)
└── supabase/                     # SQL migrations (001 through 012 + RLS policies + RPCs)
```

### 2.2 Build and Configuration Analysis

| Component | Configuration File | Key Technologies & Specifications | Health / Compliance |
|-----------|--------------------|-----------------------------------|----------------------|
| **Backend Environment** | `backend/requirements.txt`, `backend/requirements-dev.txt` | FastAPI 0.115, Pydantic 2.9, SQLAlchemy 2.0, Celery 5.4, Redis 5.0.8, PyTesseract 0.3.13, OpenCV 4.10, Presidio 2.2, Spacy 3.7, Pytest 8.3, Pytest-Asyncio 0.24 | Up to date, robust dependency pin |
| **Backend Test Runner** | `backend/pytest.ini` | `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function`, filter `DeprecationWarning` | Configured for clean async test runs |
| **Frontend Environment** | `frontend/package.json` | Next.js 16.3.1, React 19.2.8, Tailwind CSS v4, Zustand 5.0, Lucide React 1.31, date-fns 4.4, Vitest 4.1, Playwright 1.62, Happy-DOM 20.11 | Modern Next.js 16 stack |
| **Frontend Unit Test Runner** | `frontend/vitest.config.mjs` | `environment: "happy-dom"`, `setupFiles: ["./vitest.setup.ts"]`, Path aliases configured | Fast in-memory component & unit tests |
| **Frontend E2E Test Runner** | `frontend/playwright.config.ts` | Chromium desktop, fully mocked Supabase + FastAPI network layer in `e2e/mocks.ts`, WebServer runs production build | Deterministic, hermetic browser tests |
| **Containerization** | `docker-compose.yml`, `render.yaml` | Supabase Postgres (54322), Supabase Studio (54323), GoTrue Auth (54324), Storage/MinIO (54325/54326), Redis (6379), FastAPI Backend (8000), Celery Worker, Next.js Frontend (3000) | Full-stack local dev & cloud spec |
| **Database Migrations** | `supabase/migrations/001..012` | 12 sequential SQL migrations covering Multi-tenancy, Cases/Properties, Document Storage, OCR & Extraction, Ownership Graphs, Research/Drafts, RLS, RPCs, Agents/Voice, Admin, Billing | Strict RLS & tenant isolation |

---

## 3. Test Infrastructure Assessment & Verification

### 3.1 Test Infrastructure Architecture

```
                                  TEST INFRASTRUCTURE
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
  Backend Test Suite (Pytest)                                Frontend Test Suite (Vitest & Playwright)
  ├── In-Memory Doubles:                                     ├── Unit / Integration (Vitest):
  │   ├── FakeSupabase (TableStore, Filters, RPC, Storage)   │   ├── utils.test.ts (formatting, state, locale)
  │   └── FakeOCRProvider (Multi-page deterministic deeds)   │   └── mockStore.test.ts (localStorage store)
  ├── Hermetic Zero-Network Execution:                       └── Browser E2E (Playwright):
  │   ├── test_e2e_pipeline.py (Upload → OCR → Risks → PDF)  │   ├── e2e/mocks.ts (Network interception)
  │   ├── test_api.py (Auth, Cases, Admin RBAC)              │   ├── e2e/auth.spec.ts (Login/session cookies)
  │   ├── test_agent_orchestration.py (LangGraph workflows)  │   └── e2e/case-journey.spec.ts (Case lifecycle)
  │   ├── test_bharatiya_sakshya.py (BSA 2023 engine)        │
  │   ├── test_contract_intelligence.py (Clauses & risks)    │
  │   ├── test_indic_ocr.py (13 Indic languages & layout)    │
  │   ├── test_land_intelligence.py (State portals & graph)  │
  │   ├── test_pii.py (Aadhaar, PAN, GST redaction)          │
  │   ├── test_sso.py (SAML 2.0 & OIDC PKCE)                 │
  │   ├── test_title_search_report_v2.py (13 sections)       │
  │   ├── test_billing_voice.py (Usage budgets & voice)      │
  │   └── test_ssrf.py (SSRF protection & safe fetches)      │
```

### 3.2 Inventory of Test Suites

| Suite Name | File Location | Test Focus | Total Tests / Assertions |
|------------|---------------|------------|--------------------------|
| **Pipeline E2E** | `backend/tests/test_e2e_pipeline.py` | Case creation, deed upload, dual-doc OCR, conflict detection, risk generation, ReportAgent execution, PDF & DOCX binary export, legal notice drafting, grounded Q&A | 2 full E2E scenarios, 40+ assertions |
| **API & RBAC** | `backend/tests/test_api.py` | Healthcheck, JWT enforcement, Org membership, Case CRUD, Admin overview, platform admin permission escalation prevention, last-owner role guard | 12 test functions |
| **Agent Orchestrator** | `backend/tests/test_agent_orchestration.py` | LangGraph state graph, topological sorting, dependency checks, condition branch evaluation, workflow persistence, AI Kill Switch | 24 test functions |
| **Agent Core & Budgets**| `backend/tests/test_agents.py` | LLM call limits, token caps, USD cost bounds, iteration limits, tool permission guards, schema validation | 10 test functions |
| **BSA 2023 Admissibility**| `backend/tests/test_bharatiya_sakshya.py`| Sections 57 (Primary), 60 (Secondary), 63 (Electronic certificate hash), 94 (30-year Ancient doc presumption), 95-97 (Electronic agreement/certified copy presumptions), DPDP compliance | 28 test functions |
| **Contract Intelligence** | `backend/tests/test_contract_intelligence.py`| 29 clause pattern extractions, party parsing, critical/high risk keyword scoring, obligation timeline parsing, Indian legal compliance checks, redline diff | 20 test functions |
| **Indic OCR Engine** | `backend/tests/test_indic_ocr.py` | 13 language configurations, layout segmentation, fallback hierarchy, script identification | 14 test functions |
| **Land Intelligence** | `backend/tests/test_land_intelligence.py` | Connectors for Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR, rate limiting, mock record generation | 10 test functions |
| **Title Search Report v2**| `backend/tests/test_title_search_report_v2.py`| 13 mandatory legal sections, flow of title chain, legal search certificate, schedule formatting | 18 test functions |
| **PII & Data Protection** | `backend/tests/test_pii.py` | Aadhaar (Verhoeff check), PAN, GST, IFSC, Indian phone/email regex, Presidio integration, masking strategies (MASK, REPLACE, HASH, PSEUDONYMIZE) | 26 test functions |
| **SSO Authentication** | `backend/tests/test_sso.py` | SAML 2.0 AuthNRequest, signed response validation, OIDC PKCE flow, domain-based routing | 16 test functions |
| **Voice & Billing** | `backend/tests/test_billing_voice.py` | Voice session lifecycle, STT/TTS fallback providers, token & cost billing attribution | 8 test functions |
| **SSRF Security** | `backend/tests/test_ssrf.py` | Private IP blocking (127.0.0.1, 10.0.0.0/8, 169.254.169.254 AWS metadata, 192.168.0.0/16) | 6 test functions |
| **Frontend Unit** | `frontend/lib/*.test.ts` | `mockStore.test.ts` (localStorage state store), `utils.test.ts` (currency, date, locale formatting, Indian states) | 14 test assertions |
| **Frontend E2E** | `frontend/e2e/*.spec.ts` | Playwright tests for Dashboard empty state, Case creation journey, Document upload & OCR badge display, Risk list with cited evidence, Grounded Q&A with document links | 10 test specs |

---

## 4. End-to-End Data Flow & Interface Contracts (R1 through R7)

```
                                      R1–R7 SYSTEM CONTRACT MAP
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                                  │
 │  R1: Assistant Workspace  ◄──►  R2: Secure Matter Vault  ◄──►  R3: Spreadsheet Review Tables    │
 │  (Ask/Analyze/Draft SSE)        (Dual-Pass Indic OCR)          (Cell-Level Evidence Linking)     │
 │            ▲                               ▲                               ▲                     │
 │            │                               │                               │                     │
 │            ▼                               ▼                               ▼                     │
 │  R4: Multi-Agent Engine   ◄──►  R5: Contract Intelligence◄──►  R6: Shared Spaces & Security      │
 │  (LangGraph Orchestration)      (29 Clauses & Playbooks)       (RBAC, PII Redaction & Analytics) │
 │                                            ▲                                                     │
 │                                            │                                                     │
 │                                            ▼                                                     │
 │                             R7: India-First Property Moat                                        │
 │                        (5 Portals, 30-Yr Graph, BSA 2023 Certs)                                  │
 │                                                                                                  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Detailed Contract Specifications

#### R1: Assistant & Chat Workspace Contract
- **Endpoint**: `POST /api/v1/cases/{case_id}/questions` & `GET /api/v1/cases/{case_id}/assistant/stream`
- **Request Interface**:
```typescript
export interface AssistantChatRequest {
  message: string;
  mode: "ask" | "analyze" | "draft";
  model: "llama3-70b" | "claude-3-5-sonnet" | "gpt-4o" | "deepseek-r1" | "mistral";
  india_context: {
    state?: string;
    statutory_framework: "BSA_2023" | "IEA_1872";
    include_revenue_glossary: boolean;
  };
  context_document_ids?: string[];
}
```
- **SSE Stream Protocol**:
  - `event: delta` → `{"delta": "According to Section 54 of the Transfer of Property Act..."}`
  - `event: citation` → `{"id": "cit_1", "document_id": "doc_123", "document_name": "sale_deed.pdf", "page_number": 3, "source_text": "Venkatarama Reddy sells...", "confidence": 0.94}`
  - `event: done` → `{"total_tokens": 420, "model": "gpt-4o", "latency_ms": 612}`

#### R2: Secure Matter Vault & Document Intelligence Contract
- **Endpoint**: `POST /api/v1/cases/{case_id}/vault/upload`
- **Payload**: Multipart file stream + classification & OCR options.
- **Worker Job Contract**:
```json
{
  "job_type": "dual_pass_ocr_extraction",
  "document_id": "doc-uuid",
  "case_id": "case-uuid",
  "pipeline_steps": [
    "historical_preprocessing",
    "paddleocr_indic_pass",
    "tesseract_latin_pass",
    "document_classification",
    "entity_extraction_regex_llm",
    "pgvector_chunk_embeddings"
  ]
}
```

#### R3: Spreadsheet-Style Review Tables Contract
- **Endpoints**:
  - `GET /api/v1/cases/{case_id}/review-tables`
  - `POST /api/v1/cases/{case_id}/review-tables`
  - `POST /api/v1/cases/{case_id}/review-tables/{table_id}/columns`
  - `POST /api/v1/cases/{case_id}/review-tables/{table_id}/extract`
  - `GET /api/v1/cases/{case_id}/review-tables/{table_id}/export?format=xlsx|csv`
- **Data Model**:
```typescript
export interface ReviewTable {
  id: string;
  case_id: string;
  name: string;
  columns: ReviewColumn[];
  rows: ReviewRow[];
}

export interface ReviewColumn {
  id: string;
  key: string;
  label: string;
  prompt_instructions: string;
  expected_type: "text" | "currency" | "date" | "survey_no" | "boolean" | "entity";
}

export interface ReviewCell {
  column_id: string;
  document_id: string;
  value: string | number | boolean | null;
  confidence: number;
  evidence: {
    document_id: string;
    document_name: string;
    page_number: number;
    source_text: string;
    bounding_box?: { x: number; y: number; width: number; height: number };
  };
  status: "PENDING" | "EXTRACTING" | "COMPLETED" | "FAILED";
  manually_edited: boolean;
}
```

#### R4: Multi-Agent Orchestration & Workflow Builder Contract
- **Endpoints**:
  - `GET /api/v1/workflows/templates`
  - `POST /api/v1/cases/{case_id}/workflows/run`
  - `GET /api/v1/workflows/runs/{run_id}/telemetry`
- **Workflow State Machine Contract**:
```json
{
  "workflow_id": "wf-custom-001",
  "name": "Commercial Lease Audit Pipeline",
  "nodes": [
    { "id": "ocr_vault", "agent": "VaultAgent", "params": {} },
    { "id": "clause_parse", "agent": "ContractReviewAgent", "depends_on": ["ocr_vault"] },
    { "id": "risk_audit", "agent": "RiskAgent", "depends_on": ["clause_parse"] },
    { "id": "citation_check", "agent": "CitationAuditorAgent", "depends_on": ["risk_audit"] },
    { "id": "executive_report", "agent": "ReportAgent", "depends_on": ["citation_check"] }
  ]
}
```

#### R5: Contract Intelligence, Clause Library & Playbooks Contract
- **Endpoints**:
  - `POST /api/v1/cases/{case_id}/contracts/analyze`
  - `POST /api/v1/cases/{case_id}/contracts/playbook-eval`
  - `POST /api/v1/cases/{case_id}/contracts/redline`
  - `GET /api/v1/clause-library`
  - `POST /api/v1/clause-library`
- **Playbook Compliance Schema**:
```typescript
export interface PlaybookEvaluationResult {
  clause_id: string;
  clause_type: ClauseType;
  extracted_text: string;
  compliance_grade: "STANDARD" | "ACCEPTABLE_FALLBACK" | "UNACCEPTABLE_DEVIATION" | "MISSING_MANDATORY";
  matched_rule_id: string;
  risk_score_delta: number;
  suggested_redline: string;
  rationale: string;
}
```

#### R6: Shared Spaces, Command Center & Enterprise Controls Contract
- **Endpoints**:
  - `POST /api/v1/cases/{case_id}/shared-spaces`
  - `POST /api/v1/cases/{case_id}/shared-spaces/{space_id}/links`
  - `GET /api/v1/analytics/command-center`
  - `POST /api/v1/pii/redact`
- **Security Policy**:
  - Encrypted temporary tokens (expires in 24h/7d).
  - Dynamic canvas watermark overlay: `CONFIDENTIAL - [Law Firm Name] - [User Email] - [Timestamp]`.
  - Indian PII Redaction Engine: Regex + Presidio Recognizers for 12-digit Aadhaar, 10-char PAN, GSTIN, IFSC, CIN, and DIN.

#### R7: India-First Property & Legal Moat Contract
- **Endpoints**:
  - `POST /api/v1/land-portals/query`
  - `GET /api/v1/cases/{case_id}/ownership-chain/graph`
  - `POST /api/v1/cases/{case_id}/documents/{doc_id}/bsa-certificate`
- **BSA 2023 Section 63 Digital Certificate Schema**:
```json
{
  "certificate_version": "BSA-2023-Sec63-v1",
  "document_id": "doc-8912",
  "document_name": "sale_deed_1987.pdf",
  "cryptographic_hash": {
    "algorithm": "SHA-256",
    "hash_value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "creation_timestamp_utc": "2026-08-20T02:18:39Z",
  "system_declaration": "Generated in accordance with Section 63 of Bharatiya Sakshya Adhiniyam, 2023 certifying device integrity, hash verification, and untampered chain of custody.",
  "admissibility_presumption": "Section 94 (Ancient Document >30 years) & Section 97 (Certified Copy)"
}
```

---

## 5. Test Infrastructure & Mock Dataset Gaps

### 5.1 Identified Testing Gaps

| Area | Current Baseline | Gap / Deficiency | Required Remedy |
|------|------------------|-------------------|-----------------|
| **Indic OCR Mock Datasets** | Single synthetic Karnataka deed snippet in `conftest.py` | Lacks test fixtures for complex Indic scripts (Devanagari 7/12, Telugu 1B, Tamil Patta, Gujarati VF-712) with realistic historical degradation | Create `backend/tests/fixtures/indic_ocr/` with multi-lingual synthetic test fixtures for 12+ languages |
| **Review Table Test Harness** | None (new requirement) | No automated test coverage for Review Tables (column creation, async extraction worker, evidence cell binding, CSV/XLSX export) | Add `backend/tests/test_review_tables.py` and frontend Vitest component tests |
| **Contract Playbooks Dataset** | Single sample contract in `test_contract_intelligence.py` | Lacks test cases for playbook rule matching across 29+ clause types (e.g. indemnity cap breach, non-compete overbreadth, missing arbitration) | Add `backend/tests/fixtures/contracts/` covering standard, fallback, and unacceptable clause variations |
| **Workflow Builder State Machine** | Tested in backend (`test_agent_orchestration.py`), missing UI test harness | No Playwright or Vitest specs testing visual workflow builder drag-and-drop, step connection, live execution status rendering | Add `frontend/e2e/workflow-builder.spec.ts` with node graph interaction mocks |
| **Shared Spaces & Watermarking** | SSO & PII tested; Shared spaces not fully isolated in E2E | No browser test verifying expiring link generation, viewer watermarking, and download restrictions | Add E2E tests in `frontend/e2e/shared-spaces.spec.ts` |
| **Unified Test Runner** | Separate pytest / vitest / playwright commands | No unified script or Makefile command to run backend + frontend unit + E2E validation in one shot | Provide root package script / PowerShell validation runner |

---

## 6. Milestone Decomposition & Implementation Roadmap

```
                                  FOUR-MILESTONE EXECUTION ROADMAP
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                                  │
 │  MILESTONE 1: Unified Assistant Workspace & Dual-Pass Indic Vault (R1 + R2)                      │
 │  - Unified 3-Mode Assistant (Ask/Analyze/Draft) with SSE streaming, model selector, citations    │
 │  - Matter Vault with bulk upload (PDF/DOCX/XLSX/Images) & dual-pass Indic OCR (12+ languages)    │
 │  - Automated document classifier (15+ Indian land record types) & historical deed preprocessor   │
 │                                                                                                  │
 │  MILESTONE 2: Spreadsheet Review Tables & Contract Intelligence Playbooks (R3 + R5)              │
 │  - Interactive Review Table workspace with custom prompt columns & cell-level evidence linking   │
 │  - Contract Intelligence with 29+ clause types, 0-100 risk scoring & side-by-side redline diff  │
 │  - Clause Library with fallback language guidelines & Playbook deviation detection               │
 │                                                                                                  │
 │  MILESTONE 3: Visual Workflow Builder & Enterprise Shared Spaces / Analytics (R4 + R6)           │
 │  - Agent orchestration with 5 specialist agents (Research, Contract, DD, Title, Citation Auditor)│
 │  - No-code visual Workflow Builder with live step execution telemetry & run logs                 │
 │  - Matter Shared Spaces with granular RBAC, watermarking, expiring links & Presidio Indian PII   │
 │  - Command Center Analytics (AI ROI, token usage, case velocity, team productivity)             │
 │                                                                                                  │
 │  MILESTONE 4: India Property Title Graph, BSA 2023 Certification & E2E Validation (R7 + Qual)   │
 │  - 5+ State Land Portal connectors (Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR)            │
 │  - 13–30 year property ownership timeline graph generator with temporal visualization           │
 │  - BSA 2023 Section 63 electronic record certificates & Indian Kanoon legal research            │
 │  - Full regression pass: backend pytest, frontend vitest, Playwright browser E2E                │
 │                                                                                                  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Milestone Breakdown Details

#### Milestone 1: Unified Assistant Workspace & Dual-Pass Indic Vault (R1 + R2)
- **Deliverables**:
  1. Frontend: Unified Assistant component (`components/assistant/workspace.tsx`) supporting Ask, Analyze, and Draft modes with model selector (Ollama 70B, Claude 3.5, GPT-4o, DeepSeek R1), India Context toggle, and clickable citation badge renderer.
  2. Backend: SSE streaming endpoint `/api/v1/cases/{case_id}/assistant/stream` emitting text deltas and structured citation metadata.
  3. Backend: Enhanced Dual-Pass OCR pipeline combining OpenCV historical preprocessing, PaddleOCR for 12+ Indic scripts, and Tesseract.
  4. Backend: 15+ deed format classification taxonomy and regex/LLM entity extraction.
  5. Vault UI: Bulk document upload queue with format validation (PDF, DOCX, XLSX, images) and live processing telemetry.
- **Verification**: Pytest unit tests for dual-pass OCR & streaming endpoints + Vitest component tests for Assistant and Vault.

#### Milestone 2: Spreadsheet Review Tables & Contract Intelligence Playbooks (R3 + R5)
- **Deliverables**:
  1. Backend: Review Tables database schema (`review_tables`, `review_columns`, `review_cells`) and CRUD/extraction APIs.
  2. Frontend: Interactive Review Table workspace (`/cases/[caseId]/review-table`) with dynamic column prompt definitions, cell confidence indicators, clickable evidence popovers, and CSV/XLSX export.
  3. Backend: Contract Intelligence Playbook deviation engine and Clause Library management endpoints.
  4. Frontend: Contract Intelligence & Redline Diff viewer (`/cases/[caseId]/contracts`) showing side-by-side insertions/deletions, risk score breakdown, and clause library integration.
- **Verification**: Pytest suite for review extraction & contract playbooks + Playwright test for review table interactions.

#### Milestone 3: Visual Workflow Builder & Enterprise Shared Spaces / Analytics (R4 + R6)
- **Deliverables**:
  1. Backend: LangGraph multi-agent orchestrator with 5 specialist agents (Legal Research, Contract Review, Due Diligence, Title Search, Citation Auditor).
  2. Frontend: Visual Workflow Builder canvas (`/cases/[caseId]/workflows` & `/admin/workflows`) with node connection, parameter editor, and live execution telemetry.
  3. Backend & Frontend: Matter Shared Spaces with collaborator permissions, expiring links, and dynamic PDF watermarking.
  4. Backend & Frontend: Command Center Analytics dashboards (`/admin/analytics`) for AI costs, token burn, and case velocity.
  5. Backend & Frontend: Indian PII auto-redaction modal with toggleable Aadhaar, PAN, GST, and IFSC masking.
- **Verification**: Pytest suite for multi-agent workflows, PII, and analytics + Playwright tests for Shared Spaces.

#### Milestone 4: India Property Title Graph, BSA 2023 Certification & E2E Validation (R7 + Quality)
- **Deliverables**:
  1. Backend & Frontend: 5 state land portal connectors (Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR) with UI search and live/mock record ingestion.
  2. Backend & Frontend: 13–30 year ownership timeline graph generator with temporal scrubber and defect flags.
  3. Backend: BSA 2023 Section 63 tamper-evident digital certificate generator (SHA-256 hash + custodian verification).
  4. Frontend: PWA offline service worker and sync queue verification.
  5. E2E Validation: Full test suite execution across backend (pytest) and frontend (vitest + Playwright) with zero regressions.
- **Verification**: Complete test pass on all backend and frontend suites.

---

## 7. Recommendations for Architecture & Test Setup

1. **Maintain Strict In-Memory Test Hermeticity**:
   All new backend features must extend `FakeSupabase` and provide deterministic fakes for external LLM / OCR / Land Portal calls. No test should ever make an external network request or require a live PostgreSQL instance to run.
2. **Unified Mock Network Layer for Playwright**:
   All new frontend features (Review Tables, Workflow Builder, Contract Redlining) must be added to `frontend/e2e/mocks.ts` so the full browser test suite continues running deterministically against `npm run build && npm run start`.
3. **Structured SSE Protocol for Assistant**:
   Adopt standard W3C Server-Sent Events with explicit event types (`delta`, `thought`, `citation`, `error`, `done`) to enable rich citation badge hydration in the Next.js client without blocking UI rendering.
4. **Resilient Data Contracts in `shared/types.ts`**:
   Maintain single-source-of-truth TypeScript definitions in `shared/types.ts` matching Pydantic schemas in `backend/app/models/` to prevent interface drift.
