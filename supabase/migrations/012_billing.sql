-- ============================================================
-- 012: Billing — plans, subscriptions, usage metering
-- No payment processing: metering + limits only. Checkout is an
-- explicit 501 until a payment provider is chosen (no fake transactions).
-- ============================================================

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
-- ENTERPRISE price_inr 0 = custom pricing (handled in UI as "Custom")

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null unique references public.organizations(id) on delete cascade,
  plan_code text not null references public.plans(code),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'PAST_DUE', 'CANCELED', 'TRIALING')),
  current_period_start timestamptz not null default now(),
  current_period_end timestamptz,
  provider text,             -- e.g. 'razorpay' once integrated
  provider_customer_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_subscriptions_org on public.subscriptions(organization_id);

-- Metered usage events: append-only ledger, never a fake charge
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

-- Every new organization starts on the FREE plan automatically
create or replace function public.ensure_free_subscription()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.subscriptions (organization_id, plan_code)
  values (new.id, 'FREE')
  on conflict (organization_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_org_created_subscription on public.organizations;
create trigger on_org_created_subscription
  after insert on public.organizations
  for each row execute function public.ensure_free_subscription();

-- ---------- RLS ----------
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usage_events enable row level security;

-- Plans are public metadata
create policy "anyone can read plans" on public.plans
  for select using (true);

-- Subscription + usage: org members read
create policy "org members read subscription" on public.subscriptions
  for select using (public.is_org_member(organization_id));
create policy "org managers update subscription" on public.subscriptions
  for update using (public.can_manage_org(organization_id));

create policy "org members read usage" on public.usage_events
  for select using (public.is_org_member(organization_id));
