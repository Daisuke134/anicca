-- Canonical schema for the fleet registry table. Matches the LIVE schema (verified via
-- information_schema 2026-06-29). The telemetry poster signs a 19-key message; EVERY one of those
-- keys must be a column here or telemetry-store.upsertInstance silently drops it (REQ-13: do NOT
-- assume columns). CREATE for fresh DBs + idempotent ALTERs so existing DBs converge to this shape.
create table if not exists instances (
  id text primary key,                -- wallet address (lowercase) = identity (signer must match)
  ts bigint not null,                 -- last accepted unix ts (monotonic, replay guard)
  host text not null, geo text not null,
  model_live text not null, model_tier text not null,
  net_worth_usd double precision not null, revenue_mo_usd double precision not null,
  burn_day_usd double precision not null, runway_days int not null,
  status text not null,
  -- fleet-identity (added 2026-06-29): how the body is funded / where it runs / which brain backend
  funding text,                       -- 'human' | 'self'
  env text,                           -- 'local' | 'cloud'
  brain text,                         -- 'claude-p' (Claude sub) | 'proxy' (self-pay x402, incl free models)
  -- revenue + activity (posted by telemetry-poster.mjs)
  daily_revenue_usd double precision, monthly_revenue_usd double precision,
  revenue_by_source jsonb,            -- per-source P&L
  breakdown jsonb,                    -- net-worth position breakdown
  log jsonb,                          -- recent activity log (last 20 ledger lines) — drives the live-log card
  updated_at timestamptz not null default now()
);
-- Idempotent convergence for already-created tables (drift fix):
alter table instances add column if not exists funding text;
alter table instances add column if not exists env text;
alter table instances add column if not exists brain text;
alter table instances add column if not exists daily_revenue_usd double precision;
alter table instances add column if not exists monthly_revenue_usd double precision;
alter table instances add column if not exists revenue_by_source jsonb;
alter table instances add column if not exists breakdown jsonb;
alter table instances add column if not exists log jsonb;
-- RLS: service-role key bypasses RLS (the function uses it); anon key cannot read/write directly.
alter table instances enable row level security;
