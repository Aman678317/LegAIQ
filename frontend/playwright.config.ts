import { defineConfig, devices } from "@playwright/test";

/**
 * E2E suite: real Next.js app, fully mocked network (Supabase + FastAPI).
 * No backend, no database — the mock layer in e2e/mocks.ts intercepts
 * everything. See e2e/mocks.ts for the auth cookie format.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    viewport: { width: 1366, height: 900 },
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    // Production server: everything is precompiled, so page loads are fast
    // and deterministic (dev-mode on-demand compilation exceeds test timeouts).
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
    env: {
      NEXT_PUBLIC_SUPABASE_URL: "https://e2efake.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY:
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e2e-fake-anon-key",
      NEXT_PUBLIC_API_URL: "http://localhost:8000/api/v1",
    },
  },
});
