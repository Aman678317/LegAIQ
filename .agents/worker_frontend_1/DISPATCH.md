# DISPATCH

## 2026-08-20T21:28:06+05:30

Role: Worker 2 (Frontend Client, Health Proxy & Model UI Worker)
Parent: e3bd4989-9fab-4d09-bd11-f966c3b5047e

Files to own/implement:
- `frontend/lib/rajora.ts`
- `frontend/app/api/rajora/health/route.ts`
- `frontend/lib/aiEngine.ts`
- `frontend/app/(app)/cases/[caseId]/questions/page.tsx`
- `frontend/app/(app)/settings/page.tsx`
- `frontend/lib/rajora.test.ts` (and any other frontend test files needed for rajora)

Tasks:
1. Implement `frontend/lib/rajora.ts`:
   - Define `RAJORA_PRIVATE_MODEL` with `id: "rajora-private"`, `name: "Rajora Private LLM"`, `provider: "rajora"`, `badge: "Private · Zero Third-Party"`.
   - Implement `checkRajoraStatus()`: queries `/api/rajora/health` with a timeout, returns `{ online: boolean, latency_ms?: number, model?: string, error?: string }`.
   - Export helper functions for checking if a model is Rajora, formatted badges, etc.
2. Implement `frontend/app/api/rajora/health/route.ts`:
   - Proxies to `${process.env.BACKEND_URL || "http://localhost:8000"}/api/rajora/health` (or `/api/v1/rajora/health` / fallback).
   - Returns `{ online: true, status: "healthy", provider: "rajora", model: "rajora-private", latency_ms }` if reachable, or 503 with `{ online: false, error: ... }` if unreachable.
3. Update `frontend/lib/aiEngine.ts`:
   - Add `rajora-private` to model options and ensure `generateLegalAnswer`, `generateLegalResearch`, `generateLegalDraft`, `generateLegalReport` support `provider: "rajora"` / `model: "rajora-private"`.
4. Update model selectors in UI:
   - In `frontend/app/(app)/cases/[caseId]/questions/page.tsx` (and any relevant drafting/chat selectors), add `Rajora Private LLM (Private · Zero Third-Party)` to the model options.
5. Update `frontend/app/(app)/settings/page.tsx`:
   - Add a read-only status card showing Rajora connection state, "Private · Zero Third-Party" badge, latency, and a link to `/admin` for platform administrators.
6. Automated Frontend Tests:
   - Create `frontend/lib/rajora.test.ts` testing:
     - `checkRajoraStatus()` for online and offline cases.
     - Model selector entries verify `rajora-private` presence and proper request payload generation with `provider: "rajora"`.
     - Helper utilities in `frontend/lib/rajora.ts`.
   - Run `npm test` (or `npx vitest run`) in `frontend/`.
   - Ensure all tests pass with zero regressions.
