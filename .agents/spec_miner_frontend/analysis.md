# Frontend & UI Architecture Specification Mining Report

**Date:** 2026-08-20  
**Author:** teamwork_preview_spec_miner (Frontend & UI Architecture)  
**Target Application:** LegAIQ / Jurisiva AI (Enterprise Legal Intelligence Platform)  
**Integrity Mode:** Development  

---

## 1. Executive Summary & Tech Stack Overview

LegAIQ (Jurisiva AI) frontend is architected as an enterprise legal intelligence web application tailored for Indian law and property due diligence.

### Technical Stack Summary
- **Framework:** Next.js 16.3.1 (App Router, Server & Client Components)
- **UI Library:** React 19.2.8, TypeScript 5.x
- **Styling:** Tailwind CSS v4 (`@import "tailwindcss"`, `@theme` config in `app/globals.css`), `class-variance-authority`, `clsx`, `tailwind-merge`
- **Icons:** `lucide-react` (1.31.0)
- **State Management & Data:**
  - Client state: React hooks (`useState`, `useCallback`, `useMemo`, `useRef`) & Zustand (5.0.15)
  - Remote Auth & Data: `@supabase/supabase-js` (2.112.3) + `@supabase/ssr` (0.12.4)
  - Real-time updates: Server-Sent Events (SSE) via `useCaseEvents.ts` with automated polling fallback
  - Offline & PWA: Custom Service Worker, IndexedDB via `offline-db.ts`, Background Sync via `background-sync.ts`, PWA install prompt
- **API Client:** Centralized `frontend/lib/api.ts` with automated session management, 401 auto-refresh, offline demo fallback via `mockStore.ts`
- **Testing:** Vitest 4.1.11 (`happy-dom`, `@testing-library/react`), Playwright 1.62.1 E2E tests

---

## 2. Comprehensive Requirements Cross-Reference (R1 – R7)

### R1. Assistant & Chat Workspace UI

#### Authoritative Requirements:
- Unified Legal Assistant workspace supporting **Ask**, **Analyze**, and **Draft** modes.
- Real-time streaming output with reasoning depth and latency indicators.
- Inline clickable citations `[Doc: name, Pg: N]` linking directly to document viewer and source evidence snippets.
- Multi-model selection dropdown (Local Ollama 70B, Claude 3.5 Sonnet, GPT-4o, DeepSeek R1, Mistral Large).
- India Context toggle for statutory reasoning (BNS/BNSS/BSA 2023, state-specific revenue terminology).

#### Existing Implementation Status:
- **Routes:** `(app)/chat/page.tsx` (Universal Ollama chatbot), `(app)/cases/[caseId]/questions/page.tsx` (Case-specific legal Q&A).
- **Streaming:** Implemented in `api.askQuestionStream()` using Fetch + ReadableStream (`TextDecoder`, SSE parsing).
- **Model Picker:** Implemented in `questions/page.tsx` and `chat/page.tsx` with dynamic detection of local Ollama models plus predefined cloud models (Claude 3.5, GPT-4o, DeepSeek R1).
- **Language Selector:** 12+ Indic languages supported (`en`, `hi`, `kn`, `ta`, `te`, `mr`, `gu`, `bn`, etc.).

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Mode Switcher (Ask / Analyze / Draft)** | Fragmented across separate routes (`/questions`, `/analysis`, `/drafting`) | Unified mode switcher toolbar inside Assistant workspace allowing one-click mode switching without route hopping | High |
| **Inline Clickable Citations** | Citations rendered as static list block below response message | Interactive inline citation badges `[Doc: name, Pg: N]` embedded in text; clicking opens viewer side panel at exact page | High |
| **India Context Toggle** | Hardcoded prompts in `aiEngine.ts` | Explicit UI toggle switch to enable/disable India statutory & state portal reasoning mode | High |
| **Prompt Template Drawer** | 6 static suggestion chips | Searchable library of Harvey-class prompt templates for Due Diligence, Tax, Conveyance, Litigation | Medium |

---

### R2. Secure Matter Vault UI & Document Viewer

#### Authoritative Requirements:
- Matter-centric document intelligence Vault supporting bulk uploads (PDF, DOCX, XLSX, TIFF, PNG, JPG).
- Dual-pass OCR viewer (Tesseract + PaddleOCR with 12+ Indic languages).
- Historical deed preprocessing visualization (deskewed, CLAHE contrast restored, uncertain token tags `[UNCERTAIN: ...]`).
- Automatic document classification badges (Sale Deed, Partition Deed, 7/12 Extract, RTC/Pahani, Mutation Extract, Court Order).
- Entity extraction display (Survey#, Khasra, Khata, Extent, Hissa, Consideration, Dates).
- Side-by-side version compare and visual diffing.

#### Existing Implementation Status:
- **Routes:** `(app)/cases/[caseId]/documents/page.tsx`, `(app)/cases/[caseId]/comparison/page.tsx`.
- **Upload Zone:** `react-dropzone` with drag-and-drop for PDF, JPG, PNG, TIFF up to 50MB.
- **SSE Status:** Live updates with `useCaseEvents` (`live` vs `polling` badge).
- **Document Viewer:** Modal viewer with page navigation, CLAHE contrast indicator, uncertainty tag warning (`[UNCERTAIN: ...]`), page translation dropdown, and document explanation.
- **Comparison:** `(app)/cases/[caseId]/comparison/page.tsx` with match/mismatch/missing counts, inline diff view (`DiffView`), and source text quotes.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Supported File Formats** | PDF, JPG, PNG, TIFF | Add DOCX, XLSX support in dropzone & viewer | High |
| **Document Classification Badges** | Generic status (`COMPLETED`, `PROCESSING`) | Automatic classification badge: `Sale Deed`, `Partition Deed`, `7/12 Extract`, `RTC / Pahani`, `Mutation Extract`, `Court Order` | High |
| **Dual-Pass OCR Layer View** | Single text view | Dual-pass toggle (Raw Scanned Image vs Clean Extracted Text vs Tesseract+PaddleOCR confidence overlay) | High |
| **Side-by-Side Synchronized Scroll Viewer** | Tabbed diff comparison cards | Dual-pane synchronized page-by-page document viewer with visual bounding boxes | Medium |

---

### R3. Spreadsheet-Style Review Tables UI

#### Authoritative Requirements:
- Interactive Review Table workspace for bulk structured extraction across matter documents.
- Customizable prompt-driven extraction columns (e.g. "Grantor", "Consideration Amount", "Survey No.", "Stamp Duty", "Indemnity Cap").
- Cell-level evidence linking: Clicking any cell opens the document snippet in the document viewer with highlighted source text.
- Confidence score chips (e.g. 95% green, 60% amber, uncertain red).
- CSV/Excel export functionality.

#### Existing Implementation Status:
- **COMPLETELY MISSING**. No review table component or route currently exists in the frontend.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Review Table Workspace Route** | None | Create `(app)/cases/[caseId]/review/page.tsx` | Critical |
| **Dynamic Spreadsheet Grid** | None | Interactive grid with sticky document rows, resizable columns, sorting, filtering | Critical |
| **Custom Column Creator** | None | "Add Column" modal with LLM extraction prompt definition, data type selector (Text, Amount, Date, Party, Yes/No) | Critical |
| **Cell Evidence Drawer** | None | Cell click popover/drawer displaying extracted value, confidence chip, document name, page number, and source snippet | Critical |
| **CSV / Excel Export** | None | One-click export to `.csv` and `.xlsx` format | High |

---

### R4. No-Code Visual Workflow Builder UI

#### Authoritative Requirements:
- Drag-and-drop agent/node canvas (Legal Research, Contract Review, Due Diligence, Title Search, Citation Auditor, Custom LLM Step, Condition, Notification).
- Node configurations drawer (prompts, model, tools, retries, input/output mappings).
- Pre-built legal workflow templates (Property Due Diligence, Title Search Report v2, Contract Intelligence, Voice Q&A).
- Test runs, execution triggers, and real-time execution logs/timeline.

#### Existing Implementation Status:
- **Backend:** `backend/app/ai/agents/orchestration.py` has full `AgentOrchestrator`, `WorkflowDefinition`, `WorkflowNode`, and built-in workflows.
- **Frontend:** `(app)/admin/agent-runs/page.tsx` has a read-only admin table of historical agent runs and tool calls.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Workflow Studio Route** | None | Create `(app)/workflows/page.tsx` or `(app)/cases/[caseId]/workflows/page.tsx` | High |
| **Visual Node Canvas** | None | Drag-and-drop workflow canvas (triggers, agent nodes, condition branches, output nodes) | High |
| **Node Config Drawer** | None | Slide-over inspector to configure agent model, temperature, prompt template, tool whitelist | High |
| **Execution Progress Visualizer** | Static table in admin | Live visual execution timeline with glowing active nodes and step-by-step progress | High |

---

### R5. Contract Intelligence & Clause Library UI

#### Authoritative Requirements:
- Clause breakdown view (29+ clause types: Parties, Indemnity, Limitation of Liability, Termination, Governing Law, Non-Compete, etc.).
- 0–100 risk score badges (Critical, High, Medium, Low, Negligible).
- Playbook deviation detection flags & missing clause alerts.
- Searchable Clause Library with fallback language guidelines (standard fallback, aggressive fallback, mutual compromise).
- Redline visual diffing (side-by-side tracked changes editor with accept/reject modifications).

#### Existing Implementation Status:
- **Backend:** `backend/app/ai/contract_intelligence.py` has 29+ clause types extraction, risk scoring (0-100), redlining, obligation tracking, and Indian law compliance rules.
- **Frontend API:** `api.analyzeContract` and `api.redlineContract` in `frontend/lib/api.ts`.
- **Frontend Pages:** Basic `(app)/cases/[caseId]/risks/page.tsx` and `(app)/cases/[caseId]/drafting/page.tsx`.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Contract Intelligence Workspace** | None | Create `(app)/cases/[caseId]/contracts/page.tsx` | High |
| **29+ Clause Breakdown View** | None | Accordion / list of extracted clauses with risk badges, section numbers, obligation links | High |
| **Risk Score Meter (0-100)** | Count badges in risks page | 0–100 visual risk score gauge with critical issue callouts and Indian statutory compliance gaps | High |
| **Clause Library & Playbooks UI** | None | Searchable clause library with fallback guidelines & negotiation playbook editor | High |
| **Redline Diff Editor** | DiffView in comparison page | Interactive contract redlining editor with tracked changes and Accept/Reject buttons | High |

---

### R6. Enterprise Command Center & Shared Spaces UI

#### Authoritative Requirements:
- Matter-level Shared Spaces with collaborator permissions (Owner, Admin, Lawyer, Reviewer, Staff, Client).
- Watermark settings (dynamic watermark text, viewer email, timestamp on document exports/previews).
- Link expiry & password-protected sharing modal (1 hr, 24 hr, 7 days, custom date, view-only / download permissions).
- Command Center analytics dashboard for AI costs, token usage, turnaround velocity, ROI metrics.
- PII auto-redaction preview for Indian identifiers (Aadhaar, PAN, GST, IFSC, Voter ID, Passport).

#### Existing Implementation Status:
- **Admin Pages:** `(app)/admin/ai-usage/page.tsx` (AI runs, tokens, costs), `(app)/admin/audit/page.tsx` (audit events), `(app)/settings/page.tsx` (org members & roles).
- **Backend PII:** `backend/app/api/pii.py` has `/pii/detect`, `/pii/redact`, `/pii/redact-case`.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Matter Shared Space / Share Modal** | None | "Share Matter" modal with link expiry (1h/24h/7d), password protection, and access permissions | High |
| **Watermark Configuration UI** | None | Watermark settings panel (custom text, user email overlay, opacity) | Medium |
| **Command Center Velocity & ROI** | Basic token count table | Turnaround velocity charts, cost savings calculator, and per-matter cost attribution | Medium |
| **PII Redaction Preview Drawer** | None | Interactive PII preview highlighting Aadhaar/PAN/GST with unmask toggle before export | High |

---

### R7. India-First Property & Legal Moat

#### Authoritative Requirements:
- State land portal integration UI (28+ state portal selector: Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR, etc. with cascading district/taluk/village pickers).
- 13–30 year property ownership chain interactive visual graph with node drilldown.
- Encumbrance timeline & Form 15/16 inspection view.
- Bharatiya Sakshya Adhiniyam 2023 (BSA) citation & evidence compliance drawer.
- Indian Kanoon & Supreme Court legal research panel with verified statutory citations.

#### Existing Implementation Status:
- **Routes:** `(app)/cases/[caseId]/property/page.tsx`, `(app)/cases/[caseId]/ownership/page.tsx`, `(app)/cases/[caseId]/timeline/page.tsx`, `(app)/cases/[caseId]/research/page.tsx`, `(app)/cases/[caseId]/reports/page.tsx`.
- **Property Features:** Document verified field matrix, Advocate due diligence inquiry checklist, Indian land area unit converter widget.
- **Ownership:** List of relationship cards with evidence quotes.
- **Reports:** Complete Title Search & Due Diligence report generation with PDF/Word/Text exports.

#### Gaps & Missing Capabilities:
| Feature | Current State | Required State | Priority |
|---|---|---|---|
| **Live State Land Portal Search UI** | API stub in `api.searchLandPortal` | Dedicated Land Portal Search tab/modal with 28+ State selector, District/Taluk/Village dropdowns, and instant RTC/7-12 fetch | High |
| **Interactive Graph Canvas for Ownership** | Card list | Interactive node-link graph visualization with 13-30 year timeline scrubber and entity zoom | High |
| **Bharatiya Sakshya Act (BSA 2023) Drawer** | Research prompts | BSA 2023 evidence admissibility audit panel (checking Section 61, 62, 63 electronic record certificates) | High |
| **Kanoon Judgment Preview Panel** | Research links | Embedded judgment reading drawer with headnotes and ratio decidendi breakdown | Medium |

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | R1 (Chat) | `askQuestionStream` | Real-time SSE streaming Q&A with Indian legal reasoner | `caseId`, `question`, `language`, `model`, `onChunk` | Stream chunks, final response object with `citations` | Fallback to `mockStore.askDemoQuestion` on failure | `lib/api.ts:317` |
| 2 | R1 (Chat) | Ollama Connectivity | Local private LLM server detection and model enumeration | `ollamaUrl` | `OllamaStatus` (`online`, `models`, `activeModel`, `latency_ms`) | Sets `online: false` with fallback | `lib/ollama.ts` |
| 3 | R2 (Vault) | Document Upload & Real-time SSE | Bulk file drop with live SSE status updates | `caseId`, `file`, `document_type` | `DemoDocument` / API document record | Shows error toast/banner, keeps originals safe | `(app)/cases/[caseId]/documents/page.tsx` |
| 4 | R2 (Vault) | Document Viewer & Translation | Multi-page text view with uncertainty chips `[UNCERTAIN: ...]` and on-demand translation | `docId`, `page`, `language` | Translated text, page explanation | Displays fallback explanation | `lib/legalTranslator.ts` |
| 5 | R2 (Vault) | Document Comparison | Pairwise/multi-doc cross-check with inline word-level diff | `caseId`, `documentIds` | Match/Mismatch/Missing verdict array with diffs | Shows missing fields error | `(app)/cases/[caseId]/comparison/page.tsx` |
| 6 | R5 (Contract) | Contract Analysis API | Clause extraction, obligation tracking, and 0-100 risk scoring | `caseId`, `full_text`, `title` | `ContractDocument` with extracted clauses, risks, recommendations | Fallback mock contract analysis | `lib/api.ts:554` |
| 7 | R5 (Contract) | Contract Redline API | Compares original and modified agreement text | `caseId`, `original_text`, `modified_text` | `RedlineChange[]` array with insertion/deletion/modifications | Fallback mock redline | `lib/api.ts:588` |
| 8 | R6 (Admin) | AI Usage Analytics | Token usage and cost tracking by workflow and agent | None | `totals`, `by_workflow`, `by_agent` stats | Displays demo usage stats | `(app)/admin/ai-usage/page.tsx` |
| 9 | R6 (Admin) | Audit Events | Immutable log of platform and matter actions | `limit`, `offset`, `action` | List of audit events with timestamp and JSON metadata | Displays demo audit trail | `(app)/admin/audit/page.tsx` |
| 10 | R7 (Property) | Property Fields & Verification Matrix | Property metadata with Document Verified badges | `caseId`, field edits | Verified property records with source page quotes | User-provided fallback badge | `(app)/cases/[caseId]/property/page.tsx` |
| 11 | R7 (Property) | Indian Land Area Converter | Converts Acre, Gunta, Cent, Bigha, Sq.Ft, Sq.Meter | Input string (e.g. "1 Acre 20 Guntas") | Standardized conversions across all units | Shows invalid format message | `(app)/cases/[caseId]/property/page.tsx:236` |
| 12 | R7 (Property) | Ownership Chain Graph | Evidenced chain of title relationships between parties | `caseId` | Nodes (`PERSON`, `PROPERTY`) and edges (`TRANSFERRED`, `INHERITED`, etc.) | Empty state with rebuild trigger | `(app)/cases/[caseId]/ownership/page.tsx` |
| 13 | R7 (Property) | Property Timeline | Chronological event history from registered deeds | `caseId` | Ordered timeline events with linked document evidence | Empty state prompt | `(app)/cases/[caseId]/timeline/page.tsx` |
| 14 | R7 (Property) | Title Search & Due Diligence Reports | Automated Title Search Report v2 generation with exports | `caseId` | Comprehensive multi-section report (Print PDF, Word `.doc`, Text `.txt`) | Displays generation error | `(app)/cases/[caseId]/reports/page.tsx` |
| 15 | Infrastructure | PWA & Offline Database | Service worker caching, IndexedDB offline sync, PWA install prompt | Browser events | Offline indicators, background sync queue | Transparent offline fallback | `lib/pwa.ts`, `lib/offline-db.ts` |

---

## 4. Edge Cases Observed & Behavior

| # | Feature | Input / Condition | Observed Behavior |
|---|---|---|---|
| 1 | Assistant Streaming | Network disconnect mid-stream | Stream reader catches error and automatically falls back to offline AI Reasoner (`mockStore.askDemoQuestion`) |
| 2 | Document Viewer | Historical damaged / faded stamp paper with low OCR confidence | Tokens are rendered with `[UNCERTAIN: ...]` tags and amber warning banner is displayed alerting user to verify against original stamp paper |
| 3 | Document Comparison | Comparing documents with contradictory survey numbers (e.g., Sy. No 124/3 vs 124/2) | Verdict marked as `MISMATCH`, renders inline diff with red strikethrough and emerald addition, quoting verbatim source text |
| 4 | Offline Mode | Backend API unreachable / localhost demo mode | `isDemoMode()` evaluates true, automatically redirects all queries to `mockStore.ts` and `aiEngine.ts` without throwing fatal UI errors |
| 5 | PWA Sync | Actions performed while device is offline | Saved in IndexedDB (`offline-db.ts`); `background-sync.ts` replays queued requests upon network reconnection |
| 6 | Auth Session | Supabase JWT token expires (401 response) | `api.request()` catches 401, attempts `supabase.auth.refreshSession()`, and automatically retries the failed request once |

---

## 5. UI Architecture & Design System Analysis

### Component Hierarchy
```
frontend/
├── app/
│   ├── (app)/
│   │   ├── layout.tsx             # Root authenticated shell (Sidebar, Header, PWA banners)
│   │   ├── dashboard/page.tsx     # Matter list, quick case creation, overview stats
│   │   ├── chat/page.tsx          # Universal Ollama AI Chatbot workspace
│   │   ├── settings/page.tsx      # Org members, RBAC roles, Ollama endpoint config
│   │   ├── admin/
│   │   │   ├── layout.tsx         # Platform admin sidebar & navigation
│   │   │   ├── page.tsx           # Admin overview & system health
│   │   │   ├── agent-runs/        # Historical agent executions & tool calls
│   │   │   ├── ai-usage/          # Token & cost analytics by workflow/agent
│   │   │   ├── audit/             # Immutable audit event stream
│   │   │   ├── cases/             # Global cases oversight
│   │   │   ├── jobs/              # Async job queue monitor (OCR, extraction)
│   │   │   ├── organizations/     # Tenant organizations list
│   │   │   └── users/             # Platform users & admin toggle
│   │   └── cases/[caseId]/
│   │       ├── page.tsx           # Matter summary home & activity stream
│   │       ├── documents/         # Document vault & viewer modal
│   │       ├── analysis/          # AI case analysis & entity relationship flow
│   │       ├── property/          # Property fields & land unit converter
│   │       ├── ownership/         # Ownership chain graph & evidence
│   │       ├── timeline/          # Chronological property timeline
│   │       ├── comparison/        # Side-by-side document comparison & diff
│   │       ├── risks/             # Risk & issue matrix with evidence
│   │       ├── research/          # Indian legal research intelligence
│   │       ├── questions/         # Case-grounded streaming legal Q&A
│   │       ├── drafting/          # Legal drafting studio & export
│   │       ├── reports/           # Due diligence & Title Search report generator
│   │       └── voice/             # Real-time voice legal assistant
│   ├── api/
│   │   ├── chat/route.ts          # Server-side chat handler
│   │   └── ollama/[...path]/      # Ollama reverse proxy
│   ├── login/page.tsx             # Authentication login
│   ├── signup/page.tsx            # Authentication signup
│   └── globals.css                # Tailwind v4 theme definitions
```

### Design System Tokens (Tailwind v4)
- **Colors:**
  - Background: `--color-bg: #0a0a0f`
  - Surfaces: `--color-bg-surface: #12121a`, `--color-bg-elevated: #1a1a2e`
  - Primary Accent: `--color-primary: #2563eb`, `--color-primary-hover: #1d4ed8`
  - Secondary Accent: `--color-accent: #7c3aed`
  - Functional: Success (`#10b981`), Warning (`#f59e0b`), Danger (`#ef4444`)
  - Typography: White text (`#ffffff`), Secondary text (`#94a3b8`), Muted text (`#64748b`)
  - Borders: `--color-border: #1e293b`, `--color-border-light: #334155`

---

## 6. Recommendations for Implementation Phase

1. **Review Tables UI (R3):** Implement interactive Review Table workspace in `(app)/cases/[caseId]/review/page.tsx` with dynamic custom column prompts, cell confidence score chips, clickable evidence popup, and Excel/CSV export.
2. **Visual Workflow Builder (R4):** Build no-code visual workflow designer in `(app)/workflows/page.tsx` connecting directly to the existing backend `AgentOrchestrator` pipelines.
3. **Contract Intelligence Workspace (R5):** Build dedicated contract workspace with 29+ clause viewer, 0-100 risk score breakdown, searchable Clause Library with fallback tiers, and redline visual diff editor.
4. **Shared Spaces & Link Expiry (R6):** Implement matter sharing modal with collaborator permissions, expiring links (1h/24h/7d), watermark overlay settings, and PII redaction preview.
5. **Interactive Land & Ownership Moat (R7):** Embed live State Land Portal query selector (MH, KA, TN, TG, GJ) and upgrade ownership chain list into an interactive visual graph with BSA 2023 evidence drawer.
