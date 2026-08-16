-- ============================================================
-- 006: Research, Drafts, Reports, AI Runs, Audit
-- ============================================================

-- Legal research sessions
create table if not exists public.research_sessions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  question text not null,
  jurisdiction text,
  status text not null default 'QUEUED' check (
    status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')
  ),
  answer text,
  model_used text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_research_case on public.research_sessions(case_id);

-- Sources retrieved during research
create table if not exists public.research_sources (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.research_sessions(id) on delete cascade,
  title text not null,
  url text not null,
  source_type text not null default 'web', -- web, judgment, statute, regulation, secondary
  publisher text,
  published_date date,
  retrieved_at timestamptz not null default now(),
  snippet text,
  verified boolean not null default false,
  content_hash text -- for dedup
);

create index if not exists idx_rsources_session on public.research_sources(session_id);

-- Legal drafts (Drafting Studio)
create table if not exists public.drafts (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  draft_type text not null, -- petition, legal_notice, representation, application, ...
  title text not null,
  content text not null,
  status text not null default 'DRAFT' check (status in ('DRAFT', 'REVIEW', 'FINAL')),
  version integer not null default 1,
  parent_draft_id uuid references public.drafts(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_drafts_case on public.drafts(case_id);

-- Generated reports
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  report_type text not null default 'PROPERTY_DUE_DILIGENCE',
  title text not null,
  status text not null default 'QUEUED' check (
    status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')
  ),
  content jsonb, -- structured report sections
  storage_path text, -- exported PDF/DOCX path
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_reports_case on public.reports(case_id);

-- AI run tracking: cost, tokens, latency per invocation
create table if not exists public.ai_runs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete set null,
  organization_id uuid references public.organizations(id) on delete set null,
  user_id uuid references auth.users(id),
  workflow text not null, -- chat, extraction, research, drafting, translation, ...
  provider text not null,
  model text not null,
  model_version text,
  latency_ms integer,
  prompt_tokens integer,
  completion_tokens integer,
  estimated_cost_usd numeric,
  status text not null default 'RUNNING' check (status in ('RUNNING', 'COMPLETED', 'FAILED')),
  error_message text,
  created_at timestamptz not null default now()
);

create index if not exists idx_ai_runs_case on public.ai_runs(case_id);
create index if not exists idx_ai_runs_org on public.ai_runs(organization_id);

-- Audit log: security-relevant events (no sensitive content)
create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete set null,
  case_id uuid references public.cases(id) on delete set null,
  actor_id uuid references auth.users(id),
  action text not null, -- login, logout, document.upload, document.view, ...
  resource_type text,
  resource_id text,
  ip_address inet,
  user_agent text,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_org on public.audit_events(organization_id, created_at desc);
create index if not exists idx_audit_case on public.audit_events(case_id);
