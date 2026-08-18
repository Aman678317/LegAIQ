# Jurisiva AI

Jurisiva AI is an evidence-first legal artificial intelligence platform designed for legal practitioners, law firms, and property professionals in India. The platform processes legacy property documents in eleven Indian languages, reconstructs ownership chains, identifies title risks with page-level evidentiary support, and generates draft filings. All findings are cited to source material.

## Getting Started

### Prerequisites

* Node.js 20 or later
* Python 3.12 or later
* Docker for local PostgreSQL and Redis

### Environment Configuration

```bash
cp .env.example .env
```

Configure the following variables in `.env`:

* Supabase URL and keys. A Supabase project may be provisioned at supabase.com.
* Optionally set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for generative AI features.

### Infrastructure

Start local services with Docker Compose:

```bash
docker compose up -d supabase-db redis
```

A cloud-hosted Supabase project may be used in lieu of local services.

### Database Migrations

Apply migrations in sequential order via the Supabase SQL Editor:

```
001_auth_and_orgs.sql
002_cases_properties.sql
...
011_admin.sql
```

To grant platform administrator privileges:

```sql
UPDATE public.profiles 
SET is_platform_admin = true 
WHERE email = 'you@firm.com';
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API documentation is available at http://localhost:8000/api/docs.

### Background Workers

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

Workers handle OCR, extraction, and risk processing.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The application is accessible at http://localhost:3000.

---

## Local AI with Ollama (100% Private, Offline & Free)

Jurisiva AI has first-class native support for [Ollama](https://ollama.com) for 100% private, local LLM inference and document embeddings with zero external API key requirements.

### 1. Install & Launch Ollama with CORS Enabled

In your terminal:

**Windows PowerShell:**
```powershell
$env:OLLAMA_ORIGINS="*" ; ollama serve
```

**macOS / Linux:**
```bash
OLLAMA_ORIGINS="*" ollama serve
```

### 2. Pull Recommended Models

In a separate terminal:
```bash
# Recommended general LLM (8B)
ollama pull llama3

# Fast vector embedding model for document RAG
ollama pull nomic-embed-text

# Optional legal/reasoning alternative models
ollama pull mistral
ollama pull deepseek-r1
```

### 3. Verify Connection from Terminal

Run the built-in diagnostic test:
```bash
python test_ollama.py
```

---

## Testing

### Backend Tests

The backend test suite comprises unit, API, and end-to-end pipeline tests covering case creation, upload, OCR, extraction, ownership reconstruction, comparison, risk assessment, reporting, and PDF export, as well as agent budgets, SSRF protection, billing, and voice provider functionality. Tests require no external database or network connectivity.

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

### Frontend End-to-End Tests

Playwright-based browser tests validate authentication, dashboard, property case creation, deed upload, OCR statistics, risk reporting with evidence, and cited question answering. Tests execute against a production build with a page-route mock layer and require no backend or network connectivity.

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

### Continuous Integration

`.github/workflows/ci.yml` executes on push and pull request events:

1. Backend pytest
2. Frontend typechecking and build
3. Playwright browser end-to-end tests

Trace artifacts are uploaded on failure.

## Functionality Without API Keys

The following features operate without generative AI credentials:

* Case management and document upload and storage
* OCR via Tesseract, subject to local installation of `tesseract-ocr` and language packs
* Rule-based extraction of survey numbers, khata, dates, and amounts
* Document comparison and deterministic risk engine with evidence
* Keyword-based retrieval augmented generation without embeddings
* PDF report export

Generative chat, drafting, research, and translation require `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Unconfigured features return an explicit "Not configured" response.

## Deployment

`render.yaml` defines the production stack:

* `jurisiva-api` — FastAPI web service
* `jurisiva-worker` — Celery worker for OCR pipeline
* `jurisiva-beat` — Celery beat scheduler
* `jurisiva-redis` — Message broker
* `jurisiva-frontend` — Next.js application

Connect the repository to Render, configure environment variables from `.env.example`, and deploy.

## Repository Structure

```
frontend/    Next.js 16 application for landing and case workspace
backend/     FastAPI API and Celery workers
supabase/    SQL migrations
shared/      Shared TypeScript types
docs/        Implementation audit documentation
```

## Principles

1. Evidence-first: each finding references document, page, and source text.
2. No hallucination: absent information is reported as "Not found in the uploaded documents".
3. Immutability: uploaded files are not modified.
4. Server-side authorization: client-side roles are not trusted.
5. Transparent fallbacks: unconfigured features are explicitly indicated.

## Legal Notice

Jurisiva AI provides AI-assisted legal workflow support and does not constitute legal advice. It does not replace professional legal judgment. All generated documents include the disclaimer:

"AI-generated draft. Review and verify before filing or sending."
