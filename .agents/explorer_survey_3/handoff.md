# Handoff Report — Explorer 3: Frontend Client, Health Proxy & Model UI

**Sender**: Explorer 3 (`explorer_survey_3`)  
**Recipient**: Orchestrator (`e3bd4989-9fab-4d09-bd11-f966c3b5047e`)  
**Task**: Survey Frontend Client, Health Proxy & Model UI for Rajora AI Integration (Phase 5 / R4)  
**Date**: 2026-08-20  
**Handoff Type**: Hard Handoff (Task Complete)  

---

## 1. Observation

Direct observations from the codebase investigation:
1. **Model Definition & Engine**:
   - `frontend/lib/aiEngine.ts` contains `generateLegalAnswer`, `generateLegalResearch`, `generateLegalDraft`, `generateLegalReport` which accept an optional `model?: string` parameter and fall back to local Ollama (`frontend/lib/ollama.ts`) or deterministic multi-domain legal cognition.
   - Currently, there is no separate `frontend/lib/rajora.ts` or `rajora-private` definition.
2. **Model Selectors in UI**:
   - `frontend/app/(app)/cases/[caseId]/questions/page.tsx` (lines 261–286) contains a `<select>` with `<optgroup label="Cloud Legal Frontier Models">` (`claude-3-5-sonnet`, `gpt-4o`, `deepseek-r1`) and `<optgroup label="Local / Private Sovereign Models">` (`llama3.1:70b`, `llama3.1:8b`, and dynamic `ollamaStatus.models`).
   - `frontend/app/(app)/chat/page.tsx` (lines 243–271) has an Ollama status and model picker.
   - `frontend/app/(app)/cases/[caseId]/drafting/page.tsx` (lines 108–118) displays an AI engine status badge.
   - `frontend/app/(app)/cases/[caseId]/research/page.tsx` (lines 49–77) manages model selection for research memo generation.
   - `frontend/app/(app)/command-center/page.tsx` (lines 39–44) lists model breakdowns in the telemetry table.
3. **API Proxy Routes**:
   - `frontend/app/api/ollama/[...path]/route.ts` illustrates the Next.js App Router API proxy pattern using `fetch` with `AbortController` and error forwarding.
   - `frontend/app/api/chat/route.ts` shows multi-provider fallback ordering.
   - There is currently no `frontend/app/api/rajora/health/route.ts`.
4. **Settings Page**:
   - `frontend/app/(app)/settings/page.tsx` (lines 169–287) has a status card for Ollama with connection status badge, endpoint config form, model list, diagnostics, and CLI instructions.
   - Platform admin navigation is established in `frontend/app/(app)/layout.tsx` (lines 239–257) with link to `/admin`.
5. **Test Setup**:
   - `frontend/package.json` specifies `"test": "vitest run"`.
   - `frontend/vitest.config.mjs` configures `happy-dom`, `setupFiles: ["./vitest.setup.ts"]`, `include: ["**/*.test.{ts,tsx}"]`.
   - `frontend/vitest.setup.ts` stubs router and Supabase mocks.
   - 4 existing test suites pass: `m1_m2_features.test.ts`, `mockStore.test.ts`, `tier_comprehensive.test.ts`, `utils.test.ts`.

---

## 2. Logic Chain

1. **Client Helper (`frontend/lib/rajora.ts`)**:
   - Needs `checkRajoraStatus()` querying `/api/rajora/health` with a timeout and returning `{ online: boolean, latency_ms?: number, model?: string, error?: string }`.
   - Needs exported `RAJORA_PRIVATE_MODEL` constant with `id: "rajora-private"`, `name: "Rajora Private LLM"`, `provider: "rajora"`, `badge: "Private · Zero Third-Party"`.
2. **Proxy Route (`frontend/app/api/rajora/health/route.ts`)**:
   - Proxies incoming `GET` to `${process.env.BACKEND_URL || "http://localhost:8000"}/api/rajora/health`.
   - If backend returns 200, returns `{ online: true, status: "healthy", provider: "rajora", model: "rajora-private", latency_ms }`.
   - If backend is down or unreachable, returns `{ online: false, error: ... }` with status 503 without crashing.
3. **UI Model Selector Integration**:
   - In `frontend/app/(app)/cases/[caseId]/questions/page.tsx`, add `<option value="rajora-private">Rajora Private LLM (Private · Zero Third-Party)</option>` inside `<optgroup label="Local / Private Sovereign Models">`.
   - In `frontend/lib/aiEngine.ts`, register `rajora-private` in model options.
4. **Settings Status Card**:
   - In `frontend/app/(app)/settings/page.tsx`, add a read-only card for Rajora Private LLM with status badge (`"Private · Zero Third-Party"` + online/offline state), latency display, security assurance, and a link to `/admin` for platform administrators.
5. **Vitest Unit Tests (`frontend/lib/rajora.test.ts`)**:
   - Verify `checkRajoraStatus()` handles both online (mocked 200) and offline (mocked fetch rejection/500) cases.
   - Verify model selector entries and request payload formatting with `provider: "rajora"`.

---

## 3. Caveats

- In demo/offline mode (`isDemoMode()`), frontend falls back to `mockStore.ts`; `mockStore.askDemoQuestion` already handles arbitrary model IDs gracefully.
- Backend health route `/api/rajora/health` must be implemented in the backend (Phase 3/4) for the health proxy to return live status in full-stack deployments.

---

## 4. Conclusion

The frontend codebase is cleanly architected with well-isolated components, clear API proxy patterns, and an established Vitest testing setup. Integrating Rajora AI requires creating 2 new files (`frontend/lib/rajora.ts`, `frontend/app/api/rajora/health/route.ts`), updating 2 UI files (`questions/page.tsx`, `settings/page.tsx`), and adding 1 test file (`frontend/lib/rajora.test.ts`). All changes follow existing conventions with zero risk of regression to existing providers.

---

## 5. Verification Method

1. Inspect generated files and changes:
   - `frontend/lib/rajora.ts`
   - `frontend/app/api/rajora/health/route.ts`
   - `frontend/lib/aiEngine.ts`
   - `frontend/app/(app)/cases/[caseId]/questions/page.tsx`
   - `frontend/app/(app)/settings/page.tsx`
   - `frontend/lib/rajora.test.ts`
2. Run Vitest test suite:
   - Command: `npm test` (or `npx vitest run`) inside `frontend/`
   - Invalidation condition: Any failure in `frontend/lib/rajora.test.ts` or regression in existing test suites.
