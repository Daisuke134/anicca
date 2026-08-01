-- spec 2026-08-01-lm-daily-organ-design.md §1.2「計測の穴」+ §3 row 1b.
--
-- lm_wake_log records calls we were about to place; releaseWake DELETEs that claim when the dial
-- fails so a later tick can retry. The retry is correct, the erasure is not: it makes "the call that
-- should have rung and did not" invisible rather than failed. This ledger holds exactly those.
--
-- Keyed (uid, event_key) so a failure repeating across 60s ticks refreshes its reason via PostgREST
-- merge-duplicates instead of duplicating. first_seen_at is never written by the app, so it keeps
-- recording when the breakage started even as occurred_at/detail move forward.

CREATE TABLE IF NOT EXISTS public.lm_wake_miss (
  uid           text        NOT NULL,
  event_key     text        NOT NULL,
  event_start   timestamptz,
  due_at        timestamptz,          -- when the call was supposed to ring (departure − level)
  level_min     int,                  -- 10 or 5; NULL when no level ever became due
  reason        text        NOT NULL, -- dial_failed | no_call_before_departure
  detail        text,
  event_summary text,
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  -- §5.4「沈黙で失敗しない」: NULL means the user has not been told yet. A PATCH filtered on
  -- "notified_at IS NULL" is the lock that makes the Telegram notice fire exactly once, even though
  -- the 60s tick keeps retrying (and re-upserting) a failing dial.
  notified_at   timestamptz,
  PRIMARY KEY (uid, event_key)
);
ALTER TABLE public.lm_wake_miss ADD COLUMN IF NOT EXISTS notified_at timestamptz;

-- /status reads the newest row for one user; this is that read.
CREATE INDEX IF NOT EXISTS lm_wake_miss_uid_occurred_idx
  ON public.lm_wake_miss (uid, occurred_at DESC);

-- The scheduler uses the service role (bypasses RLS). Enabling RLS with no permissive policy keeps
-- the anon key from reading one user's missed calls — same posture as lm_travel_log.
ALTER TABLE public.lm_wake_miss ENABLE ROW LEVEL SECURITY;
