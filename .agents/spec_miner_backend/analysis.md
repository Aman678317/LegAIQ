# Backend & Core Domain Services — Comprehensive Specification & Gap Analysis Report

**Date:** 2026-08-20  
**Domain:** Backend & Core Domain Services (FastAPI, Python, Celery, Supabase/PostgreSQL, LangGraph, AI Providers)  
**Author:** `teamwork_preview_spec_miner` (Backend Specialist)  
**Scope:** R1 (Chat Workspace), R2 (Matter Vault & Indic Doc Intelligence), R3 (Spreadsheet Review Tables), R4 (Multi-Agent Orchestration & Workflow Engine), R5 (Contract Intelligence & Playbooks), R6 (Shared Spaces & Enterprise Controls), R7 (India-First Property & Legal Moat)

---

## 1. Executive Summary

Jurisiva AI / LegAIQ possesses an established, highly differentiated India-first backend codebase built on **FastAPI (0.115.0)**, **SQLAlchemy 2.0 / PostgreSQL with pgvector**, **Celery 5.4**, and **Supabase (Auth, RLS, Storage)**.

The platform has established market-leading core capabilities for:
- 12+ Indic language OCR (PaddleOCR + Tesseract + Google Vision)
- Historical degraded deed preprocessing (deskew, CLAHE contrast enhancement, stamp/seal detection, uncertainty calibration)
- 5 major state land portal connectors (Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR)
- Bharatiya Sakshya Adhiniyam 2023 (BSA) evidence admissibility engine & DPDP Act 2023 compliance
- 13-section Title Search Report v2 generation
- 29+ clause contract intelligence engine with risk scoring and redline diffing
- Command Center analytics (productivity, velocity, AI ROI) and Indian PII auto-redaction (Aadhaar, PAN, GST, IFSC, etc.)

**Key Discovery Gaps Identified for Full Enterprise Harvey-Class Parity**:
1. **R3 Review Tables Backend**: No dedicated database tables (`review_tables`, `review_table_columns`, `review_table_cells`) or REST API endpoints exist for prompt-driven spreadsheet extraction across documents.
2. **R4 Workflow Builder Backend**: LangGraph-style workflow execution engine is partially implemented in `app/ai/agents/orchestration.py`, but lacks user-defined visual workflow CRUD, persistent workflow executions, and step-by-step SSE log streaming endpoints.
3. **R5 Playbooks & Clause Library**: Contract intelligence engine extracts 29+ clause types, but lacks persistent `clause_library` and `playbooks` tables, along with deviation check endpoints.
4. **R6 Shared Spaces & Watermarking**: Basic RBAC and signed download URLs exist, but dedicated Shared Spaces (expiring external access links, passcodes) and dynamic PDF watermarking engine are missing.
5. **R7 State Portals & Kanoon API Exposure**: Portal connectors and BSA engine exist in `app/ai/` but require dedicated REST API routes for frontend/external invocations.

---

## 2. Features Discovered Table

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Chat | RAG Legal Chat | Grounded chat with document citations & statutory reasoning | `QuestionRequest(question, language, model, stream)` | JSON or SSE stream with `citations: [Doc: name, Pg: N]` | 404 Case not found, 403 Forbidden | `app/api/analysis.py:217` |
| 2 | R1: Chat | Ollama Local LLM | 100% private, offline LLM inference via Ollama | `OllamaChatRequest(model, messages, system, temp)` | `{content, model, provider, prompt_tokens, completion_tokens}` | 503 if unreachable, falls back to Cloud | `app/api/ai.py:71` |
| 3 | R1: Chat | Vector & Hybrid RAG | Hybrid BM25 full-text + pgvector cosine similarity | `query: str, case_id: UUID, top_k: int` | Deduplicated list of chunk dicts | Empty list if unindexed | `app/api/analysis.py:75` |
| 4 | R1: Chat | Document Explainer | Multi-language structured document summary | `document_id: UUID, language: str` | `{explanation: str, language: str}` | 404 Document not found | `app/api/analysis.py:346` |
| 5 | R2: Vault | Document Upload | Streamed upload to Supabase storage with size & MIME check | `file: UploadFile, document_type: Optional[str]` | Document record with `PROCESSING` status | 400 Bad MIME/Size (>50MB), 500 Storage fail | `app/api/documents.py:30` |
| 6 | R2: Vault | Page Listing & Signed URLs | Paginated OCR pages & time-expiring download URLs | `document_id: UUID` | Signed URL (3600s) / Page text list | 404 Document not found | `app/api/documents.py:142` |
| 7 | R2: Vault | Indic OCR (13 Languages) | Multi-script OCR via PaddleOCR & Tesseract | `file_bytes: bytes, file_type: str, doc_type: str` | `OCRDocumentResult(pages, confidence, script)` | Graceful fallback chain | `app/ai/indic_ocr.py:1` |
| 8 | R2: Vault | Historical Preprocessing | Deskew, CLAHE contrast, stamp detection, uncertainty tag | `img: PIL.Image` | `PreprocessedImageResult`, `[UNCERTAIN: ...]` | Returns original image on failure | `app/ai/historical_ocr.py:45` |
| 9 | R2: Vault | Camera Photo Preprocessing | 4-point perspective warp & glare normalization for mobile | `img: PIL.Image` | Perspective-corrected image | Fallback to historical preprocessor | `app/ai/historical_ocr.py:227` |
| 10 | R2: Vault | Document Translation | Translation of legal pages into 13 Indian languages | `document_id: UUID, page: int, language: str` | `{page_number, language, text, cached}` | 400 Unsupported lang, 404 Page | `app/api/documents.py:175` |
| 11 | R2: Vault | Document Comparison | Version/cross-deed comparison for survey, dates, amounts | `document_ids: List[UUID]` (2-6 docs) | `{job_id, status: QUEUED}` | 400 <2 docs in case | `app/api/comparison.py:28` |
| 12 | R3: Tables | Review Tables *(GAP)* | Structured prompt column bulk extraction across docs | *(Requires Implementation)* | *(Requires Implementation)* | *(Requires Implementation)* | `ORIGINAL_REQUEST.md:18` |
| 13 | R4: Agents | Agent Execution Budgeting | Token, cost ($0.50), time (240s), iteration cap guards | `AgentContext`, `AgentBudget` | Execution outcome or `BudgetExceededError` | Persists `FAILED` in `agent_runs` | `app/ai/agents/base.py:44` |
| 14 | R4: Agents | Scoped Tool Registry | Permission-checked case-scoped tools with audit logging | `ctx: AgentContext, name: str, params: dict` | Tool result dict | `ToolError` on lack of permission | `app/ai/agents/tools.py:37` |
| 15 | R4: Agents | Risk Agent | Mismatch & entity evaluation to generate grounded risks | `case_id: UUID` | `{risks_created: int}` | Malformed output skipped safely | `app/ai/agents/registry.py:26` |
| 16 | R4: Agents | Report Agent | Compiles 13-section Title Search Report v2 or Due Diligence | `case_id: UUID, report_id: UUID` | Structured report JSON in `reports` table | Falls back to deterministic compilation | `app/ai/agents/registry.py:98` |
| 17 | R4: Agents | Verification Agent | Fact-checks legal draft against extracted entities | `draft_id: UUID` | Draft appended with `[VERIFY:]` report | Flags unmatched statements | `app/ai/agents/registry.py:306` |
| 18 | R4: Agents | Voice Agent | Spoken Q&A assistant in 12+ Indic languages | `question: str, language: str` | `{answer, citations, language}` | "Not found in documents" if unevidenced | `app/ai/agents/registry.py:380` |
| 19 | R4: Agents | LangGraph Workflow Engine | Multi-step DAG orchestration with dependency resolution | `WorkflowState, WorkflowDefinition` | `WorkflowState` with node execution outcomes | Updates node status `FAILED` | `app/ai/agents/orchestration.py:86` |
| 20 | R5: Contracts | 29+ Clause Extraction | Regex + layout recognition of 29 contract clause types | `full_text: str, contract_id: str` | `List[ContractClause]` with span offsets | Unmatched assigned to `CUSTOM` | `app/ai/contract_intelligence.py:176` |
| 21 | R5: Contracts | Obligation Tracking | Extracts party obligations, deadlines, and breach conditions | `doc: ContractDocument` | `List[ContractObligation]` | Returns empty list on simple text | `app/ai/contract_intelligence.py:61` |
| 22 | R5: Contracts | Risk Scoring (0-100) | Weighted risk scoring across missing/risky clauses | `doc: ContractDocument` | `ContractRiskAssessment(score, critical_issues)` | Safe default 0 risk score | `app/ai/contract_intelligence.py:139` |
| 23 | R5: Contracts | Redline Diff Engine | Side-by-side contract comparison with change tracking | `orig_doc: ContractDoc, mod_doc: ContractDoc` | `List[RedlineChange]` (insert/delete/modify) | Empty list if identical | `app/ai/contract_intelligence.py:124` |
| 24 | R5: Contracts | Clause Library *(GAP)* | Searchable standard clauses with fallback guidelines | *(Requires Implementation)* | *(Requires Implementation)* | *(Requires Implementation)* | `ORIGINAL_REQUEST.md:24` |
| 25 | R5: Contracts | Playbook Engine *(GAP)* | Precedent management & deviation detection | *(Requires Implementation)* | *(Requires Implementation)* | *(Requires Implementation)* | `ORIGINAL_REQUEST.md:24` |
| 26 | R6: Enterprise| Indian PII Auto-Redaction | Detects/masks Aadhaar, PAN, GST, IFSC, Phone, Names | `text: str, config: RedactionConfig` | `PIIRedactionResponse(redacted_text, map)` | Preserves text if detector unconfigured | `app/api/pii.py:120` |
| 27 | R6: Enterprise| Command Center Analytics | Team productivity, turnaround velocity, AI ROI | `org_id: UUID, period: TimeRange` | Productivity, velocity, and ROI JSON models | 403 if not member | `app/api/analytics.py:1` |
| 28 | R6: Enterprise| Enterprise SSO (SAML/OIDC)| SAML 2.0 & OIDC authentication with PKCE & auto-provision | `SSOProviderCreate` | SSO redirect URLs, metadata XML | 400 invalid cert, 401 unauthenticated | `app/api/sso.py:1` |
| 29 | R6: Enterprise| Shared Spaces *(GAP)* | Collaborator spaces, watermarking, expiring links | *(Requires Implementation)* | *(Requires Implementation)* | *(Requires Implementation)* | `ORIGINAL_REQUEST.md:27` |
| 30 | R7: Moat | 5 State Land Connectors | Scrapes/connects to Mahabhulekh, Bhoomi, TN, TG, GJ | `survey_number, district, taluk, village` | Standardized `LandRecord` struct | Rate limit handling, mock mode fallback | `app/ai/state_portals.py:91` |
| 31 | R7: Moat | BSA 2023 Evidence Engine | Evidence admissibility rules under BSA 2023 (Sec 3-114) | `EvidenceItem` | `AdmissibilityReport` (status, objections) | Marks `REQUIRES_FOUNDATION` | `app/ai/bharatiya_sakshya.py:141` |
| 32 | R7: Moat | 13-30 Yr Ownership Graph | Reconstructs person/property nodes & transfer edges | `case_id: UUID` | `{nodes: [...], edges: [...]}` | Rebuild queues Celery job | `app/api/ownership.py:21` |
| 33 | R7: Moat | Title Search Report v2 | 13-section legal report with digital signature block | `TitleSearchReport` | Formatted PDF/DOCX report bytes | Fallback to text synthesis | `app/ai/title_search_report.py:100` |
| 34 | R7: Moat | Regional Land Record Units | Normalizes 15+ Indian land units (Guntha, Bigha, Cent, etc.)| `raw_area: str, state: str` | `NormalizedLandArea(sq_meters, acres, guntas)` | Unrecognized returned raw | `app/ai/land_intelligence.py:25` |
| 35 | R7: Moat | Kanoon Legal Research | SSRF-safe multi-source research across Kanoon, India Code | `ResearchRequest(question, jurisdiction, depth)` | `ResearchResponse` with verified sources | Empty list on search provider error | `app/api/research.py:1` |

---

## 3. Edge Cases & Behavioral Matrix

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Chat RAG (`ask_question`) | Question when no case documents are uploaded | Bypasses vector match, queries LLM with prompt advising no uploaded documents available, producing Indian statutory/precedent legal analysis. |
| 2 | Chat RAG (`ask_question`) | Ollama server is offline/unreachable | Catches `httpx.ConnectError`, gracefully routes request to cloud providers (`openai`/`anthropic`) or returns explicit "Not configured" message without crashing. |
| 3 | Indic OCR (`PaddleOCR`) | High-resolution PDF with mixed Devanagari and English | Converts PDF to 300 DPI images via `pdf2image`, runs deskewing + CLAHE, executes PaddleOCR with angle classification, maps bounding boxes, detects script as Devanagari. |
| 4 | Historical OCR | Degraded 1975 deed with standard deviation < 48.0 | `_assess_quality` flags `is_faded_or_damaged=True`, applies 1.8x sharpening and 1.6x contrast enhancement, marks tokens with confidence < 0.60 as `[UNCERTAIN: ... (conf: X%)]`. |
| 5 | Agent Execution | Agent exceeds 8 iterations or $0.50 cost | `UsageTracker` catches limit, raises `LoopLimitError` or `BudgetExceededError`, marks `agent_runs.status = 'FAILED'`, prevents runaway spend. |
| 6 | Contract Redlining | Identical contract texts passed | Diff engine identifies 0 changes, returns `total_changes: 0` and clean summary document without errors. |
| 7 | Indian PII Redactor | Text with 12-digit Aadhaar & 10-char PAN | Regex & Presidio engines identify Aadhaar (`\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b`) and PAN (`\b[A-Z]{5}[0-9]{4}[A-Z]\b`), masks to `****-****-1234` or custom replacement. |
| 8 | Land Record Connectors | Unofficial/blocked state portal scrapers | Falls back to realistic state-specific `_create_mock_record` generating valid 7/12 or RTC records with mutation history and encumbrance details. |
| 9 | BSA 2023 Engine | Uncertified photocopy created 10 years ago | Flags `AdmissibilityStatus.CONDITIONALLY_ADMISSIBLE`, cites Section 58/60, and adds objection: "Uncertified copy - requires explanation for non-production of original". |
| 10 | BSA 2023 Engine | Document created > 30 years ago (1985 deed) | Flags `DocumentCategory.ANCIENT_DOCUMENT`, cites Section 94, applies legal presumption of genuineness, elevates status to `ADMISSIBLE`. |

---

## 4. Existing vs. Missing Endpoints Inventory

### R1. Assistant & Chat Workspace
- **Existing Endpoints**:
  - `POST /api/v1/cases/{case_id}/questions` (RAG Q&A with streaming & citations)
  - `GET /api/v1/cases/{case_id}/questions` (Chat history)
  - `POST /api/v1/documents/{document_id}/explain` (Document summary)
  - `GET /api/v1/ai/ollama/status` (Ollama connection & model list)
  - `POST /api/v1/ai/ollama/chat` (Direct Ollama proxy)
  - `POST /api/v1/ai/embed` (Generate embeddings)
  - `GET /api/v1/ai/providers` (Provider readiness check)
  - `POST /api/v1/cases/{case_id}/drafts` (Legal drafting)
  - `POST /api/v1/research` (SSRF-protected legal research)
- **Missing / Enhanced Endpoints Required**:
  - Update `POST /api/v1/cases/{case_id}/questions` body to support:
    - `india_context: bool = True` (activates state revenue glossary and statutory reasoning)
    - `reasoning_depth: str = "standard"` ("quick", "standard", "deep" / DeepSeek R1 reasoning mode)
    - `mode: str = "ask"` ("ask", "analyze", "draft")

### R2. Secure Matter Vault & Indic Document Intelligence
- **Existing Endpoints**:
  - `POST /api/v1/cases/{case_id}/documents` (Single document upload)
  - `GET /api/v1/cases/{case_id}/documents` (List case documents)
  - `GET /api/v1/cases/{case_id}/documents/{document_id}` (Get document details)
  - `GET /api/v1/cases/{case_id}/documents/{document_id}/download-url` (Expiring signed download URL)
  - `GET /api/v1/cases/{case_id}/documents/{document_id}/pages` (Get OCR pages with confidence)
  - `POST /api/v1/cases/{case_id}/documents/{document_id}/translate` (Translate page to Indic language)
  - `GET /api/v1/cases/{case_id}/documents/{document_id}/pages/{page}/translation/{lang}` (Get cached translation)
  - `POST /api/v1/cases/{case_id}/compare` (Trigger multi-document comparison)
  - `GET /api/v1/cases/{case_id}/comparison` (Get comparison results)
  - `DELETE /api/v1/cases/{case_id}/documents/{document_id}` (Delete document & storage)
- **Missing Endpoints Required**:
  - `POST /api/v1/cases/{case_id}/documents/bulk` (Bulk upload of PDF, DOCX, XLSX, images)
  - `POST /api/v1/cases/{case_id}/documents/{document_id}/classify` (Run automatic document classification)
  - `POST /api/v1/cases/{case_id}/documents/{document_id}/reprocess-ocr` (Force dual-pass PaddleOCR + Tesseract reprocessing)

### R3. Spreadsheet Review Tables *(New Module)*
- **Existing Endpoints**: None.
- **Missing Endpoints Required (`app/api/review_tables.py`)**:
  - `POST /api/v1/cases/{case_id}/review-tables` (Create new review table workspace)
  - `GET /api/v1/cases/{case_id}/review-tables` (List review tables for case)
  - `GET /api/v1/review-tables/{table_id}` (Get table grid with columns, rows/documents, and cell values)
  - `POST /api/v1/review-tables/{table_id}/columns` (Add custom prompt extraction column)
  - `PATCH /api/v1/review-tables/{table_id}/columns/{column_id}` (Update column prompt/type)
  - `DELETE /api/v1/review-tables/{table_id}/columns/{column_id}` (Delete column)
  - `POST /api/v1/review-tables/{table_id}/extract` (Run bulk LLM extraction across documents)
  - `PATCH /api/v1/review-tables/{table_id}/cells/{cell_id}` (Edit/verify cell value)
  - `GET /api/v1/review-tables/{table_id}/export` (Export spreadsheet to CSV or XLSX)

### R4. Multi-Agent Orchestration & Workflow Builder
- **Existing Endpoints**:
  - `GET /api/v1/admin/agent-runs` (Platform agent run log)
  - `GET /api/v1/cases/{case_id}/voice/sessions` (Voice sessions & turns)
  - `POST /api/v1/cases/{case_id}/voice/ask` (Spoken question agent invocation)
- **Missing Endpoints Required (`app/api/workflows.py`)**:
  - `GET /api/v1/orgs/{org_id}/workflows` (List custom workflow templates & DAGs)
  - `POST /api/v1/orgs/{org_id}/workflows` (Create/save visual workflow definition)
  - `GET /api/v1/workflows/{workflow_id}` (Get workflow definition)
  - `PATCH /api/v1/workflows/{workflow_id}` (Update workflow definition)
  - `DELETE /api/v1/workflows/{workflow_id}` (Delete workflow)
  - `POST /api/v1/cases/{case_id}/workflows/{workflow_id}/run` (Execute workflow on case)
  - `GET /api/v1/workflows/executions/{execution_id}` (Get execution state & node results)
  - `GET /api/v1/workflows/executions/{execution_id}/stream` (SSE stream of agent tool execution logs)

### R5. Contract Intelligence, Clause Library & Playbooks
- **Existing Endpoints**:
  - `POST /api/v1/cases/{case_id}/contracts/analyze` (Extract 29+ clause types, risks, obligations)
  - `POST /api/v1/cases/{case_id}/contracts/redline` (Redline diffing between two contract versions)
- **Missing Endpoints Required (`app/api/clause_library.py` & `app/api/playbooks.py`)**:
  - `GET /api/v1/clause-library` (Search clause library by clause type, jurisdiction, tags)
  - `POST /api/v1/clause-library` (Add standard/fallback clause entry)
  - `GET /api/v1/clause-library/{id}` (Get clause guidance & fallbacks)
  - `PATCH /api/v1/clause-library/{id}` (Update clause entry)
  - `DELETE /api/v1/clause-library/{id}` (Delete clause entry)
  - `GET /api/v1/orgs/{org_id}/playbooks` (List negotiation playbooks)
  - `POST /api/v1/orgs/{org_id}/playbooks` (Create playbook with rules & fallback guidelines)
  - `GET /api/v1/playbooks/{playbook_id}` (Get playbook details)
  - `PATCH /api/v1/playbooks/{playbook_id}` (Update playbook rules)
  - `POST /api/v1/cases/{case_id}/contracts/playbook-review` (Score contract deviations against playbook)

### R6. Shared Spaces & Enterprise Controls
- **Existing Endpoints**:
  - `POST /api/v1/pii/detect` (Detect Indian & general PII)
  - `POST /api/v1/pii/redact` (Redact PII from text)
  - `POST /api/v1/pii/redact-document` (Redact PII across document pages)
  - `POST /api/v1/pii/redact-case` (Batch redact case documents)
  - `GET /api/v1/analytics/team-productivity` (Command Center productivity metrics)
  - `GET /api/v1/analytics/case-velocity` (Turnaround velocity metrics)
  - `GET /api/v1/analytics/ai-roi` (AI ROI and token cost analytics)
  - `POST /api/v1/auth/sso/providers` & auth endpoints (Enterprise SAML/OIDC)
  - `GET /api/v1/orgs/{org_id}/billing` (Metered usage & plans)
- **Missing Endpoints Required (`app/api/shared_spaces.py`)**:
  - `POST /api/v1/cases/{case_id}/shared-spaces` (Create shared space with expiring token & passcode)
  - `GET /api/v1/cases/{case_id}/shared-spaces` (List shared spaces for case)
  - `GET /api/v1/shared-spaces/{space_id}` (Get space details & collaborator permissions)
  - `DELETE /api/v1/shared-spaces/{space_id}` (Revoke shared space)
  - `GET /api/v1/public/shared-spaces/{share_token}` (Public entry point for external collaborators)
  - `GET /api/v1/public/shared-spaces/{share_token}/documents/{document_id}/download` (Download watermarked document with dynamic recipient text)

### R7. India-First Property & Legal Moat
- **Existing Endpoints**:
  - `GET /api/v1/cases/{case_id}/ownership` (Get ownership graph)
  - `POST /api/v1/cases/{case_id}/ownership/rebuild` (Rebuild 13-30 yr ownership graph)
  - `GET /api/v1/cases/{case_id}/timeline` (Chronological deed timeline)
  - `GET /api/v1/cases/{case_id}/property` (Property details with field-level verification sources)
  - `PATCH /api/v1/cases/{case_id}/property` (Update property attributes)
  - `POST /api/v1/cases/{case_id}/reports` (Generate Property Due Diligence Report)
  - `POST /api/v1/reports/{report_id}/export` (Export Title Search Report to PDF/DOCX)
- **Missing Endpoints Required (`app/api/state_portals.py` & `app/api/bharatiya_sakshya.py`)**:
  - `GET /api/v1/portals/states` (List 5+ supported state portals: MH, KA, TN, TG, GJ)
  - `POST /api/v1/portals/{state}/search` (Query state land portal by survey number / owner)
  - `POST /api/v1/portals/{state}/mutation` (Fetch mutation records for survey number)
  - `POST /api/v1/portals/{state}/encumbrance` (Fetch 30-year EC from state portal)
  - `POST /api/v1/cases/{case_id}/portals/import` (Import portal record into case timeline and ownership nodes)
  - `POST /api/v1/cases/{case_id}/evidence/admissibility-report` (Generate BSA 2023 Admissibility Report)
  - `GET /api/v1/kanoon/search` (Search Indian Kanoon Supreme Court & High Court judgments)

---

## 5. Database Schema & Migration Requirements

The Supabase PostgreSQL database currently contains:
- `organizations`, `profiles`, `memberships`
- `cases`, `case_collaborators`, `properties`, `property_field_sources`
- `documents`, `document_pages`, `page_translations`, `document_chunks`
- `extracted_entities`, `persons`, `chat_messages`
- `ownership_nodes`, `ownership_edges`, `timeline_events`
- `comparison_results`, `risks`, `findings`
- `research_sessions`, `research_sources`, `drafts`, `reports`
- `ai_runs`, `audit_events`, `agent_runs`, `agent_tool_calls`, `voice_sessions`, `voice_turns`
- `plans`, `subscriptions`, `usage_events`

### New Database Tables Required (Migration `013_harvey_parity.sql`):

```sql
-- ============================================================
-- 013: Harvey Parity & India-First Extensions
-- ============================================================

-- 1. Review Tables Workspace (R3)
CREATE TABLE IF NOT EXISTS public.review_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES public.cases(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_table_columns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id UUID NOT NULL REFERENCES public.review_tables(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  prompt TEXT NOT NULL,
  data_type TEXT NOT NULL DEFAULT 'text' CHECK (data_type IN ('text', 'number', 'date', 'boolean', 'currency', 'entity')),
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.review_table_cells (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id UUID NOT NULL REFERENCES public.review_tables(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  column_id UUID NOT NULL REFERENCES public.review_table_columns(id) ON DELETE CASCADE,
  extracted_value TEXT,
  confidence NUMERIC DEFAULT 0.0,
  evidence JSONB, -- {source_text, page_number, chunk_id, bounding_boxes}
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
  error_message TEXT,
  verified_by_user BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(table_id, document_id, column_id)
);

-- 2. Visual Workflow Builder & Executions (R4)
CREATE TABLE IF NOT EXISTS public.workflow_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  graph_definition JSONB NOT NULL, -- {nodes: [...], edges: [...], entry_node: str}
  is_template BOOLEAN NOT NULL DEFAULT false,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.workflow_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID REFERENCES public.workflow_definitions(id) ON DELETE SET NULL,
  case_id UUID NOT NULL REFERENCES public.cases(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
  state JSONB NOT NULL DEFAULT '{}'::jsonb,
  execution_logs JSONB NOT NULL DEFAULT '[]'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- 3. Clause Library & Negotiation Playbooks (R5)
CREATE TABLE IF NOT EXISTS public.clause_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
  clause_type TEXT NOT NULL,
  title TEXT NOT NULL,
  standard_language TEXT NOT NULL,
  fallback_language TEXT,
  guidance_notes TEXT,
  jurisdiction TEXT DEFAULT 'India',
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  is_standard BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  contract_type TEXT NOT NULL,
  rules JSONB NOT NULL DEFAULT '[]'::jsonb, -- [{clause_type, acceptable_terms, dealbreakers, fallback_clause_id, risk_weight}]
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Shared Spaces & Expiring Links (R6)
CREATE TABLE IF NOT EXISTS public.shared_spaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES public.cases(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  share_token TEXT NOT NULL UNIQUE,
  permissions JSONB NOT NULL DEFAULT '{"can_view": true, "can_download": false, "can_comment": false}'::jsonb,
  passcode_hash TEXT,
  watermark_enabled BOOLEAN NOT NULL DEFAULT true,
  watermark_text TEXT,
  expires_at TIMESTAMPTZ,
  max_access_count INTEGER,
  access_count INTEGER NOT NULL DEFAULT 0,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 6. Dependencies & Requirements Summary

Current `requirements.txt` contains:
- `fastapi==0.115.0`, `uvicorn[standard]==0.30.0`
- `sqlalchemy==2.0.35`, `asyncpg==0.31.0`
- `pydantic==2.9.0`, `pydantic-settings==2.5.0`
- `supabase==2.10.0`, `celery[redis]==5.4.0`, `redis==5.0.8`
- `httpx==0.27.2`, `python-multipart==0.0.12`, `aiofiles==24.1.0`
- `Pillow>=10.2.0,<12.0.0`, `pdf2image==1.17.0`, `opencv-python-headless==4.10.0.84`
- `pytesseract==0.3.13`, `langdetect==1.0.9`, `langchain-text-splitters==0.2.4`
- `litellm>=1.49.0`, `openai>=1.51.0,<2.0.0`, `anthropic>=0.34.0`, `google-cloud-vision==3.7.0`
- `presidio-analyzer>=2.2.350`, `presidio-anonymizer>=2.2.350`, `spacy>=3.7.0`
- `sse-starlette==2.1.3`, `slowapi==0.1.9`, `defusedxml>=0.7.1`

**Recommended Additional Dependencies for Full Parity**:
1. `paddlepaddle` / `paddleocr` (for Indic OCR inference on supported platforms)
2. `python-docx>=1.1.0` (for DOCX deed and report generation)
3. `openpyxl>=3.1.5` & `pandas>=2.2.0` (for Excel review table export)
4. `pypdf>=4.3.0` or `reportlab>=4.2.0` (for dynamic PDF watermarking engine)

---

## 7. Architectural Recommendations for Implementation

1. **Maintain Zero-Regression & Fake-Supabase Compatibility**:
   - Every new table (`review_tables`, `review_table_columns`, `review_table_cells`, `workflow_definitions`, `workflow_executions`, `clause_library`, `playbooks`, `shared_spaces`) must be mirrored in `backend/tests/fakes/fake_supabase.py` and `conftest.py` so the full unit and integration pytest suites run offline with zero external network dependencies.
2. **Review Table Extraction Pipeline**:
   - Create `app/services/review_table_service.py` to handle chunking, prompt generation with few-shot Indian legal examples, extraction confidence calculation, and evidence snippet bounding-box linking.
3. **Workflow Execution Streaming**:
   - Utilize existing `sse-starlette` to stream agent tool calls and step status in real time to the frontend Workflow Builder UI.
4. **Preserve Indian Legal Grounding & Anti-Hallucination**:
   - Enforce mandatory evidence citations `[Doc: name, Pg: N]` and explicit statutory provisions (`Transfer of Property Act 1882`, `Registration Act 1908`, `Bharatiya Sakshya Adhiniyam 2023`).
