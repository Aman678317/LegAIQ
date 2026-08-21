# Project: India Legal Intelligence OS (Jurisiva AI / LegAIQ)

## Architecture
The India Legal Intelligence OS is a production-grade, Harvey-class legal intelligence platform grounded in Indian statutes (BNS, BNSS, BSA 2023, CPC, Income Tax Act, RERA, Companies Act), land records (7/12, 8A, Ferfar, Property Cards, RTC, Patta Chitta), and court workflows.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Next.js 16 App Router UI                          │
│  (Chatbot, Matter Workspace, 3-Mode Legal Assistant, Review Tables,         │
│   Contract Playbooks, Property Due Diligence, Multi-Deed Diff, Exporters)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / SSE Streaming
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                             FastAPI API Gateway                             │
│  ├── Live Multi-Model Router (Groq Llama 3.3 70B, OpenAI, Anthropic, Ollama)│
│  ├── Matter-Centric Vault & Evidence Graph (LegalContext grounder)          │
│  ├── Indian Document Intelligence & OCR Engine (13 Indic Languages, CLAHE)  │
│  ├── Land Record & 13–30 Yr Title Reconstruction DAG (Cycle/Gap detection)  │
│  ├── BSA 2023 Section 63 Electronic Evidence Certificate (SHA-256 sealing)  │
│  ├── 6 Specialized Workflow Agents (Due Diligence, Title, Contract, etc.)   │
│  └── Security & DPDP Guardrails (Verhoeff PII, SSRF/DNS Rebinding, RLS)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Supabase PostgreSQL + pgvector + Auth                    │
│  (Cases, Documents, Chunks, Embeddings, Ownership Nodes/Edges, BSA Certs)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Groq LPU Llama 3.3 70B Gateway | First-class sub-600ms latency reasoning provider in backend `provider.py` & `config.py` | M1 | Survey & R1 |
| 2 | Multi-Model Dynamic Fallback | Seamless routing across Groq, OpenAI GPT-4o, Claude 3.5 Sonnet, Ollama | M1 | Survey & R1 |
| 3 | Real-Time SSE Token Streaming | Async generator token streaming for Ask, Analyze (FIRAC), Draft, Research modes | M1 | Survey & R1 |
| 4 | Elimination of Canned Fallbacks | Purge static canned answers and hardcoded mock templates repository-wide | M1 | Survey & R1 |
| 5 | Matter-Centric Vault Context | "One matter, one workspace, one evidence graph" persistent case memory | M2 | Survey & R2 |
| 6 | Interactive Citation Grounding | Interactive citation chips linking findings to `[Doc, Page, Source]` with modal preview | M2 | Survey & R2 |
| 7 | Hybrid Vector + Keyword RAG | pgvector cosine similarity + full-text search with `ts_rank` on `document_chunks` | M2 | Survey & R2 |
| 8 | Multi-Lingual Indic OCR (13 Lang) | OCR & VLM parsing for 13 Indian languages with deskewing, CLAHE, uncertainty tags | M3 | Survey & R3 |
| 9 | Indian Land Records Engine | Parsers for 7/12, 8A, Ferfar, Property Cards, CTS, RTC, Patta Chitta & Bigha normalization | M3 | Survey & R3 |
| 10 | 13–30 Year Title Reconstruction | Ownership chain DAG with circular conveyance DFS cycle detection & gap analysis | M3 | Survey & R3 |
| 11 | BSA 2023 Section 63 Certification | Electronic Evidence Certificates with SHA-256 tamper-evident sealing & presumptions | M3 | Survey & R3 |
| 12 | 6 Specialized Legal Agents | Due Diligence, Title Examiner, Contract Reviewer, Litigation Strategist, BSA, Research | M4 | Survey & R4 |
| 13 | Contract Playbook & 36 Clauses | 36 clause extraction, negotiation playbook deviation scoring, redline diff generation | M4 | Survey & R4 |
| 14 | Court-Ready Export Engine | Native Vector PDF, Word DOCX, and multi-sheet Excel (.xlsx) review tables | M4 | Survey & R4 |
| 15 | Multi-Tenant Supabase RLS | Organization-scoped and `is_case_member()` PostgreSQL RLS across migrations 001–015 | M5 | Survey & R5 |
| 16 | Verhoeff Indian PII Redaction | Mathematical checksum validation for Aadhaar + 15 Indian PII entities (5 strategies) | M5 | Survey & R5 |
| 17 | SSRF & DNS Rebinding Defense | Dual-layer IP validation and DNS resolution checks for outbound requests | M5 | Survey & R5 |
| 18 | Hermetic Backend & Frontend Tests | 100% passing test suites across Pytest (37+ test files) and Vitest (0 TS errors) | M5 | Survey & R5 |
| 19 | 100% E2E Test Suite Acceptance | Complete Tier 1-4 test pass and Tier 5 adversarial coverage hardening | M6 | Survey & Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Live Multi-Model AI Gateway & Streaming Engine | GroqProvider, real-time SSE token streaming for Ask/Analyze/Draft/Research, removal of canned fallbacks | None | DONE |
| M2 | Matter-Centric Vault & Evidence Workspace | Persistent matter memory, strict interactive citation grounding UI, hybrid RAG integration | M1 | DONE |
| M3 | Indian Document Intelligence & Property Title Engine | 13 Indic language OCR, historical restoration, land record parsers, 13-30 yr title DAG, BSA 2023 Sec 63 SHA-256 certs | M1 | DONE |
| M4 | Specialized Legal Workflow Agents & Litigation Suite | 6 workflow agents, 36 clause contract reviewer, playbooks, CPC litigation strategy, court-ready PDF/DOCX/XLSX export | M2, M3 | DONE |
| M5 | Security, DPDP Compliance & Production Hardening | Supabase RLS policies, Verhoeff Aadhaar PII redaction, SSRF defense, 0 TS errors, 100% test pass | M1, M2, M3, M4 | DONE |
| M6 | Final Acceptance: 100% E2E Pass & Adversarial Hardening | Pass 100% E2E test suite (Tiers 1-4) and Tier 5 adversarial coverage hardening | M1, M2, M3, M4, M5 | DONE |

## Interface Contracts

### AI Gateway Provider Contract (`backend/app/ai/provider.py`)
- `BaseLLMProvider.complete(prompt: str, system_prompt: str | None = None, **kwargs) -> LLMResponse`
- `BaseLLMProvider.stream_complete(prompt: str, system_prompt: str | None = None, **kwargs) -> AsyncIterator[str]`
- `ModelRouter.route(mode: str, query: str, model_preference: str | None = None) -> BaseLLMProvider`

### Matter-Centric Context Contract (`backend/app/schemas/case.py`)
- `LegalContext`: `{ case_id: UUID, client_name: str, jurisdiction: str, court: str, acts_applicable: list[str], document_ids: list[UUID], evidence_graph_id: UUID }`
- Grounding Citation: `{ document_id: UUID, document_name: str, page_number: int, source_passage: str, confidence: float, bounding_box: dict | None }`

### Indian Land Intelligence Contract (`backend/app/ai/land_intelligence.py`)
- `normalize_land_area(value: float, unit: str, state: str) -> float` (in sq meters)
- `reconstruct_title_chain(deeds: list[DeedRecord]) -> TitleChainDAG`
- `generate_bsa_certificate(case_id: UUID, document_id: UUID, operator_info: dict) -> BSACertificate` (with SHA-256 seal)

## Code Layout
- `backend/app/api/`: FastAPI route handlers (`analysis.py`, `cases.py`, `bsa.py`, `research.py`, `workflows.py`, `chat.py`, `review.py`, `contracts.py`)
- `backend/app/ai/`: Core AI & legal intelligence modules (`provider.py`, `indic_ocr.py`, `historical_ocr.py`, `land_intelligence.py`, `ownership_graph.py`, `bharatiya_sakshya.py`, `contract_intelligence.py`, `playbooks.py`, `title_search_report.py`, `review_tables.py`, `agents/`)
- `backend/app/security/`: Security & compliance (`pii.py`, `ssrf.py`, `auth.py`)
- `backend/tests/`: Pytest hermetic suites with `FakeSupabase` and `FakeOCRProvider` (38 test files, 400+ test cases)
- `frontend/app/`: Next.js 16 App Router views (`cases/`, `chat/`, `contracts/`, `property/`, `review/`, `comparison/`, `reports/`)
- `frontend/lib/`: Client SDKs, API adapters, formatters, and export engines (`api.ts`, `aiEngine.ts`, `legalTranslator.ts`, `reportExporter.ts`)
- `supabase/migrations/`: PostgreSQL schema DDL, RLS policies, vector indices, and RPC functions (001–015)
