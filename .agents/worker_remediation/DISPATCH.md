## 2026-08-19T21:12:00Z

<USER_REQUEST>
You are teamwork_preview_worker for Challenger Remediation & Platform Hardening.
Your working directory is: c:\Users\acer\OneDrive\inga legal\.agents\worker_remediation
You MUST read: c:\Users\acer\OneDrive\inga legal\.agents\ORIGINAL_REQUEST.md
Also read: c:\Users\acer\OneDrive\inga legal\PROJECT.md, c:\Users\acer\OneDrive\inga legal\TEST_INFRA.md, and c:\Users\acer\OneDrive\inga legal\TEST_READY.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Remediation Tasks based on Challenger 1 & 2 Findings:
1. `backend/app/ai/state_portals.py`: Add connector class aliases (`MahabhulekhConnector = MaharashtraPortal`, `BhoomiConnector = KarnatakaPortal`, `TNREGINETConnector = TamilNaduPortal`, `DharaniConnector = TelanganaPortal`, `AnyRoRConnector = GujaratPortal`, and `StatePortalFactory.get_connector`).
2. `backend/app/ai/bharatiya_sakshya.py`:
   - Make `check_section94_presumption` polymorphic so it accepts an `EvidenceItem`, a `datetime`, or an integer year.
   - Make `generate_section63_certificate` accept both positional and keyword argument variations gracefully.
3. `backend/app/ai/ownership_graph.py`:
   - Harden `OwnershipChainAnalyzer` with institution/lender-specific mortgage matching (track active encumbrances by lender/bank).
   - Implement directed cycle detection (DFS/Tarjan) to catch circular title transfers (e.g. A -> B -> C -> A) and report `CIRCULAR_TRANSFER_DETECTED` with `title_status = "DEFECTIVE"`.
   - Separate encumbrance/mortgage events from title ownership conveyance chains so mortgages don't cause false title break alerts.
4. `backend/app/api/bsa.py`: Add deterministic ordering (`.order("id")` or sorting by ID/hash) to document list for master audit hash generation.
5. `backend/app/ai/review_tables.py`: In `ReviewTableExporter.export_csv`, sanitize formula injection prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`) by prepending `'` to cell values.
6. `backend/app/api/workflows.py`: Ensure `_run_workflow_async` executes nodes in `_topological_sort(workflow.definition.nodes, workflow.definition.edges)` order rather than arbitrary dictionary order.
7. `backend/app/ai/contract_intelligence.py`: Broaden post-termination non-compete detection phrases to match subtle variations ("upon cessation of services", "following departure", "subsequent to disassociation", "following termination of employment").
8. `backend/app/api/shared_spaces.py`: Use `hmac.compare_digest` for constant-time passcode verification and track failed attempts to prevent brute-force attacks.
9. Verification:
   - Run backend test suites: `pytest backend/tests/ -v`.
   - Run frontend test specs: `npm test` or `npx vitest run`.
   - Write comprehensive report to `c:\Users\acer\OneDrive\inga legal\.agents\worker_remediation\handoff.md`.
   - Send completion message to parent when finished.
</USER_REQUEST>
