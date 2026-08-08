-- Life Manager mobile travel-block state machine (additive follow-up).
--
-- lm_travel_log already owns UNIQUE (uid, event_key, leg) for the legacy DAILY
-- writer.  Existing rows cannot be proven against a provider event, so they
-- are terminal and are never recreated by the mobile path.

ALTER TABLE public.lm_travel_log
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'legacy_terminal',
  ADD COLUMN IF NOT EXISTS calendar_id text NOT NULL DEFAULT 'primary',
  ADD COLUMN IF NOT EXISTS analysis_key text,
  ADD COLUMN IF NOT EXISTS payload_hash text,
  ADD COLUMN IF NOT EXISTS marker text,
  ADD COLUMN IF NOT EXISTS provider_event_id text,
  ADD COLUMN IF NOT EXISTS provider_etag text,
  ADD COLUMN IF NOT EXISTS claim_token text,
  ADD COLUMN IF NOT EXISTS claim_worker_id text,
  ADD COLUMN IF NOT EXISTS claim_acquired_at timestamptz,
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS create_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS provider_observed_at timestamptz,
  ADD COLUMN IF NOT EXISTS confirmed_at timestamptz,
  ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_error_code text,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

UPDATE public.lm_travel_log
   SET status = 'legacy_terminal',
       calendar_id = COALESCE(calendar_id, 'primary'),
       attempt_count = COALESCE(attempt_count, 0),
       updated_at = COALESCE(updated_at, created_at, now())
 WHERE status IS NULL OR status NOT IN ('legacy_terminal', 'claimed', 'creating', 'confirmed', 'blocked_collision');

ALTER TABLE public.lm_travel_log
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN calendar_id SET NOT NULL,
  ALTER COLUMN attempt_count SET NOT NULL,
  ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lm_travel_log_status_check'
  ) THEN
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_status_check
      CHECK (status IN ('legacy_terminal', 'claimed', 'creating', 'confirmed', 'blocked_collision'));
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lm_travel_log_payload_hash_check'
  ) THEN
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_payload_hash_check
      CHECK (payload_hash IS NULL OR payload_hash ~ '^[0-9a-f]{64}$');
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lm_travel_log_provider_event_id_check'
  ) THEN
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_provider_event_id_check
      CHECK (provider_event_id IS NULL OR provider_event_id ~ '^[a-v0-9]{5,1024}$');
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'lm_travel_log_attempt_count_check'
  ) THEN
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_attempt_count_check
      CHECK (attempt_count >= 0);
  END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS lm_travel_log_provider_event_unique
  ON public.lm_travel_log (uid, calendar_id, provider_event_id)
 WHERE provider_event_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS lm_travel_log_marker_unique
  ON public.lm_travel_log (uid, calendar_id, marker)
 WHERE marker IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_travel_log_status_lease_idx
  ON public.lm_travel_log (status, lease_expires_at)
 WHERE status IN ('claimed', 'creating');

ALTER TABLE public.lm_travel_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_travel_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lm_travel_log TO service_role;

CREATE OR REPLACE FUNCTION public.claim_lm_travel_block(
  p_uid text,
  p_event_key text,
  p_leg text,
  p_calendar_id text,
  p_analysis_key text,
  p_payload_hash text,
  p_marker text,
  p_provider_event_id text,
  p_claim_worker_id text,
  p_lease_seconds integer DEFAULT 120,
  p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  current_row public.lm_travel_log%ROWTYPE;
  next_token text;
  lease_seconds integer := GREATEST(1, LEAST(COALESCE(p_lease_seconds, 120), 3600));
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0
     OR p_event_key IS NULL OR char_length(p_event_key) = 0
     OR p_leg IS NULL OR p_leg NOT IN ('go', 'return')
     OR p_calendar_id IS NULL OR char_length(p_calendar_id) = 0
     OR p_analysis_key IS NULL OR char_length(p_analysis_key) = 0
     OR p_payload_hash IS NULL OR p_payload_hash !~ '^[0-9a-f]{64}$'
     OR p_marker IS NULL OR char_length(p_marker) = 0 OR char_length(p_marker) > 255
     OR p_provider_event_id IS NULL OR p_provider_event_id !~ '^[a-v0-9]{5,1024}$'
     OR p_claim_worker_id IS NULL OR char_length(p_claim_worker_id) = 0
  THEN
    RAISE EXCEPTION 'travel block claim facts invalid' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO current_row
    FROM public.lm_travel_log
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
   FOR UPDATE;

  IF NOT FOUND THEN
    next_token := 'travel_claim:' || replace(gen_random_uuid()::text, '-', '');
    INSERT INTO public.lm_travel_log(
      uid, event_key, leg, status, calendar_id, analysis_key, payload_hash,
      marker, provider_event_id, claim_token, claim_worker_id,
      claim_acquired_at, lease_expires_at, updated_at
    ) VALUES (
      p_uid, p_event_key, p_leg, 'claimed', p_calendar_id, p_analysis_key, p_payload_hash,
      p_marker, p_provider_event_id, next_token, p_claim_worker_id,
      p_now, p_now + make_interval(secs => lease_seconds), p_now
    ) RETURNING * INTO current_row;
    RETURN jsonb_build_object('decision', 'claimed', 'row', to_jsonb(current_row));
  END IF;

  -- A legacy row came from the old write path and has no provider proof.
  -- Keeping it terminal prevents an unprovable row from being recreated.
  IF current_row.status = 'legacy_terminal' THEN
    RETURN jsonb_build_object('decision', 'legacy_terminal', 'row', to_jsonb(current_row));
  END IF;

  -- The semantic key is unique.  A new payload for the same operation is an
  -- analysis conflict, never a chance to overwrite the original event.
  IF current_row.calendar_id IS DISTINCT FROM p_calendar_id
     OR current_row.payload_hash IS DISTINCT FROM p_payload_hash
     OR current_row.marker IS DISTINCT FROM p_marker
     OR current_row.provider_event_id IS DISTINCT FROM p_provider_event_id
  THEN
    RETURN jsonb_build_object('decision', 'analysis_conflict', 'row', to_jsonb(current_row));
  END IF;

  IF current_row.status IN ('claimed', 'creating')
     AND current_row.lease_expires_at IS NOT NULL
     AND current_row.lease_expires_at > p_now
  THEN
    RETURN jsonb_build_object('decision', 'busy', 'row', to_jsonb(current_row));
  END IF;

  IF current_row.status IN ('claimed', 'creating') THEN
    next_token := 'travel_claim:' || replace(gen_random_uuid()::text, '-', '');
    UPDATE public.lm_travel_log
       SET status = 'claimed', claim_token = next_token,
           claim_worker_id = p_claim_worker_id, claim_acquired_at = p_now,
           lease_expires_at = p_now + make_interval(secs => lease_seconds),
           updated_at = p_now, last_error_code = NULL
     WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
     RETURNING * INTO current_row;
    RETURN jsonb_build_object('decision', 'claimed', 'row', to_jsonb(current_row));
  END IF;

  RETURN jsonb_build_object('decision', 'reused', 'row', to_jsonb(current_row));
END;
$$;

CREATE OR REPLACE FUNCTION public.mark_lm_travel_create_started(
  p_uid text, p_event_key text, p_leg text, p_claim_token text,
  p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE changed public.lm_travel_log%ROWTYPE;
BEGIN
  IF p_claim_token IS NULL OR char_length(p_claim_token) = 0 THEN
    RETURN jsonb_build_object('started', false, 'reason', 'stale_token');
  END IF;
  UPDATE public.lm_travel_log
     SET status = 'creating', create_started_at = COALESCE(create_started_at, p_now),
         attempt_count = attempt_count + 1, updated_at = p_now
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
     AND status = 'claimed' AND claim_token = p_claim_token
     AND lease_expires_at IS NOT NULL AND lease_expires_at > p_now
  RETURNING * INTO changed;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('started', false, 'reason', 'stale_token');
  END IF;
  RETURN jsonb_build_object('started', true, 'row', to_jsonb(changed));
END;
$$;

CREATE OR REPLACE FUNCTION public.confirm_lm_travel_block(
  p_uid text, p_event_key text, p_leg text, p_claim_token text,
  p_provider_etag text, p_provider_observed_at timestamptz DEFAULT now(),
  p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE changed public.lm_travel_log%ROWTYPE;
BEGIN
  UPDATE public.lm_travel_log
     SET status = 'confirmed', provider_etag = NULLIF(p_provider_etag, ''),
         provider_observed_at = p_provider_observed_at, confirmed_at = COALESCE(confirmed_at, p_now),
         lease_expires_at = NULL, updated_at = p_now, last_error_code = NULL
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
     AND claim_token = p_claim_token AND status IN ('claimed', 'creating');
  IF NOT FOUND THEN RETURN jsonb_build_object('confirmed', false, 'reason', 'stale_token'); END IF;
  SELECT * INTO changed FROM public.lm_travel_log
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg;
  RETURN jsonb_build_object('confirmed', true, 'row', to_jsonb(changed));
END;
$$;

CREATE OR REPLACE FUNCTION public.release_lm_travel_claim(
  p_uid text, p_event_key text, p_leg text, p_claim_token text,
  p_error_code text DEFAULT 'provider_readback_failed', p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE changed public.lm_travel_log%ROWTYPE;
BEGIN
  UPDATE public.lm_travel_log
     SET status = CASE WHEN status = 'creating' THEN 'creating' ELSE 'claimed' END,
         lease_expires_at = p_now, last_error_code = left(COALESCE(p_error_code, 'provider_readback_failed'), 128),
         updated_at = p_now
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
     AND claim_token = p_claim_token AND status IN ('claimed', 'creating');
  IF NOT FOUND THEN RETURN jsonb_build_object('released', false, 'reason', 'stale_token'); END IF;
  SELECT * INTO changed FROM public.lm_travel_log
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg;
  RETURN jsonb_build_object('released', true, 'row', to_jsonb(changed));
END;
$$;

CREATE OR REPLACE FUNCTION public.block_lm_travel_collision(
  p_uid text, p_event_key text, p_leg text, p_claim_token text,
  p_error_code text DEFAULT 'provider_collision', p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE changed public.lm_travel_log%ROWTYPE;
BEGIN
  UPDATE public.lm_travel_log
     SET status = 'blocked_collision', lease_expires_at = NULL,
         last_error_code = left(COALESCE(p_error_code, 'provider_collision'), 128), updated_at = p_now
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg
     AND claim_token = p_claim_token AND status IN ('claimed', 'creating');
  IF NOT FOUND THEN RETURN jsonb_build_object('blocked', false, 'reason', 'stale_token'); END IF;
  SELECT * INTO changed FROM public.lm_travel_log
   WHERE uid = p_uid AND event_key = p_event_key AND leg = p_leg;
  RETURN jsonb_build_object('blocked', true, 'row', to_jsonb(changed));
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lm_travel_block(text, text, text, text, text, text, text, text, text, integer, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.mark_lm_travel_create_started(text, text, text, text, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.confirm_lm_travel_block(text, text, text, text, text, timestamptz, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_lm_travel_claim(text, text, text, text, text, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.block_lm_travel_collision(text, text, text, text, text, timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_travel_block(text, text, text, text, text, text, text, text, text, integer, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.mark_lm_travel_create_started(text, text, text, text, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.confirm_lm_travel_block(text, text, text, text, text, timestamptz, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_lm_travel_claim(text, text, text, text, text, timestamptz, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.block_lm_travel_collision(text, text, text, text, text, timestamptz) TO service_role;
