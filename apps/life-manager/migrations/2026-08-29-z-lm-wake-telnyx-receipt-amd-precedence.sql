-- Task 16M fix: a signed AMD webhook is the deterministic terminal truth for a wake row.
-- Hangup and AMD can arrive in either order; keep the existing row and provider identity arbiter.

CREATE OR REPLACE FUNCTION public.record_lm_wake_telnyx_receipt(
  p_uid text,
  p_event_key text,
  p_claim_token text,
  p_telnyx_call_control_id text,
  p_telnyx_call_session_id text DEFAULT NULL,
  p_telnyx_call_leg_id text DEFAULT NULL,
  p_telnyx_webhook_event_id text DEFAULT NULL,
  p_amd_result text DEFAULT NULL
) RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_matched integer;
BEGIN
  IF p_uid IS NULL OR btrim(p_uid) = '' OR char_length(p_uid) > 256
    OR p_event_key IS NULL OR btrim(p_event_key) = '' OR char_length(p_event_key) > 512
    OR p_claim_token IS NULL OR btrim(p_claim_token) = '' OR char_length(p_claim_token) > 512
    OR p_telnyx_call_control_id IS NULL OR btrim(p_telnyx_call_control_id) = ''
    OR char_length(p_telnyx_call_control_id) > 512
    OR (p_telnyx_call_session_id IS NOT NULL AND
        (btrim(p_telnyx_call_session_id) = '' OR char_length(p_telnyx_call_session_id) > 512))
    OR (p_telnyx_call_leg_id IS NOT NULL AND
        (btrim(p_telnyx_call_leg_id) = '' OR char_length(p_telnyx_call_leg_id) > 512))
    OR (p_telnyx_webhook_event_id IS NOT NULL AND
        (btrim(p_telnyx_webhook_event_id) = '' OR char_length(p_telnyx_webhook_event_id) > 512)) THEN
    RAISE EXCEPTION 'invalid Telnyx receipt identity';
  END IF;

  IF p_amd_result IS NOT NULL AND p_amd_result NOT IN ('human', 'machine', 'not_sure') THEN
    RAISE EXCEPTION 'invalid AMD result';
  END IF;

  BEGIN
    UPDATE public.lm_wake_log
       SET telnyx_call_control_id = CASE
             WHEN telnyx_call_control_id IS NULL THEN p_telnyx_call_control_id
             ELSE telnyx_call_control_id
           END,
           telnyx_call_session_id = CASE
             WHEN telnyx_call_session_id IS NULL THEN p_telnyx_call_session_id
             ELSE telnyx_call_session_id
           END,
           telnyx_call_leg_id = CASE
             WHEN telnyx_call_leg_id IS NULL THEN p_telnyx_call_leg_id
             ELSE telnyx_call_leg_id
           END,
           telnyx_webhook_event_id = CASE
             WHEN p_amd_result IS NOT NULL AND amd_result IS NULL
                  AND p_telnyx_webhook_event_id IS NOT NULL
               THEN p_telnyx_webhook_event_id
             WHEN telnyx_webhook_event_id IS NULL THEN p_telnyx_webhook_event_id
             ELSE telnyx_webhook_event_id
           END,
           telnyx_webhook_received_at = CASE
             WHEN p_amd_result IS NOT NULL AND amd_result IS NULL
                  AND p_telnyx_webhook_event_id IS NOT NULL
               THEN clock_timestamp()
             WHEN p_telnyx_webhook_event_id IS NOT NULL AND telnyx_webhook_received_at IS NULL
               THEN clock_timestamp()
             ELSE telnyx_webhook_received_at
           END,
           amd_result = CASE
             WHEN p_amd_result IS NULL THEN amd_result
             ELSE p_amd_result
           END
     WHERE uid = p_uid
       AND event_key = p_event_key
       AND claim_token = p_claim_token
       AND (telnyx_call_control_id IS NULL OR telnyx_call_control_id = p_telnyx_call_control_id)
       AND (telnyx_call_session_id IS NULL OR p_telnyx_call_session_id IS NULL
            OR telnyx_call_session_id = p_telnyx_call_session_id)
       AND (telnyx_call_leg_id IS NULL OR p_telnyx_call_leg_id IS NULL
            OR telnyx_call_leg_id = p_telnyx_call_leg_id)
       AND (
         telnyx_webhook_event_id IS NULL
         OR p_telnyx_webhook_event_id IS NULL
         OR telnyx_webhook_event_id = p_telnyx_webhook_event_id
         OR (amd_result IS NULL AND p_amd_result IS NOT NULL)
       )
       AND NOT EXISTS (
         SELECT 1
           FROM public.lm_wake_log AS other
          WHERE other.telnyx_call_control_id = p_telnyx_call_control_id
            AND (other.uid <> p_uid OR other.event_key <> p_event_key)
       )
       AND (p_telnyx_webhook_event_id IS NULL OR NOT EXISTS (
         SELECT 1
           FROM public.lm_wake_log AS other
          WHERE other.telnyx_webhook_event_id = p_telnyx_webhook_event_id
            AND (other.uid <> p_uid OR other.event_key <> p_event_key)
       ));

    GET DIAGNOSTICS v_matched = ROW_COUNT;
    RETURN v_matched;
  EXCEPTION WHEN unique_violation THEN
    RETURN 0;
  END;
END;
$$;

REVOKE ALL ON FUNCTION public.record_lm_wake_telnyx_receipt(text,text,text,text,text,text,text,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_lm_wake_telnyx_receipt(text,text,text,text,text,text,text,text)
  TO service_role;
