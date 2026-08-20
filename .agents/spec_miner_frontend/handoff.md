# Handoff Report — Frontend & UI Architecture Specification Miner

**Date:** 2026-08-20  
**Agent:** spec_miner_frontend  
**Task:** Frontend Architecture Discovery & Specification Mining for LegAIQ / Jurisiva AI  
**Integrity Mode:** Development  

---

## 1. Observation

1. **Tech Stack & Layout**:
   - `frontend/package.json` (lines 14-28, 29-43) specifies Next.js 16.3.1, React 19.2.8, TypeScript 5, Tailwind CSS v4 (`@tailwindcss/postcss: ^4`), Zustand 5.0.15, `@supabase/supabase-js: ^2.112.3`, `lucide-react: ^1.31.0`, Vitest 4.1.11, Playwright 1.62.1.
   - `frontend/app/(app)/layout.tsx` (lines 19-39) defines navigation containing `/dashboard`, `/chat`, `/settings`, and case navigation items: `documents`, `analysis`, `property`, `ownership`, `timeline`, `comparison`, `risks`, `research`, `questions`, `drafting`, `reports`, `voice`.
   - `frontend/app/globals.css` (lines 3-21) defines dark-mode design tokens: `--color-bg: #0a0a0f`, `--color-bg-surface: #12121a`, `--color-primary: #2563eb`, `--color-accent: #7c3aed`.

2. **R1: Assistant & Chat Workspace**:
   - `frontend/app/(app)/cases/[caseId]/questions/page.tsx` (lines 87-104, 133-168, 222-238) implements real-time streaming chat (`askQuestionStream`), model selection (`llama3.1:70b`, `claude-3-5-sonnet`, `gpt-4o`, `deepseek-r1`), 12+ Indic languages, and evidentiary citations list at the end of messages.
   - `frontend/app/(app)/chat/page.tsx` (lines 26-51, 152-194) implements universal Ollama chatbot with presets (General, Coding, Legal, Writing).
   - Missing: Unified Ask/Analyze/Draft mode switcher within Assistant workspace, inline clickable citation chips `[Doc: name, Pg: N]` inside the message text, explicit India Context toggle switch.

3. **R2: Secure Matter Vault & Document Viewer**:
   - `frontend/app/(app)/cases/[caseId]/documents/page.tsx` (lines 85-94, 270-390) implements drag-and-drop dropzone (PDF, JPG, PNG, TIFF up to 50MB), SSE live sync, document viewer modal with page navigation, CLAHE contrast indicator, uncertainty tag warning (`[UNCERTAIN: ...]`), and page translation.
   - `frontend/app/(app)/cases/[caseId]/comparison/page.tsx` (lines 14-73, 156-250) implements pairwise/multi-document comparison with inline diff view.
   - Missing: DOCX and XLSX dropzone support, automatic document type classification badges (Sale Deed, Partition Deed, 7/12 Extract, RTC/Pahani, Mutation Extract), dual-pass OCR confidence heatmap overlay.

4. **R3: Spreadsheet-Style Review Tables**:
   - Grep search for `ReviewTable` and `review_table` across the entire codebase returned 0 matches (`frontend/app` and `frontend/components`).
   - Missing: Complete Review Tables workspace route (`(app)/cases/[caseId]/review/page.tsx`), interactive grid with custom prompt extraction columns, cell click evidence drawer, confidence score chips, and CSV/Excel export.

5. **R4: No-Code Visual Workflow Builder**:
   - `backend/app/ai/agents/orchestration.py` (lines 45-214) implements `AgentOrchestrator`, `WorkflowDefinition`, `WorkflowNode`, and built-in workflows (`property_due_diligence`, `title_search_report`, `contract_intelligence`, `voice_qa`).
   - `frontend/app/(app)/admin/agent-runs/page.tsx` (lines 24-110) implements a read-only admin table of historical agent runs and tool calls.
   - Missing: Visual drag-and-drop workflow canvas UI, node configuration drawer, test execution triggers, and interactive live step progress visualizer.

6. **R5: Contract Intelligence & Clause Library**:
   - `backend/app/ai/contract_intelligence.py` (lines 18-50, 176-297, 641-723) implements 29+ clause types extraction, 0-100 risk assessment, obligation tracking, and redline diff generator.
   - `frontend/lib/api.ts` (lines 554-604) provides `analyzeContract` and `redlineContract` client methods.
   - Missing: Dedicated Contract Intelligence workspace UI (`/contracts`), 29+ clause breakdown view with 0-100 risk score meter, searchable Clause Library with fallback tiers, negotiation Playbooks UI, and redline visual diff editor.

7. **R6: Enterprise Command Center & Shared Spaces**:
   - `frontend/app/(app)/admin/ai-usage/page.tsx` and `(app)/admin/audit/page.tsx` provide basic token/cost stats and immutable audit events.
   - `backend/app/api/pii.py` provides Indian PII detection and redaction endpoints.
   - Missing: Matter Shared Space / Share modal with link expiry (1h/24h/7d) and password protection, watermark configuration UI, velocity/turnaround analytics charts, and interactive PII redaction preview.

8. **R7: India-First Property & Legal Moat**:
   - `frontend/app/(app)/cases/[caseId]/property/page.tsx`, `ownership/page.tsx`, `timeline/page.tsx`, `research/page.tsx`, and `reports/page.tsx` implement property fields, Advocate due diligence checklist, Indian land measurement unit converter widget, timeline, legal research, and Title Search Report v2 generation.
   - Missing: Live 28+ State Land Portal search UI tab/modal, interactive graph canvas for 13-30 year ownership chain, Bharatiya Sakshya Act (BSA 2023) evidence rules audit drawer.

---

## 2. Logic Chain

1. **Step 1**: Inspected `ORIGINAL_REQUEST.md` to identify the 7 target capability groups (R1–R7) and acceptance criteria.
2. **Step 2**: Inspected `frontend/package.json`, `app/layout.tsx`, `components/ui.tsx`, and `app/globals.css` to verify the frontend architecture, styling tokens, component library, and route structure.
3. **Step 3**: Probed existing implementations for R1 through R7 across `frontend/app/(app)/` and `frontend/lib/api.ts`.
4. **Step 4**: Verified that while the foundational core exists for Chat (R1), Documents (R2), Property (R7), and Admin (R6), there are major gaps in Review Tables (R3 - 0% implemented), Visual Workflow Builder (R4 - only admin table exists), Contract Intelligence UI (R5 - backend exists but UI is missing), and Matter Shared Spaces / Link Expiry / PII Preview (R6).
5. **Step 5**: Compiled an exhaustive gap analysis and component roadmap in `analysis.md`.

---

## 3. Caveats

- Backend contract endpoints and LangGraph workflow orchestration are implemented in Python/FastAPI (`backend/app/ai/contract_intelligence.py` and `backend/app/ai/agents/orchestration.py`), meaning frontend views can directly bind to existing backend contracts or mock fallbacks.
- E2E tests are configured in Playwright (`frontend/e2e/case-journey.spec.ts`); adding new UI routes will require updating navigation mocks in `frontend/e2e/mocks.ts`.

---

## 4. Conclusion

The LegAIQ / Jurisiva AI frontend has a strong foundation with Next.js 16, Tailwind CSS v4, dark theme design system, and PWA offline capabilities. To reach Harvey-class enterprise parity while preserving the India-first moat, the frontend roadmap requires:
1. **R1**: Integrating a 3-mode switcher (Ask/Analyze/Draft), inline clickable citation chips, and India Context toggle into Assistant.
2. **R2**: Adding DOCX/XLSX support, automatic document classification badges, and dual-pass OCR view.
3. **R3**: Building the complete Review Tables interactive spreadsheet grid with custom prompt extraction columns, cell evidence drawer, and Excel export.
4. **R4**: Building the No-Code Visual Workflow Builder with drag-and-drop canvas and live execution timeline.
5. **R5**: Building the Contract Intelligence workspace with 29+ clause breakdown, 0-100 risk meter, Clause Library, Playbooks, and Redlining editor.
6. **R6**: Implementing Matter Shared Spaces modal with link expiry, watermark settings, and PII redaction preview.
7. **R7**: Embedding live State Land Portal search picker, interactive ownership graph canvas, and BSA 2023 evidence drawer.

---

## 5. Verification Method

- Inspect analysis report: `view_file` on `c:\Users\acer\OneDrive\inga legal\.agents\spec_miner_frontend\analysis.md`
- Inspect existing UI layout: `view_file` on `c:\Users\acer\OneDrive\inga legal\frontend\app\(app)\layout.tsx`
- Inspect existing routes: `find_by_name` in `c:\Users\acer\OneDrive\inga legal\frontend\app\(app)`
- Inspect mock store & unit tests: `view_file` on `c:\Users\acer\OneDrive\inga legal\frontend\lib\mockStore.test.ts`
