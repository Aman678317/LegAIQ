# E2E Test Infra: India Legal Intelligence OS (Jurisiva AI / LegAIQ)

## Test Philosophy
- Opaque-box, requirement-driven testing covering R1 through R5.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing (Tiers 1-4) + Adversarial Hardening (Tier 5).

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|-------------|:----------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | Groq Llama 3.3 70B & Multi-Model Gateway | R1 | 5 | 5 | ✓ | ✓ |
| 2 | Real-time SSE Token Streaming (Ask/Analyze/Draft/Research) | R1 | 5 | 5 | ✓ | ✓ |
| 3 | Elimination of Static/Canned Fallbacks | R1 | 5 | 5 | ✓ | ✓ |
| 4 | Matter-Centric Vault & Persistent Case Memory | R2 | 5 | 5 | ✓ | ✓ |
| 5 | Interactive Strict Citation Grounding UI | R2 | 5 | 5 | ✓ | ✓ |
| 6 | Hybrid Vector & Full-Text Search RAG | R2 | 5 | 5 | ✓ | ✓ |
| 7 | Multi-Lingual Indic OCR (13 Languages) & Restoration | R3 | 5 | 5 | ✓ | ✓ |
| 8 | Land Record Parsing (7/12, 8A, Ferfar, CTS) & Bigha Normalization | R3 | 5 | 5 | ✓ | ✓ |
| 9 | 13–30 Year Title Reconstruction DAG & Cycle/Gap Detection | R3 | 5 | 5 | ✓ | ✓ |
| 10 | BSA 2023 Section 63 Electronic Evidence SHA-256 Certificates | R3 | 5 | 5 | ✓ | ✓ |
| 11 | 6 Specialized Legal Workflow Agents | R4 | 5 | 5 | ✓ | ✓ |
| 12 | Contract Reviewer (36 Clause Types & Playbook Deviation) | R4 | 5 | 5 | ✓ | ✓ |
| 13 | Statutory Court-Ready PDF/DOCX/XLSX Export Engine | R4 | 5 | 5 | ✓ | ✓ |
| 14 | Supabase Multi-Tenant RLS & ACL Policies | R5 | 5 | 5 | ✓ | ✓ |
| 15 | Verhoeff Aadhaar & 15+ Indian PII Redaction Engine | R5 | 5 | 5 | ✓ | ✓ |
| 16 | SSRF & DNS Rebinding Defenses | R5 | 5 | 5 | ✓ | ✓ |
| 17 | 100% Hermetic Backend & Frontend Test Passing (0 TS Errors) | R5 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Backend Test Suite: Pytest hermetic test runner (`pytest`) using `backend/tests/conftest.py` with `FakeSupabase` and `FakeOCRProvider`.
- Frontend Test Suite: Vitest with `happy-dom` (`npm test`) and TypeScript strict compilation (`npx tsc --noEmit`).
- E2E Test Suite Runner: Opaque-box integration test harness verifying API endpoints, SSE streams, legal calculations, and export formatting.

## Coverage Thresholds
- Tier 1: ≥5 tests per feature (85+ tests)
- Tier 2: ≥5 tests per feature (85+ tests)
- Tier 3: Pairwise coverage of major feature interactions (17+ tests)
- Tier 4: Realistic legal case workload scenarios (10+ scenarios)
- Total E2E test target: ~200+ comprehensive automated tests
