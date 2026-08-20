## 2026-08-20T02:25:30Z
You are teamwork_preview_worker for Milestone 1 & 2: Assistant & Chat Workspace + Secure Matter Vault & Indic Document Intelligence.
Your working directory is: c:\Users\acer\OneDrive\inga legal\.agents\worker_m1_m2_flash
You MUST read: c:\Users\acer\OneDrive\inga legal\.agents\ORIGINAL_REQUEST.md
Also read: c:\Users\acer\OneDrive\inga legal\PROJECT.md and c:\Users\acer\OneDrive\inga legal\TEST_INFRA.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope and Deliverables:
1. Milestone 1 (R1): Assistant & Chat Workspace:
   - Unified 3-mode switcher: Ask (Q&A), Analyze (deep legal reasoning), Draft (motions, petitions, clauses, notices).
   - Real-time SSE streaming with inline clickable citations `[Doc: filename, Pg: N]` linking directly to document viewer.
   - Multi-LLM runtime model selector (Claude 3.5 Sonnet, GPT-4o, DeepSeek R1, Ollama local).
   - Dedicated India Context Toggle: automatically injects relevant Indian statutes (BNS, BNSS, BSA 2023, CPC, CrPC, RERA, IBC) into prompt grounding.
2. Milestone 2 (R2): Secure Matter Vault & Indic Document Intelligence:
   - Dual-pass OCR viewer supporting 13 Indic scripts + English with confidence scoring layer and OCR toggle.
   - Multi-format ingestion (PDF, scanned images, DOCX, XLSX) with CLAHE contrast enhancement and deskew preprocessing.
   - Automatic Indian legal document classification badges (Sale Deed, Partition Deed, 7/12 Extract, RTC, Mutation Register, Gift Deed, Lease Deed) and party/entity extraction.
   - Side-by-side visual version comparison with diff highlights.
3. Verification:
   - Run backend tests and frontend tests for affected modules.
   - Write comprehensive implementation & test report in `c:\Users\acer\OneDrive\inga legal\.agents\worker_m1_m2_flash\handoff.md`.
   - Send completion message to parent when finished.
