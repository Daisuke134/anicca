-- Create usage_sessions table for minute-based billing
create table if not exists public.usage_sessions (
  session_id text primary key,
  user_id text not null,
  started_at timestamptz not null default timezone('utc', now()),
  ended_at timestamptz,
  billed_seconds int default 0,
  billed_minutes int default 0,
  source text not null default 'realtime',
  updated_at timestamptz not null default timezone('utc', now())
);

drop index if exists idx_usage_sessions_user_month;
create index if not exists idx_usage_sessions_user_started_at
  on public.usage_sessions (user_id, started_at);

