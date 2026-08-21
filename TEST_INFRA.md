# E2E Test Infra: LegAIQ / Jurisiva AI

## Test Philosophy
- Opaque-box, requirement-driven, multi-tier testing.
- Hermetic test harness for backend pytest with zero network/database dependencies.
- Browser/Happy-DOM simulated test harness for frontend Vitest.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 (Unit/Feature) | Tier 2 (Boundary/Edge) | Tier 3 (Cross-Module) | Tier 4 (Real-World) |
|---|---------|--------|:---------------------:|:----------------------:|:---------------------:|:-------------------:|
| 1 | Multi-Tenant Org & Auth | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 2 | Case Management | R1 | ✓ | ✓ | ✓ | ✓ |
| 3 | Document Ingestion | R1 | ✓ | ✓ | ✓ | ✓ |
| 4 | Indic OCR (13 langs) | R1 | ✓ | ✓ | ✓ | ✓ |
| 5 | pgvector Semantic Search | R1 | ✓ | ✓ | ✓ | ✓ |
| 6 | Interactive Legal Chat | R1 | ✓ | ✓ | ✓ | ✓ |
| 7 | Document Comparison | R1 | ✓ | ✓ | ✓ | ✓ |
| 8 | Spreadsheet Review Tables | R2 | ✓ | ✓ | ✓ | ✓ |
| 9 | Clause Library (29+ types) | R1 | ✓ | ✓ | ✓ | ✓ |
| 10 | Contract Playbook Evaluation | R1 | ✓ | ✓ | ✓ | ✓ |
| 11 | Multi-Agent Orchestration | R1 | ✓ | ✓ | ✓ | ✓ |
| 12 | 6 Specialist Legal Agents | R1 | ✓ | ✓ | ✓ | ✓ |
| 13 | Rajora LLM Engine | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 14 | Multi-Provider AI Router | R1, R2 | ✓ | ✓ | ✓ | ✓ |
| 15 | BSA 2023 Section 63 Cert | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 16 | Title Search & Due Diligence | R1 | ✓ | ✓ | ✓ | ✓ |
| 17 | Legal Risk Categorization | R1 | ✓ | ✓ | ✓ | ✓ |
| 18 | Litigation Strategy (CPC/BNS) | R1 | ✓ | ✓ | ✓ | ✓ |
| 19 | Shared Spaces & Passcodes | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 20 | Single Sign-On (SSO) | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 21 | Indian PII Redaction | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 22 | SSRF Protection | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 23 | Voice & Audio Intake | R1 | ✓ | ✓ | ✓ | ✓ |
| 24 | Timeline & Chronology | R1 | ✓ | ✓ | ✓ | ✓ |
| 25 | Legal Research & Citation | R1 | ✓ | ✓ | ✓ | ✓ |
| 26 | Analytics & Audit Logs | R1, R4 | ✓ | ✓ | ✓ | ✓ |
| 27 | Celery / Sync Background Queue | R1, R2 | ✓ | ✓ | ✓ | ✓ |
| 28 | Statutory Export Engine | R1 | ✓ | ✓ | ✓ | ✓ |
| 29 | PWA & Offline Store | R1, R2 | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- **Backend Test Runner**: `python -m pytest backend/tests/ -v` (40 test files, 550+ tests).
- **Frontend Test Runner**: `cd frontend && npm test` (`npx vitest run`) (5 test files, 48 tests).
- **Test Fixtures**: In-memory `FakeSupabase`, `FakeOCRProvider`, Happy-DOM mocking.

## Real-World Workload Scenarios (Tier 4)
| # | Scenario | Features Exercised |
|---|----------|--------------------|
| 1 | Agricultural Land Title Due Diligence (30-yr chain, mutation gap, encumbrance) | F1, F2, F3, F4, F12, F16, F28 |
| 2 | Commercial Lease Agreement Review & Playbook Deviation Redlining | F1, F2, F7, F8, F9, F10, F12, F28 |
| 3 | BSA 2023 Section 63 Statutory Electronic Evidence Certification & Tamper-Proof Hash | F1, F2, F3, F12, F15, F26, F28 |
| 4 | Multi-Tenant Client Collaboration Shared Space with Passcode & Expiration | F1, F19, F21, F22, F26 |
| 5 | Indian PII Redaction across Aadhaar (Verhoeff), PAN, GSTIN, Bank Accounts | F1, F3, F21, F28 |
