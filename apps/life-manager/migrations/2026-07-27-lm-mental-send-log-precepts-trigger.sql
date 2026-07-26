-- H4 ORG-precepts (spec §10 NEXT HORIZON row H4 ⑤): let the precepts messages into MENTAL's budget.
--
-- H4 ⑤ says the precepts ask counts against MENTAL's 3通/日 cap — 別枠にしない. That budget lives in
-- lm_mental_send_log, one row per delivered message, and the runtime writes a row after every send it
-- makes. lm_mental_send_log's `trigger` column is CHECK-constrained to the three MENTAL trigger
-- shapes (2026-07-25-lm-mental-send-log.sql), so WITHOUT THIS MIGRATION every precepts send would
-- 400 on the insert: the message would go out, the row would not land, and the cap it is supposed to
-- share would never see it. That is a silent over-send, which is the exact failure the cap exists to
-- prevent.
--
-- THE HONEST ALTERNATIVE, REJECTED: recording the precepts ask as trigger='pre_sleep' would pass the
-- existing constraint with no migration at all. It would also make the ledger lie — a row that says
-- an affirmation was sent when a question was asked — and this repo's ledgers are append-only
-- precisely because they are evidence. A ledger you have to mistranslate to write to is a ledger
-- whose schema is wrong, so the schema is what changes.
--
-- Two new values, not one: the weekly mirror is a different message from the nightly question, both
-- count against the same cap, and a shared token would make the two indistinguishable in the one
-- place anyone would look to audit what the organ actually sent.
--
-- Additive in effect: no row is altered, no column is dropped, and every value that was legal before
-- is legal after. Idempotent: re-running finds the constraint it added last time (it, too, mentions
-- pre_sleep), drops it, and re-adds the same definition.
--
-- The constraint is located by DEFINITION rather than by name. An inline column CHECK gets an
-- auto-generated name (`lm_mental_send_log_trigger_check` on every PostgreSQL this has run on), but
-- dropping a guessed name that does not exist is a no-op that leaves the old constraint in place and
-- the new one rejected as a duplicate — a migration that reports success and changes nothing.
DO $$
DECLARE c record;
BEGIN
  FOR c IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'public.lm_mental_send_log'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%pre_sleep%'
  LOOP
    EXECUTE format('ALTER TABLE public.lm_mental_send_log DROP CONSTRAINT %I', c.conname);
  END LOOP;
END $$;

ALTER TABLE public.lm_mental_send_log
  ADD CONSTRAINT lm_mental_send_log_trigger_check
  CHECK (trigger IN ('pre_event', 'between_events', 'pre_sleep', 'precepts', 'precepts_mirror'));
