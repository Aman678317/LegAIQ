-- ============================================================
-- 011: Platform admin flag + audit helpers (Phase 17)
-- ============================================================

-- Platform administrators can use the /admin API and admin UI.
-- Promote manually after signup:
--   update public.profiles set is_platform_admin = true where email = 'you@firm.com';
alter table public.profiles
  add column if not exists is_platform_admin boolean not null default false;

create or replace function public.is_platform_admin()
returns boolean
language sql
security definer set search_path = public
stable
as $$
  select coalesce(
    (select is_platform_admin from public.profiles where id = auth.uid()),
    false
  )
$$;

-- Allow users to read their own admin flag (RLS already permits own-profile reads)

-- Index for the audit log UI (org + time ordered scans)
create index if not exists idx_audit_action on public.audit_events(action);

-- Index for admin scans of agent runs
create index if not exists idx_agent_runs_started on public.agent_runs(started_at desc);
