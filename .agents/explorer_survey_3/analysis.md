# Frontend Client, Health Proxy & Model UI Investigation (Explorer 3)

**Codebase**: `c:\Users\acer\OneDrive\inga legal\frontend`  
**Date**: 2026-08-20  
**Status**: COMPLETE  

---

## 1. Executive Summary

This investigation analyzed the frontend architecture of Jurisiva AI / LegAIQ in preparation for integrating the **Rajora AI Private LLM** (Phase 5 / R4). 
The frontend is a Next.js (App Router) application utilizing React 19, TypeScript, Tailwind CSS, and Vitest.
Key integration points identified:
1. **AI Engine & Model Constants** (`frontend/lib/aiEngine.ts`, `frontend/lib/ollama.ts`, `frontend/lib/rajora.ts`): Definition of model IDs (`rajora-private`), provider identifiers (`rajora`), and metadata badges (`"Private · Zero Third-Party"`).
2. **Model Selectors in UI Workspaces**: `frontend/app/(app)/cases/[caseId]/questions/page.tsx`, `frontend/app/(app)/chat/page.tsx`, `frontend/app/(app)/cases/[caseId]/drafting/page.tsx`, `frontend/app/(app)/cases/[caseId]/research/page.tsx`, and `frontend/app/(app)/command-center/page.tsx`.
3. **API Health Proxy Route**: `frontend/app/api/rajora/health/route.ts` proxying health checks to `${process.env.BACKEND_URL}/api/rajora/health`.
4. **Settings Workspace Status Card**: `frontend/app/(app)/settings/page.tsx` displaying the sovereign Rajora connection state and platform admin navigation link.
5. **Testing Architecture**: Vitest test runner with `happy-dom` and mocked fetch / environment variables for unit testing `frontend/lib/rajora.test.ts` and model selector payloads.

---

## 2. Detailed Findings by Area

### Area 1: `frontend/lib/` Architecture & Model Definitions

- **File**: `frontend/lib/aiEngine.ts` (1411 lines)
  - Functions: `generateLegalAnswer`, `generateLegalResearch`, `generateLegalDraft`, `generateLegalReport`, `detectDomain`.
  - Currently handles `model?: string` and checks `ollamaStatus.online` with fallback to high-precision domain-specific cognitive logic.
  - **Proposed Enhancement**:
    - Export supported model registry / constants (`RAJORA_MODEL_DEFINITION`, `SUPPORTED_AI_MODELS`).
    - Integrate `rajora-private` definition:
      ```typescript
      export interface AIModelOption {
        id: string;
        name: string;
        provider: "rajora" | "ollama" | "anthropic" | "openai" | "deepseek" | "nvidia" | "groq";
        badge: string;
        description: string;
        isPrivate: boolean;
      }

      export const RAJORA_PRIVATE_MODEL: AIModelOption = {
        id: "rajora-private",
        name: "Rajora Private LLM",
        provider: "rajora",
        badge: "Private · Zero Third-Party",
        description: "Self-hosted sovereign legal LLM inference (Zero Third-Party Data Leakage)",
        isPrivate: true,
      };
      ```

- **File to Create**: `frontend/lib/rajora.ts`
  - Modeled after `frontend/lib/ollama.ts`.
  - Implements:
    - `RajoraStatus` interface: `{ online: boolean; latency_ms?: number; model?: string; error?: string }`
    - `checkRajoraStatus(endpoint?: string)`: Fetches `/api/rajora/health` with an `AbortController` timeout (e.g. 3000ms), returns online status and latency.
    - Model descriptors and helper utilities for generating request payloads with `provider: "rajora"`.

- **File**: `frontend/lib/api.ts` (1923 lines)
  - `askQuestion` and `askQuestionStream` (lines 313–473) pass `model` in payload to backend `/cases/${caseId}/questions`.
  - When `model === "rajora-private"`, backend provider registry routes request to `RajoraProvider`.

---

### Area 2: Model Selectors Across App Workspaces

1. **Matter Chat & Q&A Workspace** (`frontend/app/(app)/cases/[caseId]/questions/page.tsx`):
   - Lines 261–286 contain a `<select>` with `<optgroup label="Local / Private Sovereign Models">`:
     ```tsx
     <optgroup label="Local / Private Sovereign Models" className="bg-bg text-white">
       <option value="rajora-private">Rajora Private LLM (Private · Zero Third-Party)</option>
       <option value="llama3.1:70b">Llama 3.1 70B (Private On-Premises)</option>
       <option value="llama3.1:8b">Llama 3.1 8B (Fast Local Assistant)</option>
       {ollamaStatus.online && ollamaStatus.models.map((m) => (
         <option key={m} value={m} className="text-emerald-400">Ollama Local: {m}</option>
       ))}
     </optgroup>
     ```
   - Includes visual badges and status indicators for private sovereign execution.

2. **Universal Chat Page** (`frontend/app/(app)/chat/page.tsx`):
   - Lines 70–80 and 243–271 manage status and model picker.
   - Can display Rajora status alongside Ollama with seamless offline/online badge.

3. **Drafting Studio** (`frontend/app/(app)/cases/[caseId]/drafting/page.tsx`):
   - Lines 108–118 render private engine status indicator (Local Legal AI Engine).
   - Can highlight Rajora Private LLM when configured.

4. **Legal Research** (`frontend/app/(app)/cases/[caseId]/research/page.tsx`):
   - Lines 49–77 handle model selection for research memo generation.

5. **Command Center & Telemetry** (`frontend/app/(app)/command-center/page.tsx`):
   - Lines 39–44 define `model_breakdown` table.
   - Can include `Rajora Private LLM` (`provider: "rajora"`, `cost: "$0.00"`, `badge: "Private"`).

---

### Area 3: API Health Proxy Route (`frontend/app/api/`)

- **Current API Routes**:
  - `frontend/app/api/chat/route.ts`: Multi-provider fallback handler.
  - `frontend/app/api/ollama/[...path]/route.ts`: Local Ollama proxy.

- **New Health Route Specification**: `frontend/app/api/rajora/health/route.ts`
  - Proxies to `${process.env.BACKEND_URL}/api/rajora/health` (or fallback `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/rajora/health`).
  - Implementation specification:
    ```typescript
    import { NextRequest, NextResponse } from "next/server";

    const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

    export async function GET(req: NextRequest) {
      const targetUrl = `${BACKEND_URL.replace(/\/$/, "")}/api/rajora/health`;
      const start = Date.now();

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);

        const res = await fetch(targetUrl, {
          method: "GET",
          signal: controller.signal,
          headers: { Accept: "application/json" },
        });
        clearTimeout(timeoutId);

        const data = await res.json().catch(() => ({}));
        return NextResponse.json({
          online: res.ok,
          status: data.status || (res.ok ? "healthy" : "unhealthy"),
          provider: "rajora",
          model: data.model || "rajora-private",
          latency_ms: Date.now() - start,
        }, { status: res.status });
      } catch (err: any) {
        return NextResponse.json({
          online: false,
          status: "unreachable",
          provider: "rajora",
          error: err.message || "Failed to reach backend Rajora health check",
          latency_ms: Date.now() - start,
        }, { status: 503 });
      }
    }
    ```

---

### Area 4: Settings Page Status Card & Admin Links

- **File**: `frontend/app/(app)/settings/page.tsx` (472 lines)
  - Located directly after Ollama card (or integrated in an "Enterprise AI Providers & Sovereignty" section).
  - Status card components:
    - **Header**: ShieldCheck/Server icon, Title `"Rajora Private LLM"`, Badge `"Private · Zero Third-Party"`.
    - **Connection State**: Live badge showing "Connected (14ms)" in emerald, or "Offline / Not Configured" in amber.
    - **Security Metadata**: "Self-hosted sovereign LLM inference (SOP-AI-2026-04). Zero data leakage to public clouds."
    - **Action Controls**:
      - "Check Status" button triggering `checkRajoraStatus()`.
      - "Admin Key Management" link pointing to `/admin` or `/admin/ai-usage` (visible to platform admins).

---

### Area 5: Test Suite Setup & Verification Plan

- **Runner**: Vitest v4.1.11 with `happy-dom` (`frontend/vitest.config.mjs`).
- **Setup File**: `frontend/vitest.setup.ts` (mocks `next/navigation`, `supabase`).
- **New Tests to Create**:
  1. `frontend/lib/rajora.test.ts`:
     - Test `checkRajoraStatus()` when endpoint returns 200 OK (`{ online: true, latency_ms: expect.any(Number) }`).
     - Test `checkRajoraStatus()` on network error or 503 (`{ online: false }`).
     - Test model constant definition (`id: "rajora-private"`, `provider: "rajora"`, `badge: "Private · Zero Third-Party"`).
  2. Model Selector & Payload Unit Tests:
     - Verify `rajora-private` is listed under supported models.
     - Verify chat payload generation correctly attaches `provider: "rajora"` and `model: "rajora-private"`.
- **Zero-Regression Verification**:
  - Run all existing test suites (`m1_m2_features.test.ts`, `mockStore.test.ts`, `tier_comprehensive.test.ts`, `utils.test.ts`).

---

## 3. File Modification & Creation Matrix for Phase 5

| File | Action | Purpose |
|---|---|---|
| `frontend/lib/rajora.ts` | **Create** | Rajora client helper, `checkRajoraStatus()`, model metadata constants |
| `frontend/lib/aiEngine.ts` | **Update** | Add `rajora-private` model option & provider mapping |
| `frontend/app/api/rajora/health/route.ts` | **Create** | Next.js API route proxying to `${process.env.BACKEND_URL}/api/rajora/health` |
| `frontend/app/(app)/cases/[caseId]/questions/page.tsx` | **Update** | Add `rajora-private` option in model selector dropdown |
| `frontend/app/(app)/settings/page.tsx` | **Update** | Add Rajora Private LLM status card and Admin link |
| `frontend/lib/rajora.test.ts` | **Create** | Unit tests for Rajora status check and model selector payload validation |
