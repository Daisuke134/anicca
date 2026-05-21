-- v0.3 core tables (Prisma schema: apps/api/prisma/schema.prisma)
-- Note: This file is intentionally kept free of PL/pgSQL blocks because
-- apps/api/src/lib/migrate.js uses simple semicolon-splitting execution.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- profiles / user_settings
-- NOTE: v0.3 の新規テーブル（user_traits 等）は profiles(id) を UUID の権威として参照するため、
-- migrate.js の自動適用範囲（006/007/008/010/011）に profiles/user_settings の DDL も含める。
-- 一次情報: apps/api/supabase/migrations/20251106_create_profiles.sql
create table if not exists public.profiles (
    id uuid primary key,
    email text unique,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists profiles_apple_user_id_idx
    on public.profiles ((metadata->>'apple_user_id'))
    where metadata ? 'apple_user_id';

create table if not exists public.user_settings (
    user_id uuid primary key references public.profiles(id) on delete cascade,
    language text not null default 'ja',
    timezone text not null default 'Asia/Tokyo',
    notifications_enabled boolean not null default true,
    preferences jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

-- refresh_tokens (mobile auth)
-- NOTE: apps/api/src/services/auth/refreshStore.js が refresh_tokens を参照するため、
-- 新規環境でも自動適用されるよう 010 に含める（既に存在する場合は IF NOT EXISTS で無害）。
create table if not exists public.refresh_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  token_hash text not null,
  device_id text not null,
  user_agent text,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  rotated_from uuid,
  revoked_at timestamptz,
  last_used_at timestamptz,
  reuse_detected boolean default false
);

create index if not exists idx_refresh_tokens_user on public.refresh_tokens(user_id);
create index if not exists idx_refresh_tokens_hash on public.refresh_tokens(token_hash);

-- user_traits: ideals/struggles/big5/nudge settings
create table if not exists public.user_traits (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  ideals text[] not null default '{}'::text[],
  struggles text[] not null default '{}'::text[],
  big5 jsonb not null default '{}'::jsonb,
  keywords text[] not null default '{}'::text[],
  summary text not null default '',
  nudge_intensity text not null default 'normal',
  sticky_mode boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- daily_metrics: day-level aggregates
create table if not exists public.daily_metrics (
  user_id uuid not null,
  date date not null,
  sleep_duration_min int,
  sleep_start_at timestamptz,
  wake_at timestamptz,
  sns_minutes_total int not null default 0,
  sns_minutes_night int not null default 0,
  steps int not null default 0,
  sedentary_minutes int not null default 0,
  activity_summary jsonb not null default '{}'::jsonb,
  mind_summary jsonb not null default '{}'::jsonb,
  insights jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (user_id, date)
);

create index if not exists idx_daily_metrics_date on public.daily_metrics(date);

-- nudge_events: decision points and chosen actions
create table if not exists public.nudge_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  domain text not null,
  subtype text not null,
  decision_point text not null,
  state jsonb not null,
  action_template text,
  channel text not null,
  sent boolean not null default true,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_nudge_events_user_created_at on public.nudge_events(user_id, created_at);
create index if not exists idx_nudge_events_domain_created_at on public.nudge_events(domain, created_at);

-- nudge_outcomes: rewards and signals
create table if not exists public.nudge_outcomes (
  id uuid primary key default gen_random_uuid(),
  nudge_event_id uuid not null references public.nudge_events(id) on delete cascade,
  reward double precision,
  short_term jsonb not null default '{}'::jsonb,
  ema_score jsonb,
  signals jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_nudge_outcomes_event_id on public.nudge_outcomes(nudge_event_id);

-- feeling_sessions: EMI sessions with EMA yes/no
create table if not exists public.feeling_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  feeling_id text not null,
  topic text,
  action_template text,
  started_at timestamptz not null default timezone('utc', now()),
  ended_at timestamptz,
  ema_better boolean,
  summary text,
  transcript jsonb,
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_feeling_sessions_user_started_at on public.feeling_sessions(user_id, started_at);
create index if not exists idx_feeling_sessions_feeling_started_at on public.feeling_sessions(feeling_id, started_at);

-- habit_logs: priority habit logs (v0.3)
create table if not exists public.habit_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  habit_id text not null,
  occurred_on date not null,
  status text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_habit_logs_user_occurred_on on public.habit_logs(user_id, occurred_on);
create index if not exists idx_habit_logs_habit_occurred_on on public.habit_logs(habit_id, occurred_on);

-- bandit_models: LinTS params
create table if not exists public.bandit_models (
  id uuid primary key default gen_random_uuid(),
  domain text not null,
  version int not null default 1,
  weights jsonb not null,
  covariance jsonb not null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique(domain, version)
);










