# E2E Test Infra: LegAIQ / Jurisiva AI Enterprise Legal Intelligence

## Test Philosophy
- Opaque-box, requirement-driven testing covering all 7 core legal intelligence domains.
- Fully hermetic in-memory execution (zero flaky network / external cloud dependencies).
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinations + Real-World Workload Scenarios.

## Feature Inventory & Test Coverage Mapping
| # | Feature | Requirement | Tier 1 (Isolated) | Tier 2 (Boundaries) | Tier 3 (Interactions) | Tier 4 (Workloads) |
|---|---------|-------------|:-----------------:|:-------------------:|:---------------------:|:-------------------:|
| 1 | 3-Mode Chat (Ask/Analyze/Draft) | R1 | 5 | 5 | ✓ | ✓ |
| 2 | Streaming & Inline Citations | R1 | 5 | 5 | ✓ | ✓ |
| 3 | Multi-LLM Selection | R1 | 5 | 5 | ✓ | ✓ |
| 4 | India Context Toggle & Statutes | R1 | 5 | 5 | ✓ | ✓ |
| 5 | Dual-Pass Indic OCR (13 languages) | R2 | 5 | 5 | ✓ | ✓ |
| 6 | Multi-format Parsing (PDF/DOCX/XLSX) | R2 | 5 | 5 | ✓ | ✓ |
| 7 | Classification & Entity Extraction | R2 | 5 | 5 | ✓ | ✓ |
| 8 | Side-by-Side Version Diffing | R2 | 5 | 5 | ✓ | ✓ |
| 9 | Review Tables Backend & Extraction | R3 | 5 | 5 | ✓ | ✓ |
| 10 | Interactive Review Table UI | R3 | 5 | 5 | ✓ | ✓ |
| 11 | Cell Evidence & Confidence Linking | R3 | 5 | 5 | ✓ | ✓ |
| 12 | Review Table Excel/CSV Export | R3 | 5 | 5 | ✓ | ✓ |
| 13 | Visual Workflow Canvas | R4 | 5 | 5 | ✓ | ✓ |
| 14 | Workflow Execution Engine & SSE | R4 | 5 | 5 | ✓ | ✓ |
| 15 | Specialist Agent Library | R4 | 5 | 5 | ✓ | ✓ |
| 16 | 29 Clause Extraction & Risk 0-100 | R5 | 5 | 5 | ✓ | ✓ |
| 17 | Clause Library & Fallback Tiers | R5 | 5 | 5 | ✓ | ✓ |
| 18 | Playbook Deviation Scoring | R5 | 5 | 5 | ✓ | ✓ |
| 19 | Redline Visual Diff Editor | R5 | 5 | 5 | ✓ | ✓ |
| 20 | Shared Spaces & Access Links | R6 | 5 | 5 | ✓ | ✓ |
| 21 | Dynamic Document Watermarking | R6 | 5 | 5 | ✓ | ✓ |
| 22 | Enterprise Cost & ROI Analytics | R6 | 5 | 5 | ✓ | ✓ |
| 23 | Indian PII Auto-Redaction | R6 | 5 | 5 | ✓ | ✓ |
| 24 | 5+ State Land Portal Connectors | R7 | 5 | 5 | ✓ | ✓ |
| 25 | 13-30 Yr Ownership Chain Graph | R7 | 5 | 5 | ✓ | ✓ |
| 26 | BSA 2023 Section 63 Certification | R7 | 5 | 5 | ✓ | ✓ |
| 28 | Comprehensive Zero-Regression Tests | M8 | 5 | 5 | ✓ | ✓ |
| 29 | Rajora AI Private LLM & Key RLS | R1-R7 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Backend Test Runner**: `pytest tests/ -v` (with async pytest, FastAPI TestClient, and hermetic SQLite/in-memory state)
- **Frontend Test Runner**: `npm run test` or `npx vitest run` / `npx playwright test`
- **E2E Integration Harness**: `tests/e2e/` testing full cross-module workflows (Chat -> Vault -> Review Tables -> Workflow -> Contracts -> Property -> Shared Space).

### Supabase RLS Negative Testing (Migration 014 — rajora_llm_keys)
To verify tenant isolation on `rajora_llm_keys`:
1. As User A (belonging to Org A), insert an API key row scoped to Org A.
2. Authenticate as User B (belonging to Org B, non-admin). Attempt a `SELECT * FROM rajora_llm_keys WHERE org_id = 'Org A ID'`.
3. Assert that zero rows are returned (`users read own rajora keys` policy enforces `user_id = auth.uid()`).
4. Authenticate as Admin of Org B. Attempt to update or delete User A's key in Org A.
5. Assert update fails or affects 0 rows (`org admins manage rajora keys` policy enforces `public.can_manage_org(org_id)` where `org_id` must match Org B).

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Agricultural Land Title Due Diligence (Karnataka/Maharashtra) | F5, F7, F24, F25, F26, F15 | 30-year ownership DAG with break alerts, 7/12 & RTC validation, BSA 63 certificate generated |
| 2 | High-Volume Commercial Lease Review | F6, F9, F10, F11, F12, F16, F18 | 20-lease extraction table, prompt columns, risk scores, redlines vs firm playbook, Excel export |
| 3 | M&A Regulatory & PII Redaction Deal Room | F20, F21, F23, F22, F7 | Shared space creation with 24h expiry, Aadhaar/PAN auto-masked, dynamic viewer watermark, ROI tracked |
| 4 | Multi-Agent Litigation Strategy Formulation | F1, F2, F4, F13, F14, F15, F27 | Visual canvas agent chaining, Indian Kanoon case retrieval, Draft mode petition with citations |
| 5 | Cross-Border Software SaaS Master Services Agreement | F16, F17, F18, F19, F1, F3 | 29 clause classification, fallback tier substitution, side-by-side redline diffing, audit logging |
| 6 | Sovereign Legal Reasoning with Zero Data Egress | F1, F3, F4, F26, F29 | Private inference via RajoraProvider, SHA-256 key audit, $0 marginal cost telemetry, local fallback |
