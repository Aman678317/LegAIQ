-- ============================================================
-- Jurisiva AI — Clean Consolidated Schema (No DO $$ loops)
-- Run this in your Supabase SQL Editor
-- ============================================================

-- 1. EXTENSIONS
create extension if not exists "vector";
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- 2. ORGANIZATIONS, PROFILES, MEMBERSHIPS
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  plan text not null default 'FREE' check (plan in ('FREE', 'PROFESSIONAL', 'FIRM', 'ENTERPRISE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text,
  avatar_url text,
  default_org_id uuid references public.organizations(id) on delete set null,
  is_platform_admin boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('OWNER', 'ADMIN', 'LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')),
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);

create index if not exists idx_memberships_user on public.memberships(user_id);
create index if not exists idx_memberships_org on public.memberships(organization_id);

-- Security helper functions
create or replace function public.user_role_in_org(org_id uuid)
returns text language sql security definer set search_path = public stable as $$
  select role from public.memberships
  where organization_id = org_id and user_id = auth.uid()
$$;

create or replace function public.is_org_member(org_id uuid)
returns boolean language sql security definer set search_path = public stable as $$
  select exists (
    select 1 from public.memberships
    where organization_id = org_id and user_id = auth.uid()
  )
$$;

create or replace function public.can_manage_org(org_id uuid)
returns boolean language sql security definer set search_path = public stable as $$
  select exists (
    select 1 from public.memberships
    where organization_id = org_id and user_id = auth.uid()
      and role in ('OWNER', 'ADMIN')
  )
$$;

create or replace function public.is_platform_admin()
returns boolean language sql security definer set search_path = public stable as $$
  select coalesce(
    (select is_platform_admin from public.profiles where id = auth.uid()),
    false
  )
$$;

-- 3. CASES & PROPERTIES
create table if not exists public.cases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  name text not null,
  case_type text not null default 'OTHER' check (
    case_type in ('PROPERTY', 'CIVIL', 'CRIMINAL', 'COMMERCIAL', 'CORPORATE', 'FAMILY', 'LABOUR', 'TAX', 'OTHER')
  ),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'ARCHIVED', 'CLOSED')),
  jurisdiction_state text,
  jurisdiction_district text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cases_org on public.cases(organization_id);
create index if not exists idx_cases_status on public.cases(status);

create table if not exists public.case_collaborators (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'LAWYER' check (role in ('LAWYER', 'REVIEWER', 'STAFF', 'CLIENT')),
  created_at timestamptz not null default now(),
  unique (case_id, user_id)
);

create table if not exists public.properties (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  name text,
  address text,
  state text,
  district text,
  taluk text,
  village text,
  survey_number text,
  hissa_number text,
  plot_number text,
  khata_number text,
  registration_number text,
  property_id_number text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_properties_case on public.properties(case_id);

create table if not exists public.property_field_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  field_name text not null,
  value text not null,
  verification text not null default 'USER_PROVIDED' check (
    verification in ('USER_PROVIDED', 'DOCUMENT_VERIFIED', 'EXTERNAL_SOURCE_VERIFIED', 'UNVERIFIED')
  ),
  source_document_id uuid,
  source_page integer,
  confidence numeric,
  created_at timestamptz not null default now()
);

create index if not exists idx_pfs_property on public.property_field_sources(property_id);

create or replace function public.is_case_member(case_uuid uuid)
returns boolean language sql security definer set search_path = public stable as $$
  select exists (
    select 1 from public.cases c
    where c.id = case_uuid and public.is_org_member(c.organization_id)
  )
$$;

create or replace function public.can_manage_case(case_uuid uuid)
returns boolean language sql security definer set search_path = public stable as $$
  select exists (
    select 1 from public.cases c
    where c.id = case_uuid and public.can_manage_org(c.organization_id)
  )
$$;

-- 4. DOCUMENTS & JOBS
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  uploaded_by uuid not null references auth.users(id),
  file_name text not null,
  file_type text not null,
  file_size bigint not null,
  storage_path text not null,
  document_type text,
  status text not null default 'UPLOADED' check (
    status in ('UPLOADED', 'VALIDATING', 'PROCESSING', 'OCR_RUNNING', 'EXTRACTING', 'ANALYZING', 'COMPLETED', 'FAILED')
  ),
  page_count integer,
  language text,
  ocr_confidence numeric,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_documents_case on public.documents(case_id);
create index if not exists idx_documents_status on public.documents(status);

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  text text,
  language text,
  confidence numeric,
  bounding_boxes jsonb,
  processing_version text,
  created_at timestamptz not null default now(),
  unique (document_id, page_number)
);

create index if not exists idx_pages_document on public.document_pages(document_id);

create table if not exists public.page_translations (
  id uuid primary key default gen_random_uuid(),
  page_id uuid not null references public.document_pages(id) on delete cascade,
  target_language text not null,
  translated_text text not null,
  provider text,
  created_at timestamptz not null default now(),
  unique (page_id, target_language)
);

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  job_type text not null,
  state text not null default 'QUEUED' check (
    state in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')
  ),
  progress integer not null default 0,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  payload jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_jobs_state on public.jobs(state);
create index if not exists idx_jobs_document on public.jobs(document_id);
create index if not exists idx_jobs_case on public.jobs(case_id);

create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  actor_id uuid references auth.users(id),
  event_type text not null,
  description text not null,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_activity_case on public.activity_events(case_id, created_at desc);

-- 5. EXTRACTION, ENTITIES, CHUNKS, CHAT
create table if not exists public.extracted_entities (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  entity_type text not null,
  value text not null,
  normalized_value text,
  source_text text not null,
  confidence numeric not null default 0.0,
  verification text not null default 'UNVERIFIED' check (
    verification in ('USER_PROVIDED', 'DOCUMENT_VERIFIED', 'EXTERNAL_SOURCE_VERIFIED', 'UNVERIFIED')
  ),
  created_at timestamptz not null default now()
);

create index if not exists idx_entities_case on public.extracted_entities(case_id);
create index if not exists idx_entities_doc on public.extracted_entities(document_id);
create index if not exists idx_entities_type on public.extracted_entities(entity_type);

create table if not exists public.persons (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  full_name text not null,
  normalized_name text not null,
  father_name text,
  mother_name text,
  aliases text[],
  created_at timestamptz not null default now()
);

create index if not exists idx_persons_case on public.persons(case_id);
create index if not exists idx_persons_norm on public.persons(normalized_name);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(1536),
  token_count integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_chunks_case on public.document_chunks(case_id);
create index if not exists idx_chunks_doc on public.document_chunks(document_id);
create index if not exists idx_chunks_fts on public.document_chunks using gin (to_tsvector('simple', content));

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id),
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  citations jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_chat_case on public.chat_messages(case_id, created_at);

-- 6. OWNERSHIP GRAPH, TIMELINE, RISKS
create table if not exists public.ownership_nodes (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  node_type text not null check (node_type in ('PERSON', 'PROPERTY', 'DOCUMENT', 'TRANSACTION')),
  label text not null,
  ref_id uuid,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_onodes_case on public.ownership_nodes(case_id);

create table if not exists public.ownership_edges (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  source_id uuid not null references public.ownership_nodes(id) on delete cascade,
  target_id uuid not null references public.ownership_nodes(id) on delete cascade,
  edge_type text not null check (
    edge_type in ('OWNED', 'TRANSFERRED', 'INHERITED', 'GIFTED', 'MORTGAGED', 'RELEASED', 'PARTITIONED')
  ),
  event_date date,
  evidence jsonb not null,
  confidence numeric not null default 0.0,
  created_at timestamptz not null default now()
);

create index if not exists idx_oedges_case on public.ownership_edges(case_id);
create index if not exists idx_oedges_source on public.ownership_edges(source_id);
create index if not exists idx_oedges_target on public.ownership_edges(target_id);

create table if not exists public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  event_date date,
  sort_date date,
  party text,
  transaction_type text not null,
  description text not null,
  document_id uuid references public.documents(id) on delete set null,
  page_number integer,
  evidence_text text,
  confidence numeric,
  created_at timestamptz not null default now()
);

create index if not exists idx_timeline_case on public.timeline_events(case_id, sort_date);

create table if not exists public.comparison_results (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  field_name text not null,
  verdict text not null check (verdict in ('MATCH', 'MISMATCH', 'MISSING', 'UNCERTAIN')),
  values jsonb not null,
  explanation text,
  created_at timestamptz not null default now()
);

create index if not exists idx_comparison_case on public.comparison_results(case_id);

create table if not exists public.risks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  category text not null check (
    category in ('OWNERSHIP', 'TITLE', 'DOCUMENT', 'IDENTITY', 'BOUNDARY', 'REGISTRATION', 'ENCUMBRANCE', 'LITIGATION', 'MISSING_EVIDENCE')
  ),
  level text not null check (level in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  title text not null,
  description text not null,
  evidence jsonb not null,
  compare_with jsonb,
  recommended_action text,
  resolved boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_risks_case on public.risks(case_id);
create index if not exists idx_risks_level on public.risks(level);

create table if not exists public.findings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding text not null,
  explanation text,
  evidence jsonb not null,
  compare_with jsonb,
  risk_level text check (risk_level in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  recommended_action text,
  created_at timestamptz not null default now()
);

create index if not exists idx_findings_case on public.findings(case_id);

-- 7. RESEARCH, DRAFTS, REPORTS, AUDIT
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

create table if not exists public.research_sources (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.research_sessions(id) on delete cascade,
  title text not null,
  url text not null,
  source_type text not null default 'web',
  publisher text,
  published_date date,
  retrieved_at timestamptz not null default now(),
  snippet text,
  verified boolean not null default false,
  content_hash text
);

create index if not exists idx_rsources_session on public.research_sources(session_id);

create table if not exists public.drafts (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  draft_type text not null,
  title text not null,
  content text not null,
  status text not null default 'DRAFT' check (status in ('DRAFT', 'REVIEW', 'FINAL')),
  version integer not null default 1,
  parent_draft_id uuid references public.drafts(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_drafts_case on public.drafts(case_id);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  report_type text not null default 'PROPERTY_DUE_DILIGENCE',
  title text not null,
  status text not null default 'QUEUED' check (
    status in ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')
  ),
  content jsonb,
  storage_path text,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_reports_case on public.reports(case_id);

create table if not exists public.ai_runs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete set null,
  organization_id uuid references public.organizations(id) on delete set null,
  user_id uuid references auth.users(id),
  workflow text not null,
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

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete set null,
  case_id uuid references public.cases(id) on delete set null,
  actor_id uuid references auth.users(id),
  action text not null,
  resource_type text,
  resource_id text,
  ip_address inet,
  user_agent text,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_audit_org on public.audit_events(organization_id, created_at desc);
create index if not exists idx_audit_case on public.audit_events(case_id);
create index if not exists idx_audit_action on public.audit_events(action);

-- 8. AGENTS & VOICE
create table if not exists public.agent_runs (
  id uuid primary key,
  case_id uuid references public.cases(id) on delete set null,
  organization_id uuid references public.organizations(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  agent_name text not null,
  status text not null default 'RUNNING' check (status in ('RUNNING', 'COMPLETED', 'FAILED')),
  llm_calls integer not null default 0,
  prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0,
  estimated_cost_usd numeric,
  elapsed_seconds numeric,
  iterations integer not null default 0,
  error_message text,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_agent_runs_case on public.agent_runs(case_id, started_at desc);
create index if not exists idx_agent_runs_name on public.agent_runs(agent_name);
create index if not exists idx_agent_runs_started on public.agent_runs(started_at desc);

create table if not exists public.agent_tool_calls (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid not null references public.agent_runs(id) on delete cascade,
  tool_name text not null,
  status text not null check (status in ('COMPLETED', 'FAILED')),
  duration_ms integer,
  params jsonb,
  error_message text,
  created_at timestamptz not null default now()
);

create index if not exists idx_tool_calls_run on public.agent_tool_calls(agent_run_id);

create table if not exists public.voice_sessions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  language text not null default 'en',
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'ENDED')),
  created_at timestamptz not null default now(),
  ended_at timestamptz
);

create index if not exists idx_voice_sessions_case on public.voice_sessions(case_id);

create table if not exists public.voice_turns (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.voice_sessions(id) on delete cascade,
  case_id uuid not null references public.cases(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  language text,
  citations jsonb,
  stt_provider text,
  tts_provider text,
  agent_run_id uuid references public.agent_runs(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists idx_voice_turns_session on public.voice_sessions(id);
create index if not exists idx_voice_turns_case on public.voice_turns(case_id, created_at desc);

-- 9. PLANS & BILLING
create table if not exists public.plans (
  code text primary key,
  name text not null,
  price_inr integer not null default 0,
  period text not null default 'month',
  limits jsonb not null default '{}'::jsonb,
  sort_order integer not null default 0,
  created_at timestamptz not null default now()
);

insert into public.plans (code, name, price_inr, limits, sort_order) values
  ('FREE', 'Free', 0, '{"pages_per_month": 25, "ai_runs_per_month": 50, "cases": 1, "seats": 1}', 1),
  ('PROFESSIONAL', 'Professional', 4999, '{"pages_per_month": 500, "ai_runs_per_month": 2000, "cases": null, "seats": 1}', 2),
  ('FIRM', 'Firm', 24999, '{"pages_per_month": 3000, "ai_runs_per_month": 12000, "cases": null, "seats": 5}', 3),
  ('ENTERPRISE', 'Enterprise', 0, '{"pages_per_month": null, "ai_runs_per_month": null, "cases": null, "seats": null}', 4)
on conflict (code) do update
  set name = excluded.name, price_inr = excluded.price_inr, limits = excluded.limits, sort_order = excluded.sort_order;

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references public.organizations(id) on delete cascade,
  plan_code text not null references public.plans(code),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'PAST_DUE', 'CANCELED', 'TRIALING')),
  current_period_start timestamptz not null default now(),
  current_period_end timestamptz,
  provider text,
  provider_customer_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_subscriptions_org on public.subscriptions(organization_id);

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  case_id uuid references public.cases(id) on delete set null,
  metric text not null check (metric in ('pages', 'ai_runs', 'voice_minutes', 'storage_bytes')),
  quantity integer not null default 1,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_usage_org_metric on public.usage_events(organization_id, metric, created_at desc);

-- 10. RPC FUNCTIONS
create or replace function public.match_document_chunks(
  p_case_id uuid,
  p_query_embedding vector(1536),
  p_top_k integer default 12
)
returns table (
  id uuid,
  case_id uuid,
  document_id uuid,
  document_name text,
  page_number integer,
  chunk_index integer,
  content text,
  similarity float
)
language sql stable as $$
  select
    c.id, c.case_id, c.document_id,
    d.file_name as document_name,
    c.page_number, c.chunk_index, c.content,
    1 - (c.embedding <=> p_query_embedding) as similarity
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where c.case_id = p_case_id
    and c.embedding is not null
  order by c.embedding <=> p_query_embedding
  limit p_top_k
$$;

create or replace function public.keyword_search_chunks(
  p_case_id uuid,
  p_query text,
  p_top_k integer default 12
)
returns table (
  id uuid,
  case_id uuid,
  document_id uuid,
  document_name text,
  page_number integer,
  chunk_index integer,
  content text,
  rank float
)
language sql stable as $$
  select
    c.id, c.case_id, c.document_id,
    d.file_name as document_name,
    c.page_number, c.chunk_index, c.content,
    ts_rank(to_tsvector('simple', c.content), websearch_to_tsquery('simple', p_query)) as rank
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where c.case_id = p_case_id
    and to_tsvector('simple', c.content) @@ websearch_to_tsquery('simple', p_query)
  order by rank desc
  limit p_top_k
$$;

create or replace function public.get_risk_counts(p_case_id uuid)
returns json language sql stable as $$
  select coalesce(json_agg(t), '[]'::json) from (
    select level, count(*) as count
    from public.risks
    where case_id = p_case_id and not resolved
    group by level
  ) t
$$;

-- 11. STORAGE BUCKETS
insert into storage.buckets (id, name, public)
values ('case-documents', 'case-documents', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('case-reports', 'case-reports', false)
on conflict (id) do nothing;

-- 12. AUTOMATIC USER & ORG SETUP TRIGGER
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare
  new_org_id uuid;
  user_full_name text;
  base_slug text;
begin
  user_full_name := coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1));
  base_slug := lower(regexp_replace(split_part(new.email, '@', 1), '[^a-zA-Z0-9]', '-', 'g')) || '-' || substring(new.id::text from 1 for 8);

  -- Create profile
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, user_full_name)
  on conflict (id) do update
  set email = excluded.email, full_name = coalesce(public.profiles.full_name, excluded.full_name);

  -- Check if user already has an org
  select organization_id into new_org_id
  from public.memberships
  where user_id = new.id
  limit 1;

  -- If not, create default org
  if new_org_id is null then
    insert into public.organizations (name, slug)
    values (user_full_name || '''s Workspace', base_slug)
    returning id into new_org_id;

    insert into public.memberships (organization_id, user_id, role)
    values (new_org_id, new.id, 'OWNER')
    on conflict do nothing;

    insert into public.subscriptions (organization_id, plan_code)
    values (new_org_id, 'FREE')
    on conflict do nothing;
  end if;

  -- Link default_org_id
  update public.profiles
  set default_org_id = new_org_id
  where id = new.id;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 13. ROW LEVEL SECURITY (RLS)
alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.memberships enable row level security;
alter table public.cases enable row level security;
alter table public.case_collaborators enable row level security;
alter table public.properties enable row level security;
alter table public.property_field_sources enable row level security;
alter table public.documents enable row level security;
alter table public.document_pages enable row level security;
alter table public.page_translations enable row level security;
alter table public.jobs enable row level security;
alter table public.activity_events enable row level security;
alter table public.extracted_entities enable row level security;
alter table public.persons enable row level security;
alter table public.document_chunks enable row level security;
alter table public.chat_messages enable row level security;
alter table public.ownership_nodes enable row level security;
alter table public.ownership_edges enable row level security;
alter table public.timeline_events enable row level security;
alter table public.comparison_results enable row level security;
alter table public.risks enable row level security;
alter table public.findings enable row level security;
alter table public.research_sessions enable row level security;
alter table public.research_sources enable row level security;
alter table public.drafts enable row level security;
alter table public.reports enable row level security;
alter table public.ai_runs enable row level security;
alter table public.audit_events enable row level security;
alter table public.agent_runs enable row level security;
alter table public.agent_tool_calls enable row level security;
alter table public.voice_sessions enable row level security;
alter table public.voice_turns enable row level security;
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usage_events enable row level security;

-- Profiles
create policy "read own profile" on public.profiles for select using (auth.uid() = id);
create policy "update own profile" on public.profiles for update using (auth.uid() = id);

-- Organizations
create policy "read own orgs" on public.organizations for select using (public.is_org_member(id));
create policy "create org" on public.organizations for insert with check (auth.uid() is not null);
create policy "update org if manager" on public.organizations for update using (public.can_manage_org(id));

-- Memberships
create policy "read memberships of own orgs" on public.memberships for select using (public.is_org_member(organization_id));
create policy "insert own membership" on public.memberships for insert with check (auth.uid() = user_id or public.can_manage_org(organization_id));
create policy "manage memberships if admin" on public.memberships for all using (public.can_manage_org(organization_id)) with check (public.can_manage_org(organization_id));

-- Cases
create policy "read cases in own org" on public.cases for select using (public.is_org_member(organization_id));
create policy "create case in own org" on public.cases for insert with check (public.is_org_member(organization_id));
create policy "update case if org member" on public.cases for update using (public.is_org_member(organization_id));
create policy "delete case if admin" on public.cases for delete using (public.can_manage_org(organization_id));

-- Case Collaborators
create policy "case members read collaborators" on public.case_collaborators for select using (public.is_case_member(case_id));
create policy "case members insert collaborators" on public.case_collaborators for insert with check (public.is_case_member(case_id));
create policy "case members update collaborators" on public.case_collaborators for update using (public.is_case_member(case_id));
create policy "case admins delete collaborators" on public.case_collaborators for delete using (public.can_manage_case(case_id));

-- Properties
create policy "case members read properties" on public.properties for select using (public.is_case_member(case_id));
create policy "case members insert properties" on public.properties for insert with check (public.is_case_member(case_id));
create policy "case members update properties" on public.properties for update using (public.is_case_member(case_id));
create policy "case admins delete properties" on public.properties for delete using (public.can_manage_case(case_id));

-- Documents
create policy "case members read documents" on public.documents for select using (public.is_case_member(case_id));
create policy "case members insert documents" on public.documents for insert with check (public.is_case_member(case_id));
create policy "case members update documents" on public.documents for update using (public.is_case_member(case_id));
create policy "case admins delete documents" on public.documents for delete using (public.can_manage_case(case_id));

-- Jobs
create policy "case members read jobs" on public.jobs for select using (public.is_case_member(case_id));
create policy "case members insert jobs" on public.jobs for insert with check (public.is_case_member(case_id));
create policy "case members update jobs" on public.jobs for update using (public.is_case_member(case_id));
create policy "case admins delete jobs" on public.jobs for delete using (public.can_manage_case(case_id));

-- Activity Events
create policy "case members read activity" on public.activity_events for select using (public.is_case_member(case_id));
create policy "case members insert activity" on public.activity_events for insert with check (public.is_case_member(case_id));
create policy "case members update activity" on public.activity_events for update using (public.is_case_member(case_id));
create policy "case admins delete activity" on public.activity_events for delete using (public.can_manage_case(case_id));

-- Extracted Entities
create policy "case members read entities" on public.extracted_entities for select using (public.is_case_member(case_id));
create policy "case members insert entities" on public.extracted_entities for insert with check (public.is_case_member(case_id));
create policy "case members update entities" on public.extracted_entities for update using (public.is_case_member(case_id));
create policy "case admins delete entities" on public.extracted_entities for delete using (public.can_manage_case(case_id));

-- Persons
create policy "case members read persons" on public.persons for select using (public.is_case_member(case_id));
create policy "case members insert persons" on public.persons for insert with check (public.is_case_member(case_id));
create policy "case members update persons" on public.persons for update using (public.is_case_member(case_id));
create policy "case admins delete persons" on public.persons for delete using (public.can_manage_case(case_id));

-- Document Chunks
create policy "case members read chunks" on public.document_chunks for select using (public.is_case_member(case_id));
create policy "case members insert chunks" on public.document_chunks for insert with check (public.is_case_member(case_id));
create policy "case members update chunks" on public.document_chunks for update using (public.is_case_member(case_id));
create policy "case admins delete chunks" on public.document_chunks for delete using (public.can_manage_case(case_id));

-- Chat Messages
create policy "case members read chat" on public.chat_messages for select using (public.is_case_member(case_id));
create policy "case members insert chat" on public.chat_messages for insert with check (public.is_case_member(case_id));
create policy "case members update chat" on public.chat_messages for update using (public.is_case_member(case_id));
create policy "case admins delete chat" on public.chat_messages for delete using (public.can_manage_case(case_id));

-- Ownership Nodes
create policy "case members read onodes" on public.ownership_nodes for select using (public.is_case_member(case_id));
create policy "case members insert onodes" on public.ownership_nodes for insert with check (public.is_case_member(case_id));
create policy "case members update onodes" on public.ownership_nodes for update using (public.is_case_member(case_id));
create policy "case admins delete onodes" on public.ownership_nodes for delete using (public.can_manage_case(case_id));

-- Ownership Edges
create policy "case members read oedges" on public.ownership_edges for select using (public.is_case_member(case_id));
create policy "case members insert oedges" on public.ownership_edges for insert with check (public.is_case_member(case_id));
create policy "case members update oedges" on public.ownership_edges for update using (public.is_case_member(case_id));
create policy "case admins delete oedges" on public.ownership_edges for delete using (public.can_manage_case(case_id));

-- Timeline Events
create policy "case members read timeline" on public.timeline_events for select using (public.is_case_member(case_id));
create policy "case members insert timeline" on public.timeline_events for insert with check (public.is_case_member(case_id));
create policy "case members update timeline" on public.timeline_events for update using (public.is_case_member(case_id));
create policy "case admins delete timeline" on public.timeline_events for delete using (public.can_manage_case(case_id));

-- Comparison Results
create policy "case members read comparison" on public.comparison_results for select using (public.is_case_member(case_id));
create policy "case members insert comparison" on public.comparison_results for insert with check (public.is_case_member(case_id));
create policy "case members update comparison" on public.comparison_results for update using (public.is_case_member(case_id));
create policy "case admins delete comparison" on public.comparison_results for delete using (public.can_manage_case(case_id));

-- Risks
create policy "case members read risks" on public.risks for select using (public.is_case_member(case_id));
create policy "case members insert risks" on public.risks for insert with check (public.is_case_member(case_id));
create policy "case members update risks" on public.risks for update using (public.is_case_member(case_id));
create policy "case admins delete risks" on public.risks for delete using (public.can_manage_case(case_id));

-- Findings
create policy "case members read findings" on public.findings for select using (public.is_case_member(case_id));
create policy "case members insert findings" on public.findings for insert with check (public.is_case_member(case_id));
create policy "case members update findings" on public.findings for update using (public.is_case_member(case_id));
create policy "case admins delete findings" on public.findings for delete using (public.can_manage_case(case_id));

-- Research Sessions & Sources
create policy "case members read research" on public.research_sessions for select using (public.is_case_member(case_id));
create policy "case members insert research" on public.research_sessions for insert with check (public.is_case_member(case_id));
create policy "case members update research" on public.research_sessions for update using (public.is_case_member(case_id));
create policy "case admins delete research" on public.research_sessions for delete using (public.can_manage_case(case_id));
create policy "case members read sources" on public.research_sources for select using (exists (select 1 from public.research_sessions s where s.id = session_id and public.is_case_member(s.case_id)));

-- Drafts
create policy "case members read drafts" on public.drafts for select using (public.is_case_member(case_id));
create policy "case members insert drafts" on public.drafts for insert with check (public.is_case_member(case_id));
create policy "case members update drafts" on public.drafts for update using (public.is_case_member(case_id));
create policy "case admins delete drafts" on public.drafts for delete using (public.can_manage_case(case_id));

-- Reports
create policy "case members read reports" on public.reports for select using (public.is_case_member(case_id));
create policy "case members insert reports" on public.reports for insert with check (public.is_case_member(case_id));
create policy "case members update reports" on public.reports for update using (public.is_case_member(case_id));
create policy "case admins delete reports" on public.reports for delete using (public.can_manage_case(case_id));

-- Property field sources
create policy "case members read pfs" on public.property_field_sources for select using (public.is_case_member((select p.case_id from public.properties p where p.id = property_id)));
create policy "case members insert pfs" on public.property_field_sources for insert with check (public.is_case_member((select p.case_id from public.properties p where p.id = property_id)));
create policy "case members update pfs" on public.property_field_sources for update using (public.is_case_member((select p.case_id from public.properties p where p.id = property_id)));
create policy "case admins delete pfs" on public.property_field_sources for delete using (public.can_manage_case((select p.case_id from public.properties p where p.id = property_id)));

-- Document pages
create policy "case members read pages" on public.document_pages for select using (public.is_case_member((select d.case_id from public.documents d where d.id = document_id)));
create policy "case members insert pages" on public.document_pages for insert with check (public.is_case_member((select d.case_id from public.documents d where d.id = document_id)));
create policy "case members update pages" on public.document_pages for update using (public.is_case_member((select d.case_id from public.documents d where d.id = document_id)));
create policy "case admins delete pages" on public.document_pages for delete using (public.can_manage_case((select d.case_id from public.documents d where d.id = document_id)));

-- Page translations
create policy "case members read translations" on public.page_translations for select using (public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id)));
create policy "case members insert translations" on public.page_translations for insert with check (public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id)));
create policy "case members update translations" on public.page_translations for update using (public.is_case_member((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id)));
create policy "case admins delete translations" on public.page_translations for delete using (public.can_manage_case((select d.case_id from public.documents d join public.document_pages p on p.document_id = d.id where p.id = page_id)));

-- AI Runs & Audit
create policy "org members read ai runs" on public.ai_runs for select using (public.is_org_member(organization_id));
create policy "org admins read audit" on public.audit_events for select using (public.can_manage_org(organization_id));
create policy "system inserts audit" on public.audit_events for insert with check (auth.uid() is not null);

-- Agent Runs & Voice
create policy "org members read agent runs" on public.agent_runs for select using (public.is_org_member(organization_id));
create policy "org members read tool calls" on public.agent_tool_calls for select using (exists (select 1 from public.agent_runs r where r.id = agent_run_id and public.is_org_member(r.organization_id)));
create policy "case members read voice sessions" on public.voice_sessions for select using (public.is_case_member(case_id));
create policy "case members insert voice sessions" on public.voice_sessions for insert with check (public.is_case_member(case_id));
create policy "case members update voice sessions" on public.voice_sessions for update using (public.is_case_member(case_id));
create policy "case members read voice turns" on public.voice_turns for select using (public.is_case_member(case_id));
create policy "case members insert voice turns" on public.voice_turns for insert with check (public.is_case_member(case_id));

-- Plans & Subscriptions
create policy "anyone can read plans" on public.plans for select using (true);
create policy "org members read subscription" on public.subscriptions for select using (public.is_org_member(organization_id));
create policy "org managers update subscription" on public.subscriptions for update using (public.can_manage_org(organization_id));
create policy "org members read usage" on public.usage_events for select using (public.is_org_member(organization_id));

-- 14. SYNC EXISTING USERS & ORGS (Pure SQL)
update auth.users set email_confirmed_at = now() where email_confirmed_at is null;

insert into public.profiles (id, email, full_name, is_platform_admin)
select id, email, coalesce(raw_user_meta_data->>'full_name', split_part(email, '@', 1)), true
from auth.users
on conflict (id) do update set is_platform_admin = true;

insert into public.organizations (name, slug)
select 
  coalesce(u.raw_user_meta_data->>'full_name', split_part(u.email, '@', 1)) || '''s Workspace',
  lower(regexp_replace(split_part(u.email, '@', 1), '[^a-zA-Z0-9]', '-', 'g')) || '-' || substring(u.id::text from 1 for 8)
from auth.users u
where not exists (select 1 from public.memberships m where m.user_id = u.id)
on conflict (slug) do nothing;

insert into public.memberships (organization_id, user_id, role)
select o.id, u.id, 'OWNER'
from auth.users u
join public.organizations o on o.slug = lower(regexp_replace(split_part(u.email, '@', 1), '[^a-zA-Z0-9]', '-', 'g')) || '-' || substring(u.id::text from 1 for 8)
where not exists (select 1 from public.memberships m where m.user_id = u.id)
on conflict (organization_id, user_id) do nothing;

update public.profiles p
set default_org_id = m.organization_id
from public.memberships m
where m.user_id = p.id and p.default_org_id is null;

insert into public.subscriptions (organization_id, plan_code)
select id, 'FREE'
from public.organizations
on conflict (organization_id) do nothing;
