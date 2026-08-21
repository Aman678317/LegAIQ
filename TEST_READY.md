# TEST_READY: India Legal Intelligence OS (Jurisiva AI / LegAIQ)

## Overview
The requirement-driven, opaque-box E2E test suite for the **India Legal Intelligence OS** is fully configured, validated, and ready for continuous regression and acceptance testing across Requirements **R1 through R5**.

The test architecture implements the full testing spectrum:
- **Tier 1 (Feature Coverage)**: ≥5 tests per feature covering representative inputs across all core modules.
- **Tier 2 (Boundary & Corner Cases)**: ≥5 boundary tests per feature (e.g., Verhoeff checksums, circular title conveyances, missing deed links, regional Bigha conversions, large files, Unicode script mixing, network timeouts, SSRF rebinding, cross-tenant RLS isolation).
- **Tier 3 (Cross-Feature Combinations)**: Pairwise integration pipelines verifying data flow across OCR, Land Records, Title DAG, BSA Section 63 Certification, Contract Review, PII Redaction, and Exporters.
- **Tier 4 (Real-World Enterprise Workloads)**: Complex multi-step realistic legal scenarios (30-year Maharashtra agricultural land title search, 20-lease commercial portfolio extraction with Excel export, M&A deal room clean room with 24h link expiry, High Court plaint drafting with CPC Order VII).

---

## Test Inventory & Mapping

| Tier | Focus | Requirement Mapping | Test File(s) | Test Count | Status |
|---|---|---|---|:---:|:---:|
| **Tier 1** | Chat & Assistant Intelligence (Ask, Analyze/FIRAC, Draft, SSE, Routing, Statutes) | R1 & R2 | `backend/tests/test_tier1_chat_assistant.py` | 24 | **PASS** |
| **Tier 1** | Document Intelligence & Indic OCR (13 Langs, Preprocessing, Extraction, Diffing) | R3 | `backend/tests/test_tier1_document_intelligence.py` | 20 | **PASS** |
| **Tier 1** | Review Tables & Extraction (Schema, Confidence, BBox, OpenXML XLSX, CSV) | R4 | `backend/tests/test_tier1_review_tables.py` | 20 | **PASS** |
| **Tier 1** | Workflow Engine & Specialist Agents (Canvas, DAG sort, 6 Legal Agents, Kill Switch) | R4 | `backend/tests/test_tier1_workflows_agents.py` | 20 | **PASS** |
| **Tier 1** | Contract Intelligence (29/36 Clauses, Risk 0-100, Library, Playbooks, Redlines) | R4 | `backend/tests/test_tier1_contracts.py` | 23 | **PASS** |
| **Tier 1** | Enterprise Controls & Indian PII (Shared Spaces, Watermarking, ROI, 15+ PII) | R5 | `backend/tests/test_tier1_enterprise_pii.py` | 23 | **PASS** |
| **Tier 1** | Property Moat, BSA 2023 & Kanoon (5 Portals, 30-Yr DAG, BSA Sec 63, Research) | R3 | `backend/tests/test_tier1_property_bsa_kanoon.py` | 22 | **PASS** |
| **Tier 2** | Boundary Value Analysis & Corner Cases (10 Categories, Checksums, Cycles, SSRF) | R1–R5 | `backend/tests/test_tier2_boundaries.py` | 44 | **PASS** |
| **Tier 3** | Cross-Feature Interactions & Pairwise Multi-Module Pipelines (7 Pipelines) | R1–R5 | `backend/tests/test_tier3_interactions.py` | 7 | **PASS** |
| **Tier 4** | Real-World Enterprise Workload Scenarios (7 Full Scenarios) | R1–R5 | `backend/tests/test_tier4_workloads.py` | 7 | **PASS** |
| **Component** | Core Unit & Subsystem Test Suites (DAG, BSA, Kanoon, Portals, RLS, PII, SSRF) | R1–R5 | `backend/tests/test_*.py` (27 additional test files) | 160+ | **PASS** |
| **Total** | **Comprehensive E2E Test Suite** | **R1–R5** | **37 Test Files** | **370+ Tests** | **100% READY** |

---

## Test Execution Guide

### 1. Prerequisites
Ensure Python 3.11+ and project dependencies are installed:
```powershell
cd "backend"
pip install -r requirements.txt
```

### 2. Running the Complete Hermetic Test Suite
Run all Pytest test files using the hermetic test fixtures (`FakeSupabase` and `FakeOCRProvider`):
```powershell
pytest backend/tests -v
```

### 3. Running by Tier
To run specific test tiers:

```powershell
# Tier 1: Core Feature Coverage
pytest backend/tests/test_tier1_*.py -v

# Tier 2: Boundary Value Analysis & Edge Cases
pytest backend/tests/test_tier2_boundaries.py -v

# Tier 3: Cross-Feature Interactions & Pairwise Pipelines
pytest backend/tests/test_tier3_interactions.py -v

# Tier 4: Real-World Workload Scenarios
pytest backend/tests/test_tier4_workloads.py -v
```

### 4. Running Critical Acceptance & Pipeline Tests
```powershell
# Full E2E Pipeline Acceptance Test
pytest backend/tests/test_e2e_pipeline.py -v

# BSA 2023 Section 63 Certification & Presumption Tests
pytest backend/tests/test_bsa_section63.py backend/tests/test_bharatiya_sakshya.py -v

# Ownership Chain DAG & Cycle Detection
pytest backend/tests/test_ownership_chain_dag.py -v

# Indian PII Verhoeff Redaction Engine
pytest backend/tests/test_pii.py -v

# SSRF Dual-Layer Defense Guard
pytest backend/tests/test_ssrf.py -v
```

### 5. Running Frontend Tests & Type Checking
```powershell
cd "frontend"
npm test
npx tsc --noEmit
```

---

## Requirement Coverage Matrix

### R1. Live Multi-Model AI Gateway & High-Speed Reasoning
- [x] Sub-600ms Groq LPU (Llama 3.3 70B) provider mapping and dynamic fallback routing across OpenAI, Anthropic, Ollama, and Mock.
- [x] Elimination of static canned fallbacks; prompt structures enforce structured FIRAC reasoning.
- [x] Server-Sent Events (SSE) token streaming across Ask, Analyze, Draft, and Research modes.
- *Verified in:* `test_tier1_chat_assistant.py`, `test_tier2_boundaries.py`, `test_tier3_interactions.py`.

### R2. Matter-Centric Vault & Evidence Workspace
- [x] Persistent case memory with case facts grounding tool and agent executions.
- [x] Strict interactive citation grounding linking findings to `[Doc: name, Pg: N]` with metadata.
- [x] Hybrid pgvector cosine similarity + full-text keyword RAG search.
- *Verified in:* `test_tier1_chat_assistant.py`, `test_milestones_m1_m2.py`, `test_tier3_interactions.py`, `test_e2e_pipeline.py`.

### R3. Indian Document Intelligence & Property Title Engine
- [x] Multi-lingual OCR & VLM supporting 13 Indian languages (Hindi, Kannada, Marathi, Tamil, Telugu, etc.).
- [x] Historical document preprocessing (CLAHE contrast enhancement, deskewing, red/purple seal detection).
- [x] Revenue land record parsing for 7/12 extracts, 8A, Ferfar mutation entries, CTS property cards, and RTC Pahani.
- [x] Regional Bigha unit normalization across states (UP Pucca, Gujarat, Bengal, Assam, etc.) to square meters.
- [x] 13–30 year title ownership reconstruction DAG with circular conveyance DFS cycle detection and mutation gap alerts.
- [x] BSA 2023 Section 63 Electronic Evidence Certification with SHA-256 tamper-evident sealing, Section 94 (30-yr presumption), and Section 97 (certified copy presumption).
- *Verified in:* `test_tier1_document_intelligence.py`, `test_tier1_property_bsa_kanoon.py`, `test_ownership_chain_dag.py`, `test_bsa_section63.py`, `test_tier4_workloads.py`.

### R4. Specialized Legal Workflow Agents & Litigation Suite
- [x] 6 Specialized legal workflow agents: Due Diligence, Title Examiner, Contract Reviewer, Litigation Strategist, BSA Compliance, and Legal Research.
- [x] Contract Intelligence Engine: 29/36 clause extraction, 0-100 risk scoring, clause library with standard/fallback/walkaway tiers, and playbook deviation analysis.
- [x] Redline Visual Diff engine detecting insertions, deletions, modifications, and generating tracked changes.
- [x] Court-ready statutory export engine generating native vector PDF, Word DOCX, OpenXML Excel .xlsx review tables, and CSV.
- *Verified in:* `test_tier1_workflows_agents.py`, `test_tier1_contracts.py`, `test_tier1_review_tables.py`, `test_tier3_interactions.py`, `test_tier4_workloads.py`.

### R5. Security, DPDP Compliance & Production Hardening
- [x] Multi-tenant organization isolation and Row Level Security (RLS) policies.
- [x] Verhoeff checksum validation for Aadhaar and detection of 15+ Indian PII entity types across 5 redaction strategies (Mask, Replace, Hash, Remove, Pseudonymize).
- [x] Dual-layer SSRF protection with IP range validation, private IP blocking, cloud metadata blocking, and DNS rebinding defense.
- *Verified in:* `test_tier1_enterprise_pii.py`, `test_ssrf.py`, `test_pii.py`, `test_tier2_boundaries.py`.
