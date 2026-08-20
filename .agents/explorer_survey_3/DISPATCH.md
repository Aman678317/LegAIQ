## 2026-08-20T15:54:45Z
Investigate the Frontend Client, Health Proxy & Model UI for Rajora AI integration.
Tasks:
1. Examine frontend/lib/aiEngine.ts, frontend/lib/, and how models, providers, and badges are defined and used.
2. Search all model selectors in chat, drafting, review, or workflow pages where models can be chosen.
3. Examine frontend/app/api/ routes, health check routes, and how API proxying to ${process.env.BACKEND_URL} is implemented.
4. Examine frontend/app/(app)/settings/page.tsx and settings components to see where status cards and admin links are placed.
5. Check frontend test suite setup (vitest, npm test, test utilities, mocks).
