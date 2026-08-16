-- ============================================================
-- 010: Agent runs, tool calls, voice sessions (Phases 13 & 16)
-- ============================================================

-- Agent run accounting: budgets, usage, outcomes (no chain-of-thought)
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

-- Audit log of every agent tool invocation (params truncated, no doc content)
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

-- Voice assistant sessions (Phase 16)
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

-- Voice conversation turns: transcript + spoken answer + citations
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

-- ---------- RLS ----------
alter table public.agent_runs enable row level security;
alter table public.agent_tool_calls enable row level security;
alter table public.voice_sessions enable row level security;
alter table public.voice_turns enable row level security;

-- Agent runs: org members read, system writes
create policy "org members read agent runs" on public.agent_runs
  for select using (public.is_org_member(organization_id));

-- Tool calls: readable via the parent run's org
create policy "org members read tool calls" on public.agent_tool_calls
  for select using (
    exists (
      select 1 from public.agent_runs r
      where r.id = agent_run_id and public.is_org_member(r.organization_id)
    )
  );

-- Voice sessions + turns: case-scoped like other child tables
create policy "case members read voice sessions" on public.voice_sessions
  for select using (public.is_case_member(case_id));
create policy "case members insert voice sessions" on public.voice_sessions
  for insert with check (public.is_case_member(case_id));
create policy "case members update voice sessions" on public.voice_sessions
  for update using (public.is_case_member(case_id));

create policy "case members read voice turns" on public.voice_turns
  for select using (public.is_case_member(case_id));
create policy "case members insert voice turns" on public.voice_turns
  for insert with check (public.is_case_member(case_id));
