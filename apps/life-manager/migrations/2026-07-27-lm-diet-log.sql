-- H2 ORG-diet (spec §10 NEXT HORIZON row H2 ②): the diet ledger.
--
-- ONE table for the whole organ, discriminated by `kind`:
--   ask    — we opened the lunch closed question (max 1/day, 3/week — the weekly cap is counted here)
--   answer — the user tapped one of the four choices (this is the only row that carries `answer`)
--   nudge  — we sent the intervention message (max 1/day)
--
-- The UNIQUE (uid, day, kind) index is not bookkeeping, it is the CAP: the 60s tick sees the lunch
-- window for 120 consecutive minutes, and the runtime claims the day by INSERTing before it sends.
-- A duplicate-key 409 is how the second tick learns it lost the race — no in-memory counter, so a
-- restart can neither double-ask nor forget (the lm_care_scan_log / claimWake precedent).
--
-- Append-only, and stricter than lm_care_scan_log: that table had to let the 11b chain land on the
-- row afterwards, this one has nothing to fill in later, so NO row may ever be updated or deleted.
-- What a person ate is a fact about their day; a ledger that can be quietly rewritten is not evidence.
--
-- Deliberately NOT stored (spec H2 ⑥ — 診断・カロリー計算はしない): no calories, no weight, no
-- nutrition score, no verdict. The four tap values and the day are the entire observation. The nudge
-- row's `venue` holds only PUBLIC Google Places data (name + address), never anything about the user.
-- Additive only: nothing existing is altered or dropped.
CREATE TABLE IF NOT EXISTS public.lm_diet_log (
  id bigserial PRIMARY KEY,
  uid text NOT NULL,
  -- The user's LOCAL day. Lunch is a local idea: a UTC day would split one Tokyo lunch across two rows.
  day date NOT NULL,
  kind text NOT NULL CHECK (kind IN ('ask', 'answer', 'nudge')),
  answer text CHECK (answer IS NULL OR answer IN ('teishoku', 'men', 'fast', 'skip')),
  -- When the message left us: the question for an `ask` row, the nudge for a `nudge` row.
  asked_at timestamptz,
  -- `answer` rows only: when the tap arrived. The 14-day fast-share windows on this column.
  answered_at timestamptz,
  telegram_message_id text,
  -- nudge rows only: {name, address} of the one alternative we named, or null when Places found
  -- nothing and we said so honestly. Public venue data only.
  venue jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  -- An answer row must carry a choice, and nothing else may: the 14-day fast-share is computed over
  -- these rows, so a kind='ask' row with an answer would silently corrupt the intervention threshold.
  CONSTRAINT lm_diet_log_answer_matches_kind CHECK ((kind = 'answer') = (answer IS NOT NULL))
);

-- THE cap. One ask, one answer, one nudge per user per local day.
CREATE UNIQUE INDEX IF NOT EXISTS lm_diet_log_uid_day_kind
  ON public.lm_diet_log (uid, day, kind);

-- The trailing 7-day (weekly cap) and 14-day (fast share) reads.
CREATE INDEX IF NOT EXISTS lm_diet_log_uid_created_at
  ON public.lm_diet_log (uid, created_at DESC);

CREATE OR REPLACE FUNCTION public.lm_diet_log_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lm_diet_log is append-only';
END $$;

DROP TRIGGER IF EXISTS lm_diet_log_guard ON public.lm_diet_log;
CREATE TRIGGER lm_diet_log_guard
  BEFORE UPDATE OR DELETE ON public.lm_diet_log
  FOR EACH ROW EXECUTE FUNCTION public.lm_diet_log_guard();

ALTER TABLE public.lm_diet_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_diet_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_diet_log TO service_role;
REVOKE UPDATE ON TABLE public.lm_diet_log FROM service_role;
REVOKE DELETE ON TABLE public.lm_diet_log FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_diet_log_id_seq TO service_role;
