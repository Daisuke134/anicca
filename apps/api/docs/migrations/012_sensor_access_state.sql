-- sensor_access_state: iOS sensor integration toggle states
-- Phase-7: Persist user's Sleep/Steps/ScreenTime/Motion toggle preferences
-- Note: This file is intentionally kept free of PL/pgSQL blocks because
-- apps/api/src/lib/migrate.js uses simple semicolon-splitting execution.

create table if not exists public.sensor_access_state (
  user_id uuid primary key,
  screen_time_enabled boolean not null default false,
  sleep_enabled boolean not null default false,
  steps_enabled boolean not null default false,
  motion_enabled boolean not null default false,
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_sensor_access_state_updated_at on public.sensor_access_state(updated_at);

