# Project: LegAIQ / Jurisiva AI — Enterprise Legal Intelligence Platform

## Architecture
- **Backend**: FastAPI (Python 3.11/3.12) with Pydantic v2, Celery task queue, LangGraph multi-agent orchestration, PaddleOCR + Tesseract Indic OCR engine.
- **Database & Storage**: PostgreSQL 15 / Supabase with Row Level Security (RLS), pgvector for semantic legal embeddings.
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide icons, SSE streaming client.
- **Security & Compliance**: Bharatiya Sakshya Adhiniyam (BSA) 2023 Section 63 electronic evidence compliance, DPDP Act 2023 PII auto-redaction (Aadhaar, PAN, GSTIN, IFSC), role-based access control, SHA-256 tamper-evident matter audit logs.

## Feature Inventory
| # | Feature | Description | Milestone | Status |
|---|---------|-------------|-----------|--------|
| 1 | 3-Mode Chat Workspace | Ask, Analyze, Draft modes with mode-specific system prompts & behavior | M1 | DONE |
| 2 | Real-time Streaming & Citations | SSE token streaming with clickable inline citations `[Doc: name, Pg: N]` | M1 | DONE |
| 3 | Multi-LLM Selection | Runtime switching (Claude 3.5, GPT-4o, DeepSeek R1, Ollama local) | M1 | DONE |
| 4 | India Context Toggle | Dedicated toggle injecting Indian statutes (BNS, BNSS, BSA, CPC, CrPC, RERA, IBC) | M1 | DONE |
| 5 | Dual-Pass Indic OCR & Viewer | PaddleOCR + Tesseract for 13 Indic languages with confidence layer | M2 | DONE |
| 6 | Multi-Format Document Ingestion | PDF, Scan, DOCX, XLSX parsing with CLAHE contrast & deskew preprocessing | M2 | DONE |
| 7 | Document Classification & Entity Ext | Auto-classification badges (Sale Deed, Partition, 7/12, RTC, Mutation) & parties | M2 | DONE |
| 8 | Side-by-Side Version Compare | Visual diffing across document versions with change highlight | M2 | DONE |
| 9 | Spreadsheet Review Tables Backend | Database tables & API endpoints for bulk prompt extraction across documents | M3 | DONE |
| 10 | Interactive Review Table UI | Handsontable/Ag-Grid style spreadsheet UI with dynamic prompt columns | M3 | DONE |
| 11 | Cell Evidence & Confidence Linking | Cell click popover jumping to exact document page/snippet with confidence chips | M3 | DONE |
| 12 | Review Table Export | One-click export to formatted Excel (.xlsx) and CSV with formula sanitization | M3 | DONE |
| 13 | Visual Workflow Builder Canvas | Drag-and-drop node graph canvas for chaining specialist legal agents | M4 | DONE |
| 14 | Workflow Execution Engine | Async execution engine with topological sort & SSE step-by-step progress | M4 | DONE |
| 15 | Specialist Agent Library | 6 pre-built agents (Due Diligence, Title Examiner, Risk Auditor, Litigation Strategist, Contract Reviewer, BSA Compliance) | M4 | DONE |
| 16 | 29+ Clause Extraction & Risk 0-100 | Clause extraction across standard & Indian clauses with risk severity rating | M5 | DONE |
| 17 | Clause Library & Fallback Tiers | Enterprise clause repository with Standard, Fallback, and Walkaway options | M5 | DONE |
| 18 | Playbook Deviation Analysis | Compare contracts against firm playbooks with automated deviation flags | M5 | DONE |
| 19 | Redline Visual Diff Editor | Redline suggestion engine with visual addition/deletion diff view | M5 | DONE |
| 20 | Matter Shared Spaces & Access Links | External collaboration spaces with 1h/24h/7d expiry, constant-time passcodes & rate-limiting | M6 | DONE |
| 21 | Dynamic Document Watermarking | Configurable watermarking on document download/view with viewer identity | M6 | DONE |
| 22 | Enterprise Cost/ROI Analytics | Token usage, cost per matter, time saved metrics, and billing breakdown | M6 | DONE |
| 23 | Indian PII Auto-Redaction | Auto-masking Aadhaar (Verhoeff D5), PAN, Passport, Voter ID, GSTIN, Bank A/C with preview | M6 | DONE |
| 24 | 5+ State Land Portal Connectors | Direct connectors for Mahabhulekh, Bhoomi, Dharani, AnyRoR, TNREGINET | M7 | DONE |
| 25 | 13-30 Yr Ownership Chain Graph | Interactive visual DAG of title flow, 3-color DFS cycle check & encumbrance separation | M7 | DONE |
| 26 | BSA 2023 Evidence Certification | Section 63 compliance hash generator, audit log, and 65B/63 certificate PDF | M7 | DONE |
| 27 | Indian Kanoon Legal Research | Integrated case law search with citation graph & judgment summaries | M7 | DONE |
| 28 | Comprehensive Zero-Regression Tests | Hermetic pytest, vitest, and E2E test suites with 100% pass rate | M8 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Assistant & Chat Workspace | Features 1-4: 3-mode switcher, streaming, inline citations, model select, India toggle | none | DONE |
| M2 | Secure Matter Vault & Indic OCR | Features 5-8: Dual-pass Indic OCR, DOCX/XLSX, classification badges, version compare | none | DONE |
| M3 | Spreadsheet Review Tables | Features 9-12: Backend schema, extraction APIs, interactive UI, evidence popover, export | M1, M2 | DONE |
| M4 | Workflow Builder & Multi-Agent | Features 13-15: Visual canvas, execution engine SSE, specialist agent library | M1, M2 | DONE |
| M5 | Contract Intelligence & Playbooks | Features 16-19: 29 clause types, risk 0-100, clause library, playbooks, redline diff | M2 | DONE |
| M6 | Shared Spaces, Command Center & PII | Features 20-23: Expiring links, watermarking, cost analytics, Indian PII redaction | M2 | DONE |
| M7 | India Property Moat & BSA 2023 | Features 24-27: 5 state portals, 13-30 yr ownership DAG, BSA 2023 cert, Kanoon search | M2 | DONE |
| M8 | E2E Testing & Verification Hardening | Feature 28: Full test runner, 4-tier test cases, coverage verification, zero regressions | M1-M7 | DONE |
