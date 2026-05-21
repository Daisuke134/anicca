-- v0.3 JSONB GIN indexes (jsonb_path_ops)
-- Keep this file DDL-only (no PL/pgSQL blocks).

create index if not exists idx_nudge_events_state_gin
  on public.nudge_events using gin (state jsonb_path_ops);

create index if not exists idx_nudge_outcomes_short_term_gin
  on public.nudge_outcomes using gin (short_term jsonb_path_ops);

create index if not exists idx_daily_metrics_mind_summary_gin
  on public.daily_metrics using gin (mind_summary jsonb_path_ops);

create index if not exists idx_daily_metrics_activity_summary_gin
  on public.daily_metrics using gin (activity_summary jsonb_path_ops);

create index if not exists idx_daily_metrics_insights_gin
  on public.daily_metrics using gin (insights jsonb_path_ops);










