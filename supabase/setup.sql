-- ============================================================
-- Jurisiva AI — Fast All-in-One Database Setup
-- ============================================================

create extension if not exists "vector";
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Core Auth & Orgs
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  plan text not null default 'FREE',
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
  role text not null default 'OWNER',
  created_at timestamptz not null default now(),
  unique (organization_id, user_id)
);

-- Cases & Properties
create table if not exists public.cases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  name text not null,
  case_type text not null default 'PROPERTY',
  status text not null default 'ACTIVE',
  jurisdiction_state text,
  jurisdiction_district text,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.case_collaborators (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'LAWYER',
  created_at timestamptz not null default now(),
  unique (case_id, user_id)
);

create table if not exists public.properties (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  name text, address text, state text, district text, taluk text, village text,
  survey_number text, hissa_number text, plot_number text, khata_number text,
  registration_number text, property_id_number text, description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.property_field_sources (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  field_name text not null, value text not null, verification text not null default 'USER_PROVIDED',
  source_document_id uuid, source_page integer, confidence numeric,
  created_at timestamptz not null default now()
);

-- Documents & Pages
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  uploaded_by uuid not null references auth.users(id),
  file_name text not null, file_type text not null, file_size bigint not null,
  storage_path text not null, document_type text, status text not null default 'UPLOADED',
  page_count integer, language text, ocr_confidence numeric, error_message text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null, text text, language text, confidence numeric,
  bounding_boxes jsonb, processing_version text,
  created_at timestamptz not null default now(), unique (document_id, page_number)
);

create table if not exists public.page_translations (
  id uuid primary key default gen_random_uuid(),
  page_id uuid not null references public.document_pages(id) on delete cascade,
  target_language text not null, translated_text text not null, provider text,
  created_at timestamptz not null default now(), unique (page_id, target_language)
);

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  job_type text not null, state text not null default 'QUEUED',
  progress integer not null default 0, attempts integer not null default 0,
  max_attempts integer not null default 3, payload jsonb, error_message text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  actor_id uuid references auth.users(id), event_type text not null, description text not null,
  metadata jsonb, created_at timestamptz not null default now()
);

-- Extraction & Vectors
create table if not exists public.extracted_entities (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null, entity_type text not null, value text not null,
  normalized_value text, source_text text not null, confidence numeric not null default 0.0,
  verification text not null default 'UNVERIFIED', created_at timestamptz not null default now()
);

create table if not exists public.persons (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  full_name text not null, normalized_name text not null, father_name text,
  mother_name text, aliases text[], created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  page_number integer not null, chunk_index integer not null, content text not null,
  embedding vector(1536), token_count integer, created_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id), role text not null,
  content text not null, citations jsonb, created_at timestamptz not null default now()
);

-- Analysis & Risks
create table if not exists public.ownership_nodes (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  node_type text not null, label text not null, ref_id uuid, metadata jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.ownership_edges (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  source_id uuid not null references public.ownership_nodes(id) on delete cascade,
  target_id uuid not null references public.ownership_nodes(id) on delete cascade,
  edge_type text not null, event_date date, evidence jsonb not null,
  confidence numeric not null default 0.0, created_at timestamptz not null default now()
);

create table if not exists public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  event_date date, sort_date date, party text, transaction_type text not null,
  description text not null, document_id uuid references public.documents(id) on delete set null,
  page_number integer, evidence_text text, confidence numeric, created_at timestamptz not null default now()
);

create table if not exists public.comparison_results (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  field_name text not null, verdict text not null, values jsonb not null,
  explanation text, created_at timestamptz not null default now()
);

create table if not exists public.risks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  category text not null, level text not null, title text not null, description text not null,
  evidence jsonb not null, compare_with jsonb, recommended_action text,
  resolved boolean not null default false, created_at timestamptz not null default now()
);

create table if not exists public.findings (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  finding text not null, explanation text, evidence jsonb not null,
  compare_with jsonb, risk_level text, recommended_action text, created_at timestamptz not null default now()
);

-- Research & Drafts
create table if not exists public.research_sessions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id), question text not null, jurisdiction text,
  status text not null default 'QUEUED', answer text, model_used text,
  created_at timestamptz not null default now(), completed_at timestamptz
);

create table if not exists public.research_sources (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.research_sessions(id) on delete cascade,
  title text not null, url text not null, source_type text not null default 'web',
  publisher text, published_date date, retrieved_at timestamptz not null default now(),
  snippet text, verified boolean not null default false, content_hash text
);

create table if not exists public.drafts (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id), draft_type text not null,
  title text not null, content text not null, status text not null default 'DRAFT',
  version integer not null default 1, parent_draft_id uuid references public.drafts(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  created_by uuid not null references auth.users(id), report_type text not null default 'PROPERTY_DUE_DILIGENCE',
  title text not null, status text not null default 'QUEUED', content jsonb, storage_path text,
  error_message text, created_at timestamptz not null default now(), completed_at timestamptz
);

create table if not exists public.ai_runs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete set null,
  organization_id uuid references public.organizations(id) on delete set null,
  user_id uuid references auth.users(id), workflow text not null, provider text not null,
  model text not null, model_version text, latency_ms integer, prompt_tokens integer,
  completion_tokens integer, estimated_cost_usd numeric, status text not null default 'RUNNING',
  error_message text, created_at timestamptz not null default now()
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references public.organizations(id) on delete set null,
  case_id uuid references public.cases(id) on delete set null,
  actor_id uuid references auth.users(id), action text not null, resource_type text,
  resource_id text, ip_address inet, user_agent text, metadata jsonb, created_at timestamptz not null default now()
);

create table if not exists public.agent_runs (
  id uuid primary key,
  case_id uuid references public.cases(id) on delete set null,
  organization_id uuid references public.organizations(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  agent_name text not null, status text not null default 'RUNNING',
  llm_calls integer not null default 0, prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0, estimated_cost_usd numeric,
  elapsed_seconds numeric, iterations integer not null default 0, error_message text,
  started_at timestamptz not null default now(), completed_at timestamptz
);

create table if not exists public.agent_tool_calls (
  id uuid primary key default gen_random_uuid(),
  agent_run_id uuid not null references public.agent_runs(id) on delete cascade,
  tool_name text not null, status text not null, duration_ms integer, params jsonb,
  error_message text, created_at timestamptz not null default now()
);

create table if not exists public.voice_sessions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  language text not null default 'en', status text not null default 'ACTIVE',
  created_at timestamptz not null default now(), ended_at timestamptz
);

create table if not exists public.voice_turns (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.voice_sessions(id) on delete cascade,
  case_id uuid not null references public.cases(id) on delete cascade,
  role text not null, content text not null, language text, citations jsonb,
  stt_provider text, tts_provider text, agent_run_id uuid references public.agent_runs(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists public.plans (
  code text primary key, name text not null, price_inr integer not null default 0,
  period text not null default 'month', limits jsonb not null default '{}'::jsonb,
  sort_order integer not null default 0, created_at timestamptz not null default now()
);

insert into public.plans (code, name, price_inr, limits, sort_order) values
  ('FREE', 'Free', 0, '{"pages_per_month": 25, "ai_runs_per_month": 50, "cases": 1, "seats": 1}', 1)
on conflict (code) do nothing;

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references public.organizations(id) on delete cascade,
  plan_code text not null references public.plans(code),
  status text not null default 'ACTIVE', current_period_start timestamptz not null default now(),
  current_period_end timestamptz, provider text, provider_customer_id text,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  case_id uuid references public.cases(id) on delete set null,
  metric text not null, quantity integer not null default 1,
  metadata jsonb, created_at timestamptz not null default now()
);

-- Storage buckets
insert into storage.buckets (id, name, public) values ('case-documents', 'case-documents', true) on conflict (id) do nothing;
insert into storage.buckets (id, name, public) values ('case-reports', 'case-reports', true) on conflict (id) do nothing;

-- 10. RPC FUNCTIONS
create or replace function public.match_document_chunks(
  p_case_id uuid, p_query_embedding vector(1536), p_top_k integer default 12
)
returns table (
  id uuid, case_id uuid, document_id uuid, document_name text,
  page_number integer, chunk_index integer, content text, similarity float
)
language sql stable as $$
  select c.id, c.case_id, c.document_id, d.file_name as document_name,
    c.page_number, c.chunk_index, c.content, 1 - (c.embedding <=> p_query_embedding) as similarity
  from public.document_chunks c
  join public.documents d on d.id = c.document_id
  where c.case_id = p_case_id and c.embedding is not null
  order by c.embedding <=> p_query_embedding limit p_top_k
$$;

create or replace function public.get_risk_counts(p_case_id uuid)
returns json language sql stable as $$
  select coalesce(json_agg(t), '[]'::json) from (
    select level, count(*) as count from public.risks
    where case_id = p_case_id and not resolved group by level
  ) t
$$;

-- Enable RLS and permissive policies for all tables
alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.memberships enable row level security;
alter table public.cases enable row level security;
alter table public.properties enable row level security;
alter table public.documents enable row level security;
alter table public.document_pages enable row level security;
alter table public.jobs enable row level security;
alter table public.activity_events enable row level security;
alter table public.extracted_entities enable row level security;
alter table public.persons enable row level security;
alter table public.document_chunks enable row level security;
alter table public.chat_messages enable row level security;
alter table public.risks enable row level security;
alter table public.drafts enable row level security;
alter table public.reports enable row level security;
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;

drop policy if exists "allow_all_orgs" on public.organizations;
create policy "allow_all_orgs" on public.organizations for all using (true) with check (true);

drop policy if exists "allow_all_profiles" on public.profiles;
create policy "allow_all_profiles" on public.profiles for all using (true) with check (true);

drop policy if exists "allow_all_memberships" on public.memberships;
create policy "allow_all_memberships" on public.memberships for all using (true) with check (true);

drop policy if exists "allow_all_cases" on public.cases;
create policy "allow_all_cases" on public.cases for all using (true) with check (true);

drop policy if exists "allow_all_properties" on public.properties;
create policy "allow_all_properties" on public.properties for all using (true) with check (true);

drop policy if exists "allow_all_documents" on public.documents;
create policy "allow_all_documents" on public.documents for all using (true) with check (true);

drop policy if exists "allow_all_pages" on public.document_pages;
create policy "allow_all_pages" on public.document_pages for all using (true) with check (true);

drop policy if exists "allow_all_jobs" on public.jobs;
create policy "allow_all_jobs" on public.jobs for all using (true) with check (true);

drop policy if exists "allow_all_activity" on public.activity_events;
create policy "allow_all_activity" on public.activity_events for all using (true) with check (true);

drop policy if exists "allow_all_entities" on public.extracted_entities;
create policy "allow_all_entities" on public.extracted_entities for all using (true) with check (true);

drop policy if exists "allow_all_persons" on public.persons;
create policy "allow_all_persons" on public.persons for all using (true) with check (true);

drop policy if exists "allow_all_chunks" on public.document_chunks;
create policy "allow_all_chunks" on public.document_chunks for all using (true) with check (true);

drop policy if exists "allow_all_chat" on public.chat_messages;
create policy "allow_all_chat" on public.chat_messages for all using (true) with check (true);

drop policy if exists "allow_all_risks" on public.risks;
create policy "allow_all_risks" on public.risks for all using (true) with check (true);

drop policy if exists "allow_all_drafts" on public.drafts;
create policy "allow_all_drafts" on public.drafts for all using (true) with check (true);

drop policy if exists "allow_all_reports" on public.reports;
create policy "allow_all_reports" on public.reports for all using (true) with check (true);

drop policy if exists "allow_all_plans" on public.plans;
create policy "allow_all_plans" on public.plans for select using (true);

drop policy if exists "allow_all_subs" on public.subscriptions;
create policy "allow_all_subs" on public.subscriptions for all using (true) with check (true);

-- SYNC ALL REGISTERED USERS & WORKSPACES
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
