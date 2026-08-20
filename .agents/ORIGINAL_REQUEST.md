# Original User Request

## Initial Request — 2026-08-20T02:17:59+05:30

Transform LegAIQ / Jurisiva AI into an enterprise-grade legal intelligence platform with Harvey-class capabilities (Assistant, Vault, Review Tables, Workflow Agents, Workflow Builder, Knowledge, Contract Intelligence, Clause Library, Playbooks, Shared Spaces, and Command Center) while preserving and strengthening its India-first moats (28+ state land portals, 12+ Indic languages, 15+ regional land record formats, and Bharatiya Sakshya Act compliance).

Working directory: c:\Users\acer\OneDrive\inga legal
Integrity mode: development

## Requirements

### R1. Assistant & Chat Workspace
Implement a unified legal Assistant workspace supporting Ask, Analyze, and Draft modes with streaming output, inline clickable citations [Doc: name, Pg: N], multi-model selection (Ollama 70B, Claude 3.5, GPT-4o, DeepSeek R1), and an India Context toggle for state-specific terminology and statutory reasoning.

### R2. Secure Matter Vault & Document Intelligence
Implement a matter-centric document intelligence Vault supporting bulk uploads (PDF, DOCX, XLSX, images), dual-pass OCR (Tesseract + PaddleOCR with 12+ Indic languages), historical deed preprocessing, automatic classification (Sale Deed, Partition, 7/12, RTC, Mutation, Court Orders), entity extraction, and version comparison.

### R3. Spreadsheet-Style Review Tables
Implement an interactive Review Table workspace for bulk structured extraction across matter documents with customizable prompt-driven extraction columns, cell-level evidence linking, confidence scores, and CSV/Excel export.

### R4. Multi-Agent Orchestration & Workflow Builder
Implement an agent orchestration layer with specialist agents (Legal Research, Contract Review, Due Diligence, Title Search, Citation Auditor) and a no-code visual Workflow Builder with triggers, step templates, test runs, and execution logs.

### R5. Contract Intelligence, Clause Library & Playbooks
Implement contract analysis with 29+ clause types extraction, risk scoring (0-100), playbook deviation detection, redline side-by-side diffing, a searchable Clause Library with fallback language guidelines, and negotiation Playbooks.

### R6. Shared Spaces, Command Center & Enterprise Controls
Implement matter-level Shared Spaces with collaborator permissions, watermarking, and expiring links; Command Center analytics for AI costs, token usage, and turnaround velocity; and PII auto-redaction for Indian identifiers (Aadhaar, PAN, GST, IFSC).

### R7. India-First Property & Legal Moat
Preserve and extend connectors for 5+ major state land portals (Mahabhulekh, Bhoomi, TNREGINET, Dharani, AnyROR), 13–30 year property ownership chain graph generation, Bharatiya Sakshya Adhiniyam 2023 evidence rules, and Indian Kanoon research.

## Acceptance Criteria

### Assistant & Streaming
- [ ] Assistant streams responses in real time with model selection and reasoning depth.
- [ ] All legal assertions contain source grounding and citations.

### Review Tables & Extraction
- [ ] Users can create custom columns, define extraction prompts, and extract structured data across multiple documents.
- [ ] Every cell displays extracted value, confidence score, and clickable source snippet evidence.

### Agents & Workflows
- [ ] Specialist agents execute multi-step legal tasks with transparent tool call logs.
- [ ] Workflow builder allows assembling and executing multi-step legal pipelines.

### Contract Intelligence & Redlining
- [ ] Contract review extracts clauses, scores risks, and flags missing/deviating clauses against playbooks.
- [ ] Redline engine generates tracked changes between contract versions.

### Quality & Regression
- [ ] All existing backend (pytest) and frontend (vitest / Playwright) test suites continue to pass without regression.
- [ ] Responsive UI/UX with PWA offline service worker and mobile compatibility.

## Follow-up — 2026-08-20T10:27:21+05:30

Expand the existing LegAIQ / Jurisiva AI production codebase into an enterprise-grade, Harvey-class legal AI platform tailored for the Indian legal market, preserving all existing capabilities and strengthening India-first moats (land records, Indic OCR, title graphs, DPDP, Bharatiya Sakshya).

Working directory: c:\Users\acer\OneDrive\inga legal
Integrity mode: demo

## Requirements

### R1. Harvey-Class Core Workspaces (Assistant, Vault, Review Tables, Agents & Workflows)
- Enhance and unify the Assistant workspace supporting 3 primary modes (Ask, Analyze, Draft) with multi-model routing, reasoning depth control, inline clickable citation chips `[Doc: name, Pg: N]`, and an evidence panel.
- Expand Matter Vaults into a hierarchical intelligence system (Organization → Matter → Vault → Folder → Document → Version → Analysis) supporting bulk multi-format ingestion (PDF, DOCX, XLSX, scans), OCR classification, duplicate detection, and source provenance.
- Deliver Review Tables for spreadsheet-style natural-language batch field extraction across large document sets, storing cell-level confidence, bounding box / character offsets, model versions, and reviewer status with XLSX/CSV export.
- Implement an Agent Orchestration framework with durable state transitions (Planner → Task Graph → Specialist Agents → Tools → Evidence Store → Reviewer/Validator → Final Composer) featuring specialist agents (Legal Research, Contract Review, Due Diligence, Title Search, Drafting, Translation, Evidence Validator, Citation Auditor, PII Redaction).
- Build a no-code Workflow Builder supporting trigger-to-export automation templates, versioning, DAG validation, approval checkpoints, and execution history.

### R2. Contract Intelligence, Clause Library & Knowledge Systems
- Expand Contract Intelligence to extract 29+ legal clause types, compute 0–100 risk scores, identify missing/unusual clauses, detect playbook deviations, generate side-by-side redline diffs, and suggest fallback language.
- Build a searchable Clause Library & Playbook Builder with exact and semantic search, fallback tiers, risk ratings, and versioned precedent management.
- Implement a first-class Indian Legal Knowledge repository organizing Supreme Court judgments, High Courts, Central/State statutes, circulars, and tribunal decisions with citation validation.

### R3. Enterprise Security, Governance, Integrations & India Moat Superpowers
- Implement enterprise security and governance: SAML/OIDC SSO, SCIM provisioning, RBAC, tenant isolation, immutable audit logging, dynamic watermarking, and multi-mode PII auto-redaction (display, export, AI-context, permanent) for Indian identifiers (Aadhaar, PAN, GSTIN, IFSC).
- Build Shared Spaces with external collaborator isolation, access expiration, download restrictions, and audit logs.
- Provide a Command Center analytics dashboard tracking usage KPIs, matter costs, model routing metrics, turnaround times, and citation acceptance rates without exposing sensitive content.
- Build public REST/WebSocket/SSE APIs, Webhook event notification system, and connectors framework (Word, Outlook, Google Drive, SharePoint, DMS).
- Deepen India differentiation: 28+ state land portal connectors, 13 Indic language OCR/transliteration, 13–30 year ownership chain graph reconstruction, mutation analysis, and Bharatiya Sakshya Act (BSA 2023) Section 63/94/97 digital evidence certification.

## Verification Resources

- Existing test suite located in `backend/tests/` comprising 4 verification tiers:
  - Tier 1: Isolated feature coverage across all 27 core capabilities (`test_tier1_*.py`)
  - Tier 2: Boundary value analysis, 0-byte uploads, bad PII, cyclic DAGs, and tenant isolation (`test_tier2_boundaries.py`)
  - Tier 3: Multi-stage pipeline interactions (`test_tier3_interactions.py`)
  - Tier 4: Real-world enterprise workload scenarios (`test_tier4_workloads.py`)
- Frontend unit/store test specs (`frontend/src/**/*.test.ts`, `tier_comprehensive.test.ts`).

## Acceptance Criteria

### Platform Integrity & Backward Compatibility
- [ ] No existing backend models, API routes, or frontend components are deleted or replaced with stubbed code.
- [ ] Existing functionality (authentication, case management, RAG pipeline, billing, PWA) remains fully operational.
- [ ] The existing 4-tier hermetic test suite (`backend/tests/`) continues to pass with 100% genuine assertions.

### Core Workspace Capabilities
- [ ] Assistant executes Ask/Analyze/Draft flows with streamed responses and verifiable citation chips linked to evidence snippets.
- [ ] Vault correctly ingests, categorizes, and indexes multi-format documents and land records with full provenance metadata.
- [ ] Review Tables successfully extract dynamic prompt-defined columns across document batches, displaying cell confidence and source offsets.
- [ ] Agent Orchestrator manages task graphs across specialist agents with tool permissions, budget limits, and audit history.
- [ ] Workflow Builder correctly creates, validates (DAG cycle check), executes, and versions multi-step legal automations.

### Contract, Knowledge & Enterprise Governance
- [ ] Contract Intelligence extracts clauses, computes risk scores (0–100), detects playbook deviations, and generates redline diffs.
- [ ] Clause Library enables exact and semantic search across clauses with fallback tiers.
- [ ] Indian PII engine automatically redacts Aadhaar, PAN, and GSTIN across AI-context and export modes.
- [ ] 13–30 year property ownership chain graph reconstructs transaction timelines and produces BSA Section 63 compliance certificates.
- [ ] Command Center displays aggregated telemetry and usage metrics without leaking raw client documents.

