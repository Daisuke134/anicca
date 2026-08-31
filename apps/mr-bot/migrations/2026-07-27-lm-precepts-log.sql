-- H4 ORG-precepts (spec §10 NEXT HORIZON row H4 ②): the precepts ledger.
--
-- ONE table for the whole organ, discriminated by `kind`:
--   ask    — we opened the bedtime closed question (at most 1/day, and in practice 1/week)
--   answer — the user tapped one of the five choices (this is the only row that carries `answer`)
--   mirror — we sent the Sunday-night weekly mirror (at most 1/day, and at most 1/week)
--
-- The UNIQUE (uid, day, kind) index is not bookkeeping, it is the CAP: the 60s tick sees the bedtime
-- window for 30 consecutive minutes, and the runtime claims the day by INSERTing before it sends. A
-- duplicate-key 409 is how the second tick learns it lost the race — no in-memory counter, so a
-- restart can neither double-ask nor forget (the lm_diet_log / lm_care_scan_log / claimWake precedent).
--
-- Append-only. What a person noticed about their own evening is the most private thing this product
-- holds; a ledger that can be quietly rewritten is not evidence, and a ledger that can be quietly
-- emptied is not a record. No row may ever be updated or deleted, by anyone, including us.
--
-- Deliberately NOT stored (spec H4 ③ — 説教・評価・スコア化禁止): no score, no total, no trend, no
-- verdict, no free text. FIVE ENUM TOKENS AND A DAY are the entire observation. There is no column
-- here that could hold a sentence about a person, which is the only durable way to guarantee that no
-- sentence about a person is ever written. The mirror row's `pattern` holds ONLY the shape the weekly
-- message named — {kind, answer, count, weekday} — never an event title, never a place, never a name.
-- Additive only: nothing existing is altered or dropped.
CREATE TABLE IF NOT EXISTS public.lm_precepts_log (
  id bigserial PRIMARY KEY,
  uid text NOT NULL,
  -- The user's LOCAL day. Bedtime is a local idea, and a 23:40 JST question is the 27th's evening
  -- even though it is still the 27th 14:40 in UTC.
  day date NOT NULL,
  kind text NOT NULL CHECK (kind IN ('ask', 'answer', 'mirror')),
  -- The 五戒 in ordinary Japanese, stored as ASCII tokens: lie / harsh / time / impulse / calm.
  -- 'calm' is a real observation, not an absence — the mirror counts it alongside the rest so the
  -- weekly message is a record of the week rather than a highlight reel of its worst nights.
  answer text CHECK (answer IS NULL OR answer IN ('lie', 'harsh', 'time', 'impulse', 'calm')),
  -- When the message left us: the question for an `ask` row, the mirror for a `mirror` row.
  asked_at timestamptz,
  -- `answer` rows only: when the tap arrived. The trailing-7-day mirror windows on this column.
  answered_at timestamptz,
  telegram_message_id text,
  -- mirror rows only: the deterministic pattern the message named, or null when it stated facts
  -- only. Shape, never content — see the header.
  pattern jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  -- An answer row must carry a choice, and nothing else may: the trailing-7-day counts are computed
  -- over these rows, so a kind='ask' row with an answer would silently corrupt the mirror.
  CONSTRAINT lm_precepts_log_answer_matches_kind CHECK ((kind = 'answer') = (answer IS NOT NULL))
);

-- THE cap. One ask, one answer, one mirror per user per local day.
CREATE UNIQUE INDEX IF NOT EXISTS lm_precepts_log_uid_day_kind
  ON public.lm_precepts_log (uid, day, kind);

-- The trailing-window reads, on the column they actually filter by. All three — the 7-day ask
-- spacing, the 7-day answer window the mirror counts over, the 7-day mirror cooldown — are
-- (uid, day >= <a local day>), because `day` is the user's own calendar day and the only key an
-- evening history can honestly be bucketed on. The asked_at / answered_at cuts are served THROUGH
-- this index: the query narrows by day (with a one-day cushion for timezone slop) and the exact
-- timestamp cut is made on the narrowed rows.
CREATE INDEX IF NOT EXISTS lm_precepts_log_uid_day
  ON public.lm_precepts_log (uid, day DESC);

CREATE OR REPLACE FUNCTION public.lm_precepts_log_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lm_precepts_log is append-only';
END $$;

DROP TRIGGER IF EXISTS lm_precepts_log_guard ON public.lm_precepts_log;
CREATE TRIGGER lm_precepts_log_guard
  BEFORE UPDATE OR DELETE ON public.lm_precepts_log
  FOR EACH ROW EXECUTE FUNCTION public.lm_precepts_log_guard();

-- THE HOLE THE ROW TRIGGER LEAVES, closed — the hardening note lm_diet_log wrote down for every
-- future ledger in this repo, applied. A row-level BEFORE UPDATE OR DELETE trigger never fires for
-- TRUNCATE (TRUNCATE is neither; it removes the rows without visiting any of them), so a ledger
-- guarded only by that trigger could still be emptied in one statement, and the append-only promise
-- would be true of every row and false of the table. Statement-level trigger, same guard function
-- (it touches neither NEW nor OLD, so it serves both). All three parts are present below:
--   1. REVOKE UPDATE, DELETE (the ordinary writes),
--   2. REVOKE TRUNCATE, plus REFERENCES and TRIGGER — a role that may add its own trigger or FK can
--      arrange for rows to disappear anyway, so leaving those granted leaves the guard editable by
--      the very role it guards against,
--   3. triggers at BOTH levels, because a grant is a policy and a trigger is a mechanism, and a
--      ledger that is evidence needs the mechanism as well as the policy.
DROP TRIGGER IF EXISTS lm_precepts_log_truncate_guard ON public.lm_precepts_log;
CREATE TRIGGER lm_precepts_log_truncate_guard
  BEFORE TRUNCATE ON public.lm_precepts_log
  FOR EACH STATEMENT EXECUTE FUNCTION public.lm_precepts_log_guard();

ALTER TABLE public.lm_precepts_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_precepts_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_precepts_log TO service_role;
REVOKE UPDATE ON TABLE public.lm_precepts_log FROM service_role;
REVOKE DELETE ON TABLE public.lm_precepts_log FROM service_role;
REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE public.lm_precepts_log FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_precepts_log_id_seq TO service_role;
