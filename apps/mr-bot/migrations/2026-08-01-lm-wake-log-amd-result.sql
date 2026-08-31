-- spec 2026-08-01-lm-daily-organ-design.md §1.3 + §3 row 2.
--
-- Correlating every Telnyx call event against lm_wake_log proved the recording path healthy:
-- AMD result=human → answered_at SET, 10 of 10; machine/not_sure → null, 33 of 33. What is broken is
-- the TABLE, which collapses four different realities into the single reading "answered_at IS NULL":
-- a call that rang unanswered, a call that reached voicemail, and a webhook that never arrived at
-- all. If Telnyx rotates its signing key and every webhook starts returning 403, answered_at goes
-- permanently null and nothing anywhere records that — the same failure class as §3 row 1b, where a
-- failure looks like an event that never happened.
--
-- This column is what separates them. Read it as:
--
--   amd_result='human'  + answered_at SET   → a person picked up.
--   amd_result='machine'                    → voicemail: genuinely nobody, the call did happen.
--   amd_result='not_sure'                   → AMD ran and could not tell; still a call we placed.
--   amd_result IS NULL                      → we never heard from the webhook. This is a RECORDING
--                                             FAILURE, not a user behaviour. Rows dialled before
--                                             this migration are also NULL, so treat NULL as
--                                             "unknown", never as "the user ignored us".
--
-- text, not an enum: the value is written verbatim from Telnyx's data.payload.result. If Telnyx ever
-- adds a fourth result, we want it stored and visible, not rejected into the invisible NULL bucket
-- this column exists to empty.

ALTER TABLE public.lm_wake_log ADD COLUMN IF NOT EXISTS amd_result text;

COMMENT ON COLUMN public.lm_wake_log.amd_result IS
  'Verbatim Telnyx AMD data.payload.result (human|machine|not_sure). NULL = no detection webhook was '
  'ever recorded for this row (recording failure or pre-2026-08-01 row), NOT "nobody answered".';

-- §2c reads "what fraction of wake calls reach a person" per user over time, newest first.
CREATE INDEX IF NOT EXISTS lm_wake_log_uid_amd_result_idx
  ON public.lm_wake_log (uid, amd_result);
