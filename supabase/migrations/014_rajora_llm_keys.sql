-- ============================================================
-- 014: Rajora LLM Keys & Row-Level Security
-- Integration with Rajora AI Private LLM (RAJORA-SOP-AI-2026-04)
-- ============================================================

-- Table for managing Rajora LLM API keys
create table if not exists public.rajora_llm_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  key_hash text unique not null,
  key_prefix text not null,
  label text,
  active boolean default true not null,
  created_at timestamptz default now() not null,
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Indexes for lookup and isolation
create index if not exists idx_rajora_llm_keys_org on public.rajora_llm_keys(org_id);
create index if not exists idx_rajora_llm_keys_user on public.rajora_llm_keys(user_id);
create unique index if not exists idx_rajora_llm_keys_active_hash on public.rajora_llm_keys(key_hash) where active = true;

-- Row Level Security
alter table public.rajora_llm_keys enable row level security;

-- Users can select/read their own keys
create policy "users read own rajora keys" on public.rajora_llm_keys
  for select using (user_id = auth.uid());

-- Org admins (OWNER, ADMIN) can manage keys within their organization
create policy "org admins manage rajora keys" on public.rajora_llm_keys
  for all using (public.can_manage_org(org_id))
  with check (public.can_manage_org(org_id));
