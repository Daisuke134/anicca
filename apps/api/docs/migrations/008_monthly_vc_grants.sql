-- Create monthly_vc_grants table to track VC grants and prevent duplicates
create table if not exists public.monthly_vc_grants (
  user_id text not null,
  grant_month date not null,
  reason text not null check (reason in ('free', 'annual')),
  minutes int not null,
  granted_at timestamptz not null default timezone('utc', now()),
  primary key (user_id, grant_month, reason)
);

create index if not exists idx_monthly_vc_grants_month on public.monthly_vc_grants (grant_month);

