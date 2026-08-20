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
