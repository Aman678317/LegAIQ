# Original User Request

## 2026-08-21T03:46:22Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team

Conduct a comprehensive project audit, bug fix, dead code cleanup, security hardening, and end-to-end verification across the entire LegAIQ / Jurisiva AI repository to make the platform fully production-ready while preserving all existing working functionality.

Working directory: c:\Users\acer\OneDrive\inga legal
Integrity mode: development

## Requirements

### R1. Full Architecture & Codebase Audit
- Inspect all modules across the repository: Frontend (Next.js 16 / React 19 / Tailwind CSS), Backend (FastAPI, Celery, LangGraph), Database (Supabase PostgreSQL migrations 001–014, pgvector, RLS), AI Providers (Rajora, Nvidia, Ollama, OpenAI, Anthropic, Mock), and Security layers (SSO, PII redaction, BSA 2023, SSRF).
- Verify connection integrity and routing between frontend API routes, FastAPI backend endpoints, Celery tasks, and Supabase RPCs.

### R2. Bug Fixing & Type Safety Hardening
- Identify and fix all runtime errors, type errors (`tsc`), broken API calls, missing imports, unhandled exceptions, and edge cases.
- Validate async/await patterns, error propagation, and fallbacks in AI provider routing and background task execution.
- Ensure all frontend interactive modals, review tables, and document viewers handle loading, empty, and error states gracefully.

### R3. Dead Code & Orphaned Resource Cleanup
- Identify and remove unused files, dead code, abandoned functions, redundant console logs, and unused dependencies without touching active features.
- Clean up unused imports and standardize error formatting across all router endpoints.

### R4. Security Review & Secret Protection
- Audit all code, tests, and configuration files to ensure zero secrets, API keys, or private tokens are committed or leaked in logs.
- Verify that Supabase Row Level Security (RLS) policies enforce multi-tenant isolation across all tables.
- Validate timing-safe authentication and permission checks on all admin and internal endpoints.

### R5. Verification, Test Hardening & Final Report
- Run and verify all test suites across the repository (backend hermetic pytest, frontend Vitest, and Playwright E2E suites).
- Generate a comprehensive audit report detailing fixed bugs, removed items, security improvements, and test coverage verification.

## Acceptance Criteria

### Automated Backend Tests
- [ ] `python -m pytest backend/tests/ -v` passes 100% (550+ tests passing, 0 failures, 0 errors).
- [ ] Adversarial and security boundary tests pass with zero unhandled exceptions.

### Automated Frontend Tests & Type Checks
- [ ] `npm test` (`vitest run`) passes 100% across all test suites (`rajora.test.ts`, `tier_comprehensive.test.ts`, `mockStore.test.ts`, `utils.test.ts`, `m1_m2_features.test.ts`).
- [ ] Zero TypeScript compilation errors across the entire frontend.

### Security & Production Guardrails
- [ ] No hardcoded API keys, tokens, or credentials exist in any committed file or test fixture.
- [ ] All RLS policies correctly isolate tenant data by `organization_id` and `auth.uid()`.
- [ ] All existing working functionality across all 29 features remains fully intact with zero regressions.
