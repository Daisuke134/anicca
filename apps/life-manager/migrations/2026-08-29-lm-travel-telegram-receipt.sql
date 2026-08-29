-- Durable Telegram delivery receipt on the existing travel claim row.
-- The claim key, four-leg CHECK, RLS, and existing rows remain the source of truth.

ALTER TABLE public.lm_travel_log
  ADD COLUMN IF NOT EXISTS telegram_message_id bigint;

ALTER TABLE public.lm_travel_log
  ADD COLUMN IF NOT EXISTS telegram_sent_at timestamptz;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conrelid = 'public.lm_travel_log'::regclass
       AND conname = 'lm_travel_log_telegram_message_id_check'
  ) THEN
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_telegram_message_id_check
      CHECK (telegram_message_id IS NULL OR telegram_message_id > 0) NOT VALID;
  END IF;
END
$$;

ALTER TABLE public.lm_travel_log
  VALIDATE CONSTRAINT lm_travel_log_telegram_message_id_check;

CREATE UNIQUE INDEX IF NOT EXISTS lm_travel_log_uid_telegram_message_id_key
  ON public.lm_travel_log (uid, telegram_message_id)
  WHERE telegram_message_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.record_lm_travel_telegram_receipt(
  p_uid text,
  p_event_key text,
  p_leg text,
  p_telegram_message_id bigint
) RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
  matched integer;
BEGIN
  IF p_uid IS NULL OR btrim(p_uid) = '' OR char_length(p_uid) > 256 THEN
    RAISE EXCEPTION 'invalid uid';
  END IF;
  IF p_event_key IS NULL OR btrim(p_event_key) = '' OR char_length(p_event_key) > 512 THEN
    RAISE EXCEPTION 'invalid event key';
  END IF;
  IF p_leg IS NULL OR p_leg NOT IN ('telegram-t5', 'trial-upgrade') THEN
    RAISE EXCEPTION 'invalid receipt leg';
  END IF;
  IF p_telegram_message_id IS NULL OR p_telegram_message_id <= 0 THEN
    RAISE EXCEPTION 'invalid Telegram message ID';
  END IF;

  UPDATE public.lm_travel_log AS target
     SET telegram_message_id = CASE
           WHEN target.telegram_message_id IS NULL THEN p_telegram_message_id
           ELSE target.telegram_message_id
         END,
         telegram_sent_at = CASE
           WHEN target.telegram_message_id IS NULL THEN clock_timestamp()
           ELSE target.telegram_sent_at
         END
   WHERE target.uid = p_uid
     AND target.event_key = p_event_key
     AND target.leg = p_leg
     AND (target.telegram_message_id IS NULL OR target.telegram_message_id = p_telegram_message_id)
     AND NOT EXISTS (
       SELECT 1
         FROM public.lm_travel_log AS used
        WHERE used.uid = p_uid
          AND used.telegram_message_id = p_telegram_message_id
          AND (used.uid, used.event_key, used.leg) <> (target.uid, target.event_key, target.leg)
     );

  GET DIAGNOSTICS matched = ROW_COUNT;
  RETURN matched;
EXCEPTION
  WHEN unique_violation THEN
    RETURN 0;
END;
$function$;

REVOKE ALL ON FUNCTION public.record_lm_travel_telegram_receipt(text, text, text, bigint)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_lm_travel_telegram_receipt(text, text, text, bigint)
  TO service_role;
