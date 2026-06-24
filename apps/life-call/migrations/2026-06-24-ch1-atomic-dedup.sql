-- C-H1 (HARD-1): make TRAVEL + ASK dedup ATOMIC like wake (lm_wake_log unique(uid,event_key)).
-- Race truth (B2 adversary FIND-005): wake is atomic (insert→409); travel/ask were in-memory read-then-write
-- → two concurrent ticks could double-insert a [Travel] block / double-ask. These atomic ledgers fix it:
-- a claim is an INSERT that 409s on a duplicate, so exactly one writer proceeds.

-- 1) ASK: lm_ask_log gets a UNIQUE(uid, event_id) so an ask is claimed by insert (409 = already asked).
--    First collapse any pre-existing duplicates (keep the earliest row), else ADD CONSTRAINT fails.
DELETE FROM public.lm_ask_log a
USING public.lm_ask_log b
WHERE a.ctid > b.ctid AND a.uid = b.uid AND a.event_id = b.event_id;

-- Idempotent: only add the constraint if it does not already exist (re-runnable migration).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'lm_ask_log_uid_event_id_key') THEN
    ALTER TABLE public.lm_ask_log ADD CONSTRAINT lm_ask_log_uid_event_id_key UNIQUE (uid, event_id);
  END IF;
END $$;

-- 2) TRAVEL: a new claim ledger keyed by (uid, event_key, leg) where leg = 'go' | 'return'.
--    fillTravel claims before createTravelBlock; a duplicate concurrent run 409s and does not create.
CREATE TABLE IF NOT EXISTS public.lm_travel_log (
  uid        text        NOT NULL,
  event_key  text        NOT NULL,
  leg        text        NOT NULL CHECK (leg IN ('go','return')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (uid, event_key, leg)
);
CREATE INDEX IF NOT EXISTS lm_travel_log_uid_idx ON public.lm_travel_log (uid);

-- RLS: service-role (the scheduler) bypasses RLS; enable it so the anon key can't read/write directly.
ALTER TABLE public.lm_travel_log ENABLE ROW LEVEL SECURITY;
