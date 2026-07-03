-- Sprint-2 S7: additive migration for the Agents-that-Earn leaderboard.
-- Extends `instances` with the leaderboard columns named in
-- `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md`.
--
-- INVARIANTS
--   - Additive-only. No DROP, no SET NOT NULL: every currently-valid row (base 11 columns)
--     remains valid (sprint-1 R9 back-compat).
--   - Every DDL statement is idempotent (IF NOT EXISTS): running the migration twice is safe.
--   - `telemetry-schema.js` continues to type-check these fields WHEN PRESENT (sprint-1 R9);
--     nothing here changes the runtime validator contract.

alter table instances add column if not exists tags text[];
alter table instances add column if not exists revenue_today_usd double precision;
alter table instances add column if not exists revenue_by_source jsonb;
alter table instances add column if not exists net_worth_src text;
alter table instances add column if not exists earn_src text;
alter table instances add column if not exists last_heartbeat timestamptz;

create index if not exists idx_instances_tags_gin on instances using gin(tags);
