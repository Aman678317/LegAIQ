# Jurisiva AI

**AI for Legal Work. Built for India.**

An evidence-first legal AI platform for lawyers, law firms, and property
professionals. Jurisiva reads old property documents in 11 Indian languages,
reconstructs ownership chains, flags title risks with page-level evidence,
and drafts filings — every finding cites its source.

## Quick Start (Local)

### 1. Prerequisites
- Node.js 20+
- Python 3.12+
- Docker (for Postgres + Redis)

### 2. Configure environment
```bash
cp .env.example .env
# Fill in Supabase URL + keys (create a free project at supabase.com)
# Optionally set OPENAI_API_KEY (or ANTHROPIC_API_KEY) for real AI
```

### 3. Run infrastructure
```bash
docker compose up -d supabase-db redis
# Or use a cloud Supabase project and skip this
```

### 4. Apply database migrations
Run the SQL files in order against your Supabase project
(SQL Editor → paste each file from `supabase/migrations/`):
```
001_auth_and_orgs.sql → 002_cases_properties.sql → ... → 011_admin.sql
```

To make yourself a platform administrator (admin panel access):
```sql
update public.profiles set is_platform_admin = true where email = 'you@firm.com';
```

### 5. Start the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/api/docs
```

### 6. Start the worker (OCR, extraction, risks)
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

### 7. Start the frontend
```bash
cd frontend
npm install
npm run dev
# App: http://localhost:3000
```

## Running Tests

### Backend — 67 tests (unit + API + full E2E pipeline)
Create case → upload → OCR → extraction → ownership → comparison →
risks → report → PDF export, plus agent budgets, SSRF guard, billing,
and voice provider tests. No database or network needed:

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

### Frontend browser E2E — 10 Playwright tests
Login → dashboard → create property case → upload deed → OCR stats →
risks with evidence → cited Q&A. Runs the real Next.js production build
in Chromium against a page-route mock layer (`frontend/e2e/mocks.ts`)
— no backend, no database, no network:

```bash
cd frontend
npx playwright install chromium   # once
npm run test:e2e
```

### CI (GitHub Actions)
`.github/workflows/ci.yml` runs on every push and pull request:
backend tests → frontend typecheck + build → Playwright browser E2E
(with trace artifacts uploaded on failure).

## What Works Without API Keys

- Full case management, document upload, storage
- OCR via tesseract (install separately: `tesseract-ocr` + language packs)
- Regex-based extraction of survey numbers, khata, dates, amounts
- Document comparison + risk engine (deterministic, evidence-based)
- Keyword search RAG (no embeddings needed)
- PDF report export

AI chat, drafting, research, and translation require at least one of:
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. Without keys, these features return a
clear "Not configured" message — they never fake results.

## Deployment (Render)

`render.yaml` defines the full stack:
- `jurisiva-api` — FastAPI web service
- `jurisiva-worker` — Celery worker (OCR pipeline)
- `jurisiva-beat` — job dispatcher
- `jurisiva-redis` — message broker
- `jurisiva-frontend` — Next.js

Connect the repo at render.com, set the environment variables from
`.env.example`, and deploy.

## Repository Layout

```
frontend/    Next.js 16 app (landing + case workspace)
backend/     FastAPI API + Celery workers
supabase/    SQL migrations (apply in order)
shared/      TypeScript types
docs/        Implementation audit
```

## Core Principles

1. **Evidence-first** — every finding shows document, page, and source text
2. **No hallucination** — "Not found in the uploaded documents" when absent
3. **Never modify originals** — uploaded files are immutable
4. **Server-side authorization** — frontend roles are never trusted
5. **Honest fallbacks** — unconfigured features say so, never fake results

## Legal Notice

Jurisiva AI provides AI-assisted legal workflow support. It does not replace
professional legal judgment. All generated documents display:
"AI-generated draft. Review and verify before filing or sending."
