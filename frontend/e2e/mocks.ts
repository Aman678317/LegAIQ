/**
 * Network mock layer for the Playwright E2E suite.
 *
 * Intercepts every Supabase (auth + REST) and FastAPI request the app makes.
 * No real backend exists — the tests drive the actual UI code end to end.
 */
import { test as base, expect } from "@playwright/test";

export const SUPA = "https://e2efake.supabase.co";
export const API = "http://localhost:8000/api/v1";

export const USER = {
  id: "e2e-user-0001",
  email: "lawyer@e2e.test",
};

export const ORG = {
  id: "e2e-org-0001",
  name: "E2E Law Firm",
  slug: "e2e-law-firm",
};

export const CASE_ID = "e2e-case-0001";
export const DOC_ID = "e2e-doc-0001";

// Synthetic auth fixtures that exist ONLY inside the mocked network layer —
// they never authenticate against anything real. Deliberately named as
// fixtures so secret scanners cannot mistake them for credentials.
export const MOCK_BEARER_FIXTURE = "fixture-bearer-not-a-real-secret-0001";
export const MOCK_RENEWAL_FIXTURE = "fixture-renewal-not-a-real-secret-0001";

// ---------------------------------------------------------------- state ----
export interface JourneyState {
  documents: any[];
  caseCreated: boolean;
  uploaded: boolean;
}

export function freshState(): JourneyState {
  return { documents: [], caseCreated: false, uploaded: false };
}

// ------------------------------------------------- session cookie seeding ----
// @supabase/ssr stores the session in cookie `sb-<ref>-auth-token` as:
//   "base64-" + base64url(JSON.stringify(session))
// (chunks become name.0, name.1 only when large; ours is small)
function chunkedSessionValue(): string {
  // Fake fixtures for the browser E2E suite only — never real credentials.
  const session = {
    access_token: MOCK_BEARER_FIXTURE,
    refresh_token: MOCK_RENEWAL_FIXTURE,
    token_type: "bearer",
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    user: { id: USER.id, email: USER.email, aud: "authenticated" },
  };
  const b64url = btoa(JSON.stringify(session))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `base64-${b64url}`;
}

export async function seedAuthSession(context: import("@playwright/test").BrowserContext) {
  await context.addInitScript(
    ({ name, value }) => {
      document.cookie = `${name}=${value}; path=/; SameSite=Lax`;
    },
    { name: "sb-e2efake-auth-token", value: chunkedSessionValue() }
  );
}

// ------------------------------------------------------------ mock data ----
const RISK = {
  id: "risk-0001",
  case_id: CASE_ID,
  category: "BOUNDARY",
  level: "HIGH",
  title: "Survey number mismatch across documents",
  description:
    "Conflicting survey numbers found: Sale Deed states 124/3, Partition Deed states 124/2.",
  evidence: [
    {
      document_id: DOC_ID,
      document_name: "sale_deed_1987.pdf",
      page_number: 7,
      source_text: "…Sy. No. 124/3 situated in Whitefield Hobli…",
    },
  ],
  recommended_action: "Verify the official record at the Sub-Registrar office.",
  resolved: false,
  created_at: "2026-08-10T10:00:00+00:00",
};

function caseSummary() {
  return {
    case: {
      id: CASE_ID,
      name: "Whitefield Sy 124/3 — Due Diligence",
      case_type: "PROPERTY",
      status: "ACTIVE",
      jurisdiction_state: "Karnataka",
      jurisdiction_district: "Bengaluru Urban",
      created_at: "2026-08-10T09:00:00+00:00",
      updated_at: "2026-08-10T09:00:00+00:00",
    },
    document_count: state.documents.length,
    processing_count: 0,
    risk_summary: { total: 1, critical: 0, high: 1, medium: 0, low: 0 },
  };
}

const state = freshState();
export function resetState() {
  Object.assign(state, freshState());
}
export { state };

// --------------------------------------------------------------- wiring ----
export const test = base.extend<{ mocked: void }>({
  mocked: [async ({ context }, use) => {
    resetState();
    await seedAuthSession(context);
    await routeMocks(context);
    await use();
  }, { auto: true }],
});

async function json(route: any, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

export async function routeMocks(context: import("@playwright/test").BrowserContext) {
  // ---------------- Supabase auth ----------------
  await context.route(`${SUPA}/auth/v1/user**`, (route) =>
    json(route, {
      id: USER.id,
      email: USER.email,
      aud: "authenticated",
      app_metadata: {},
      user_metadata: { full_name: "E2E Lawyer" },
    })
  );

  await context.route(`${SUPA}/auth/v1/token**`, (route) =>
    json(route, {
      access_token: MOCK_BEARER_FIXTURE,
      refresh_token: MOCK_RENEWAL_FIXTURE,
      token_type: "bearer",
      expires_in: 3600,
      expires_at: Math.floor(Date.now() / 1000) + 3600,
      user: { id: USER.id, email: USER.email, aud: "authenticated" },
    })
  );

  // ---------------- Supabase REST (direct client queries) ----------------
  await context.route(`${SUPA}/rest/v1/**`, async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (url.includes("/profiles")) {
      return json(route, [
        { id: USER.id, email: USER.email, full_name: "E2E Lawyer", is_platform_admin: false },
      ]);
    }
    if (url.includes("/memberships")) {
      return json(route, [
        { role: "OWNER", organizations: ORG },
      ]);
    }
    if (url.includes("/cases")) {
      if (method === "GET") return json(route, []);
      return json(route, []);
    }
    // documents / jobs / anything else the SSE-poll fallback queries
    return json(route, []);
  });

  // ---------------- FastAPI backend ----------------
  await context.route(`${API}/**`, async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    // SSE stream: close immediately; the hook falls back to polling (mocked above)
    if (url.includes("/events")) {
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: "" });
    }

    if (url.endsWith("/cases") && method === "POST") {
      state.caseCreated = true;
      return json(route, {
        id: CASE_ID,
        organization_id: ORG.id,
        name: "Whitefield Sy 124/3 — Due Diligence",
        case_type: "PROPERTY",
        status: "ACTIVE",
        jurisdiction_state: "Karnataka",
        created_at: "2026-08-10T09:00:00+00:00",
        updated_at: "2026-08-10T09:00:00+00:00",
      });
    }

    // GET /cases?organization_id=... (paginated shape)
    if (/\/cases\/?$/.test(new URL(url).pathname) && method === "GET") {
      return json(route, { items: [], total: 0, offset: 0, limit: 50 });
    }

    if (url.includes(`/cases/${CASE_ID}/documents`) && method === "POST") {
      state.uploaded = true;
      state.documents.push({
        id: DOC_ID,
        case_id: CASE_ID,
        file_name: "sale_deed_1987.pdf",
        file_type: "application/pdf",
        file_size: 238_492,
        storage_path: `organizations/${ORG.id}/cases/${CASE_ID}/documents/${DOC_ID}/sale_deed_1987.pdf`,
        status: "COMPLETED",
        page_count: 7,
        language: "en",
        ocr_confidence: 0.94,
        created_at: "2026-08-10T09:05:00+00:00",
        updated_at: "2026-08-10T09:05:00+00:00",
      });
      return json(route, state.documents[0]);
    }

    if (url.includes(`/cases/${CASE_ID}/documents`) && method === "GET") {
      return json(route, state.documents);
    }

    if (url.includes(`/cases/${CASE_ID}/summary`)) return json(route, caseSummary());
    if (url.includes(`/cases/${CASE_ID}/risks`)) return json(route, [RISK]);
    if (url.includes(`/cases/${CASE_ID}/activity`)) return json(route, []);
    if (url.includes(`/cases/${CASE_ID}/jobs`)) return json(route, []);

    if (url.includes(`/cases/${CASE_ID}/questions`) && method === "POST") {
      return json(route, {
        id: "msg-0002",
        case_id: CASE_ID,
        role: "assistant",
        content:
          "The sale deed records the survey number as Sy. No. 124/3 of Whitefield Hobli. [Document: sale_deed_1987.pdf, Page: 7]",
        citations: [
          {
            document_id: DOC_ID,
            document_name: "sale_deed_1987.pdf",
            page_number: 7,
            source_text: "…Sy. No. 124/3 situated in Whitefield Hobli…",
          },
        ],
        created_at: "2026-08-10T10:30:00+00:00",
      });
    }
    if (url.includes(`/cases/${CASE_ID}/questions`)) return json(route, []);

    if (url.includes(`/cases/${CASE_ID}/ownership`)) {
      return json(route, { nodes: [], edges: [] });
    }

    // Default: empty list keeps every page in a defined state
    return json(route, []);
  });
}

export { expect };
