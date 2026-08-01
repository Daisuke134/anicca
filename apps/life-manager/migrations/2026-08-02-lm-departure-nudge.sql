-- spec 2026-08-01-lm-daily-organ-design.md §5.2.1 + §5.2.2 (#2c).
--
-- The departure push is a Telegram ladder (T-25/-10/-5/0/+3/+7), and §5.2.1's rule is that the
-- STOPPING is the product: 停止条件の無い連投は嫌がらせであって製品ではない. This table is where a
-- ladder's position and its stop live in the SAME row, so "may I send" is one write, not a read
-- followed by a decision (D4) — two overlapping 60s ticks lose that race and the user gets doubles.
--
-- D3: one row per EVENT, not per rung. last_level_min decreases monotonically (25 → 10 → 5 → 0 → -3
-- → -7); it is both "how far the ladder got" and the predicate that admits the next rung. Its own
-- table rather than a ride on lm_wake_log, because that table means "we placed a phone call" and its
-- amd_result / answered_at census (machine 17 : human 3, §1.3) must not be polluted by pushes —
-- 信用できない証拠は証拠が無いより悪い, the same reason 2d refuses to log test calls.

CREATE TABLE IF NOT EXISTS public.lm_departure_nudge (
  uid             text        NOT NULL,
  -- '<uid>|<startIso>'. Deliberately WITHOUT the rung: lm_wake_log keys per level because each level
  -- is a separate call, but here the levels are states of one ladder.
  event_key       text        NOT NULL,
  last_level_min  integer     NOT NULL,  -- minutes from departure; positive = before, negative = after
  -- NULL means the ladder is still running. Every claim filters on "acked_at IS NULL", so setting
  -- this column IS the stop — there is no second place to remember to check.
  acked_at        timestamptz,
  ack_reason      text,                  -- tap | call_answered | left_home (left_home awaits #3)
  last_message_id bigint,                -- the Telegram message a tap will edit back into its answered state
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, event_key)
);

-- Every read and write is (uid, event_key) — the primary key already serves them, so no extra index
-- is warranted here (lm_wake_miss needed one only because /status orders by occurred_at).

-- The scheduler uses the service role (bypasses RLS). Enabling RLS with no permissive policy keeps
-- the anon key from reading one user's schedule — same posture as lm_wake_miss and lm_travel_log.
ALTER TABLE public.lm_departure_nudge ENABLE ROW LEVEL SECURITY;
