# Original User Request

## 2026-08-21T17:31:06Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team

Build and harden the complete **India Legal Intelligence OS** (Jurisiva AI / LegAIQ) — a full-scale, production-ready, ultra-fast Harvey-class Legal AI platform for India grounded in Indian statutes (BNS, BNSS, BSA 2023, CPC, Income Tax Act, RERA, Companies Act), land records (7/12, 8A, Ferfar, Property Cards), and court workflows.

Working directory: `C:\Users\acer\OneDrive\inga legal`
Integrity mode: development

---

## Requirements

### R1. Live Multi-Model AI Gateway & High-Speed Legal Reasoning
- Implement an AI Gateway routing queries dynamically across **Groq LPU (Llama 3.3 70B)** for sub-second responses, **OpenAI (GPT-4o / GPT-4o-mini)**, **Anthropic (Claude 3.5 Sonnet)**, and **Local Ollama**.
- Eliminate all static mock/canned fallbacks repository-wide — every feature must generate deep, nuanced, realistic, and context-aware responses.
- Deliver real-time Server-Sent Events (SSE) streaming for all interaction modes: **Ask** (Direct Q&A), **Analyze** (Deep FIRAC legal reasoning & issue spotting), **Draft** (Court petitions, notices, contracts), and **Research** (Statutory memorandums).

### R2. Matter-Centric Vault & Evidence Workspace (Harvey Architecture)
- Unify the platform under the north star: *"One matter, one workspace, one evidence graph, many agents"*.
- Implement persistent matter memory so the active client, jurisdiction, document collection, and case facts automatically ground every agent and tool execution without redundant user prompting.
- Enforce strict citation grounding: every legal finding, risk, or statutory claim must link to a verified source class with document name, page number, and source passage.

### R3. Indian Document Intelligence & Property Title Engine
- Provide multi-lingual OCR and VLM parsing supporting 13 Indian languages with automated image restoration (CLAHE/deskew) for historical and degraded deed records.
- Support deep parsing and entity extraction for Indian property records: **7/12, 8A, Ferfar (Mutation entries), Property Cards, CTS survey numbers**, and registered deed chains.
- Automate 13–30 year title ownership reconstruction, mutation gap detection, boundary mismatch identification, encumbrance auditing, and generation of **BSA 2023 Section 63 Electronic Evidence Certificates** with SHA-256 tamper-evident sealing.

### R4. Specialized Legal Workflow Agents & Litigation Suite
- Implement 6 specialized workflow agents:
  1. **Due Diligence Agent**: Complete title search, encumbrance verification, and risk profiling.
  2. **Title Examiner**: Multi-deed chain reconciliation and boundary validation.
  3. **Contract Reviewer**: 29+ legal clause extraction, deviation scoring, and playbook evaluation.
  4. **Litigation Strategist**: Cause of action analysis under CPC / BNS / BNSS and limitation period calculations.
  5. **BSA Compliance Agent**: Section 63 certificate generation and admissibility auditing.
  6. **Legal Research Agent**: Precedent retrieval and statutory analysis with direct eCourts & Indian Kanoon citations.
- Provide statutory export engine generating court-ready PDF, DOCX, and Excel review tables.

### R5. Security, DPDP Compliance & Production Hardening
- Enforce matter-level Access Control Lists (ACL), organization-scoped Row Level Security (RLS) across all Supabase PostgreSQL tables, and ethical wall boundaries.
- Implement Verhoeff-verified Indian PII redaction (Aadhaar, PAN, Bank details) and dual-layer SSRF protection with DNS rebinding defenses.
- Verify 100% pass rate on all backend Pytest hermetic suites and frontend Vitest suites with zero TypeScript compilation errors.

---

## Acceptance Criteria

### Performance & Response Quality
- [ ] Direct chat and case questions respond via Groq Llama 3.3 70B with first-token latency under 600ms.
- [ ] No query produces identical, canned, or hardcoded dummy templates under any scenario.
- [ ] All legal answers include structured FIRAC analysis, statutory section citations, and binding Supreme Court / High Court precedents.

### Feature Completeness
- [ ] Universal AI Chatbot, Case Matter Workspace, Review Tables, Contract Playbooks, and Title Due Diligence operate seamlessly with live AI.
- [ ] Document comparison correctly highlights discrepancies across uploaded deeds with side-by-side evidence inspection.
- [ ] Full export to PDF/DOCX generates properly formatted legal filings with disclaimers.

### Security & Integrity
- [ ] Zero secrets, API keys, or private tokens committed to git.
- [ ] RLS policies isolate tenant data by `organization_id` and `auth.uid()`.
- [ ] Backend test suite (`pytest`) and frontend test suite (`vitest`) pass with 0 errors.
