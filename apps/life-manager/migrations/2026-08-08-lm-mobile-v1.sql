-- Life Manager mobile v1 durable boundary.
--
-- The mobile HTTP adapters use service_role REST/RPC calls.  Every user-owned
-- row is keyed by the authenticated scope UID; raw bearer values, OAuth state,
-- and APNs tokens are never accepted as tenant authority.

ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS product_locale text,
  ADD COLUMN IF NOT EXISTS calls_enabled boolean,
  ADD COLUMN IF NOT EXISTS call_language text,
  ADD COLUMN IF NOT EXISTS time_zone text,
  ADD COLUMN IF NOT EXISTS calendar_status text;

UPDATE public.lm_users
   SET product_locale = 'en'
 WHERE product_locale IS NULL;

UPDATE public.lm_users
   SET calls_enabled = false
 WHERE calls_enabled IS NULL;

ALTER TABLE public.lm_users
  ALTER COLUMN product_locale SET DEFAULT 'en',
  ALTER COLUMN product_locale SET NOT NULL,
  ALTER COLUMN calls_enabled SET DEFAULT false,
  ALTER COLUMN calls_enabled SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'lm_users_product_locale_mobile_check'
  ) THEN
    ALTER TABLE public.lm_users
      ADD CONSTRAINT lm_users_product_locale_mobile_check
      CHECK (product_locale IN ('en', 'ja'));
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.lm_mobile_oauth_states (
  state_hash text PRIMARY KEY CHECK (length(state_hash) = 64),
  uid text REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  subject_hash text CHECK (subject_hash IS NULL OR length(subject_hash) = 64),
  provider text NOT NULL DEFAULT 'google_calendar',
  redirect_uri text,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_mobile_oauth_states_expiry_idx
  ON public.lm_mobile_oauth_states (expires_at);

CREATE TABLE IF NOT EXISTS public.lm_mobile_sessions (
  session_id text PRIMARY KEY,
  family_id text NOT NULL,
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  access_token_hash text NOT NULL UNIQUE CHECK (length(access_token_hash) = 64),
  refresh_token_hash text NOT NULL UNIQUE CHECK (length(refresh_token_hash) = 64),
  product_locale text NOT NULL DEFAULT 'en' CHECK (product_locale IN ('en', 'ja')),
  provider_connection jsonb,
  access_expires_at timestamptz NOT NULL,
  refresh_expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  rotated_at timestamptz,
  revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS lm_mobile_sessions_uid_idx
  ON public.lm_mobile_sessions (uid, revoked_at);
CREATE INDEX IF NOT EXISTS lm_mobile_sessions_family_idx
  ON public.lm_mobile_sessions (family_id);

-- This table deliberately has no lm_users FK: pre-auth session mutations use
-- a deterministic anonymous scope until Calendar identity exchange succeeds.
CREATE TABLE IF NOT EXISTS public.lm_mobile_idempotency (
  uid text NOT NULL,
  idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 8 AND 128),
  request_hash text NOT NULL CHECK (length(request_hash) = 64),
  status text NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed')),
  result jsonb,
  result_expires_at timestamptz,
  error jsonb,
  status_code integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, idempotency_key)
);

CREATE INDEX IF NOT EXISTS lm_mobile_idempotency_updated_idx
  ON public.lm_mobile_idempotency (updated_at);

ALTER TABLE public.lm_mobile_idempotency
  ADD COLUMN IF NOT EXISTS result_expires_at timestamptz;

CREATE TABLE IF NOT EXISTS public.lm_mobile_analysis_states (
  uid text PRIMARY KEY REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('idle', 'reading_events', 'checking_locations', 'calculating_route', 'route_ready', 'needs_information', 'no_upcoming_event', 'route_unavailable', 'failed')),
  analysis_id text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.lm_mobile_outbox (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  sequence bigint GENERATED ALWAYS AS IDENTITY,
  id text NOT NULL,
  key text NOT NULL,
  type text,
  args jsonb NOT NULL DEFAULT '{}'::jsonb,
  user_content jsonb,
  question jsonb,
  route jsonb,
  mutation_key text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, id),
  UNIQUE (uid, sequence)
);

CREATE INDEX IF NOT EXISTS lm_mobile_outbox_cursor_idx
  ON public.lm_mobile_outbox (uid, sequence);

CREATE TABLE IF NOT EXISTS public.lm_mobile_questions (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  id text NOT NULL,
  type text NOT NULL,
  prompt text,
  event_id text,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'claimed', 'answered', 'stale')),
  answer text,
  created_at timestamptz NOT NULL DEFAULT now(),
  claimed_at timestamptz,
  answered_at timestamptz,
  PRIMARY KEY (uid, id)
);

CREATE INDEX IF NOT EXISTS lm_mobile_questions_open_idx
  ON public.lm_mobile_questions (uid, status, created_at);

ALTER TABLE public.lm_mobile_questions DROP CONSTRAINT IF EXISTS lm_mobile_questions_status_check;
ALTER TABLE public.lm_mobile_questions
  ADD CONSTRAINT lm_mobile_questions_status_check CHECK (status IN ('open', 'claimed', 'answered', 'stale'));

CREATE TABLE IF NOT EXISTS public.lm_mobile_call_attempts (
  attempt_id text PRIMARY KEY,
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  idempotency_key text NOT NULL,
  day date NOT NULL,
  status text NOT NULL CHECK (status IN ('claimed', 'placed', 'failed', 'rate_limited')),
  provider_receipt jsonb,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (uid, idempotency_key)
);

CREATE INDEX IF NOT EXISTS lm_mobile_call_attempts_day_idx
  ON public.lm_mobile_call_attempts (day, uid, created_at);

-- One row is the globally shared daily call budget.  Claims increment this
-- row with a guarded UPDATE so concurrent tenants cannot both consume the
-- final slot after observing the same count.
CREATE TABLE IF NOT EXISTS public.lm_mobile_call_day_guards (
  day date PRIMARY KEY,
  global_count integer NOT NULL DEFAULT 0 CHECK (global_count >= 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Preserve the budget when this migration is applied after call attempts
-- already exist.  GREATEST keeps a previously claimed guard from decreasing
-- on a repeated migration run.
INSERT INTO public.lm_mobile_call_day_guards AS guard(day, global_count)
SELECT day, count(*)::integer
  FROM public.lm_mobile_call_attempts
 GROUP BY day
ON CONFLICT (day) DO UPDATE
   SET global_count = GREATEST(guard.global_count, EXCLUDED.global_count),
       updated_at = now();

CREATE TABLE IF NOT EXISTS public.lm_mobile_devices (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  token text NOT NULL CHECK (token ~ '^[0-9a-fA-F]{64}$'),
  environment text NOT NULL CHECK (environment IN ('production', 'development')),
  locale text NOT NULL CHECK (locale IN ('en', 'ja')),
  timezone text NOT NULL,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, token)
);

-- APNs tokens identify one physical app installation globally.  The composite
-- tenant key remains for compatibility, while this unique index makes the
-- ownership transfer RPC atomic across tenants.
CREATE UNIQUE INDEX IF NOT EXISTS lm_mobile_devices_token_unique
  ON public.lm_mobile_devices (token);

-- A deletion receipt must survive the lm_users cascade so the client can
-- display proof of completion after the account row is gone.
CREATE TABLE IF NOT EXISTS public.lm_mobile_deletion_receipts (
  uid text NOT NULL,
  operation_id text NOT NULL,
  status text NOT NULL CHECK (status IN ('incomplete', 'completed')),
  completed_at timestamptz,
  capability_hash text CHECK (capability_hash IS NULL OR length(capability_hash) = 64),
  provider_cleanup jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, operation_id)
);

CREATE INDEX IF NOT EXISTS lm_mobile_deletion_receipts_uid_idx
  ON public.lm_mobile_deletion_receipts (uid, created_at);

ALTER TABLE public.lm_mobile_deletion_receipts
  ADD COLUMN IF NOT EXISTS capability_hash text;

CREATE INDEX IF NOT EXISTS lm_mobile_deletion_receipts_capability_idx
  ON public.lm_mobile_deletion_receipts (operation_id, capability_hash);

-- Mobile route results reuse the Gate 1 lm_route_cache table, but need a
-- request digest and the complete structured route (not only duration/geometry)
-- to survive process restarts.  The tenant UID remains the storage boundary;
-- the digest covers the event anchor, direction, addresses, and IANA timezone.
CREATE TABLE IF NOT EXISTS public.lm_route_cache (
  uid text NOT NULL,
  from_geo text NOT NULL,
  to_geo text NOT NULL,
  time_bucket bigint NOT NULL,
  provider text NOT NULL,
  duration_secs integer NOT NULL,
  geometry jsonb,
  computed_at timestamptz NOT NULL DEFAULT now(),
  ttl_secs integer NOT NULL DEFAULT 600,
  UNIQUE (uid, from_geo, to_geo, time_bucket)
);

ALTER TABLE public.lm_route_cache
  ADD COLUMN IF NOT EXISTS cache_key text,
  ADD COLUMN IF NOT EXISTS route jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_mobile_key_unique
  ON public.lm_route_cache (uid, cache_key)
 WHERE cache_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_route_cache_mobile_expiry_idx
  ON public.lm_route_cache (uid, computed_at);

ALTER TABLE public.lm_route_cache ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.lm_mobile_oauth_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_analysis_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_call_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_call_day_guards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_mobile_deletion_receipts ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_oauth_state(
  p_state_hash text,
  p_uid text DEFAULT NULL,
  p_subject_hash text DEFAULT NULL
)
RETURNS TABLE(
  state_hash text,
  uid text,
  subject_hash text,
  provider text,
  redirect_uri text,
  expires_at timestamptz,
  used_at timestamptz
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_mobile_oauth_states AS s
     SET used_at = now()
   WHERE s.state_hash = p_state_hash
     AND s.used_at IS NULL
     AND s.expires_at > now()
     AND (s.uid IS NULL OR s.uid = p_uid)
     AND (s.subject_hash IS NULL OR p_subject_hash IS NULL OR s.subject_hash = p_subject_hash)
  RETURNING s.state_hash, s.uid, s.subject_hash, s.provider, s.redirect_uri, s.expires_at, s.used_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_idempotency(
  p_uid text, p_idempotency_key text, p_request_hash text
)
RETURNS TABLE(
  claimed boolean,
  request_hash text,
  status text,
  result jsonb,
  error jsonb,
  status_code integer
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE inserted_count integer;
BEGIN
  INSERT INTO public.lm_mobile_idempotency(uid, idempotency_key, request_hash, status)
       VALUES (p_uid, p_idempotency_key, p_request_hash, 'pending')
  ON CONFLICT (uid, idempotency_key) DO NOTHING;
  GET DIAGNOSTICS inserted_count = ROW_COUNT;
  RETURN QUERY
  SELECT (inserted_count = 1), r.request_hash, r.status, r.result, r.error, r.status_code
    FROM public.lm_mobile_idempotency AS r
   WHERE r.uid = p_uid AND r.idempotency_key = p_idempotency_key;
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_lm_mobile_idempotency(
  p_uid text, p_idempotency_key text, p_status text,
  p_result jsonb DEFAULT NULL, p_error jsonb DEFAULT NULL,
  p_status_code integer DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  UPDATE public.lm_mobile_idempotency
     SET status = p_status, result = p_result, error = p_error,
         status_code = p_status_code, updated_at = now()
   WHERE uid = p_uid AND idempotency_key = p_idempotency_key;
  RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION public.rotate_lm_mobile_refresh(
  p_session_id text,
  p_family_id text,
  p_uid text,
  p_next_session_id text,
  p_next_access_token_hash text,
  p_next_refresh_token_hash text,
  p_next_access_expires_at timestamptz,
  p_next_refresh_expires_at timestamptz,
  p_product_locale text
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE current_session public.lm_mobile_sessions%ROWTYPE;
BEGIN
  SELECT * INTO current_session
    FROM public.lm_mobile_sessions
   WHERE session_id = p_session_id
     AND family_id = p_family_id
     AND uid = p_uid
   FOR UPDATE;
  IF NOT FOUND OR current_session.rotated_at IS NOT NULL OR current_session.revoked_at IS NOT NULL THEN
    UPDATE public.lm_mobile_sessions SET revoked_at = COALESCE(revoked_at, now()) WHERE family_id = p_family_id;
    RETURN jsonb_build_object('replay', true);
  END IF;
  UPDATE public.lm_mobile_sessions SET rotated_at = now(), revoked_at = now() WHERE session_id = p_session_id;
  INSERT INTO public.lm_mobile_sessions(
    session_id, family_id, uid, access_token_hash, refresh_token_hash,
    product_locale, access_expires_at, refresh_expires_at
  ) VALUES (
    p_next_session_id, p_family_id, p_uid, p_next_access_token_hash,
    p_next_refresh_token_hash, p_product_locale, p_next_access_expires_at,
    p_next_refresh_expires_at
  );
  RETURN jsonb_build_object('rotated', true, 'session_id', p_next_session_id);
END;
$$;

CREATE OR REPLACE FUNCTION public.consume_lm_mobile_question(
  p_uid text, p_question_id text, p_answer text
)
RETURNS TABLE(uid text, id text, type text, prompt text, event_id text, status text, answer text, answered_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_mobile_questions AS q
     SET status = 'answered', answer = p_answer, answered_at = now()
   WHERE q.uid = p_uid AND q.id = p_question_id AND q.status = 'open'
  RETURNING q.uid, q.id, q.type, q.prompt, q.event_id, q.status, q.answer, q.answered_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_question(
  p_uid text, p_question_id text, p_answer text
)
RETURNS TABLE(uid text, id text, type text, prompt text, event_id text, status text, answer text, answered_at timestamptz, claimed_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_mobile_questions AS q
     SET status = 'claimed', answer = p_answer, claimed_at = COALESCE(q.claimed_at, now())
   WHERE q.uid = p_uid AND q.id = p_question_id
     AND (q.status = 'open' OR (q.status = 'claimed' AND q.answer = p_answer))
  RETURNING q.uid, q.id, q.type, q.prompt, q.event_id, q.status, q.answer, q.answered_at, q.claimed_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_lm_mobile_question(
  p_uid text, p_question_id text, p_answer text
)
RETURNS TABLE(uid text, id text, type text, prompt text, event_id text, status text, answer text, answered_at timestamptz, claimed_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_mobile_questions AS q
     SET status = 'answered', answer = p_answer, answered_at = now()
   WHERE q.uid = p_uid AND q.id = p_question_id AND q.status = 'claimed' AND q.answer = p_answer
  RETURNING q.uid, q.id, q.type, q.prompt, q.event_id, q.status, q.answer, q.answered_at, q.claimed_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_device(
  p_uid text, p_token text, p_environment text, p_locale text,
  p_timezone text, p_last_seen_at timestamptz DEFAULT now()
)
RETURNS public.lm_mobile_devices
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE claimed public.lm_mobile_devices;
BEGIN
  -- Delete any stale tenant owner and then upsert under the global token key in
  -- one transaction. The unique index is the final race-safe arbiter.
  DELETE FROM public.lm_mobile_devices
   WHERE token = p_token AND uid <> p_uid;
  INSERT INTO public.lm_mobile_devices(uid, token, environment, locale, timezone, last_seen_at, updated_at)
       VALUES (p_uid, p_token, p_environment, p_locale, p_timezone, p_last_seen_at, now())
  ON CONFLICT (token) DO UPDATE SET
    uid = EXCLUDED.uid, environment = EXCLUDED.environment, locale = EXCLUDED.locale,
    timezone = EXCLUDED.timezone, last_seen_at = EXCLUDED.last_seen_at, updated_at = now()
  RETURNING * INTO claimed;
  RETURN claimed;
END;
$$;

CREATE OR REPLACE FUNCTION public.finalize_lm_mobile_deletion(
  p_uid text, p_operation_id text, p_capability_hash text,
  p_provider_cleanup jsonb DEFAULT '[]'::jsonb,
  p_preserve_idempotency_key text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE completed timestamptz := now(); existing public.lm_mobile_deletion_receipts%ROWTYPE;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.lm_users WHERE uid = p_uid) THEN
    SELECT * INTO existing FROM public.lm_mobile_deletion_receipts
     WHERE uid = p_uid AND operation_id = p_operation_id AND capability_hash = p_capability_hash;
    IF existing.status = 'completed' THEN
      RETURN jsonb_build_object(
        'operationId', existing.operation_id, 'status', existing.status,
        'completedAt', existing.completed_at, 'providerCleanup', existing.provider_cleanup
      );
    END IF;
    RAISE EXCEPTION 'account_not_found' USING ERRCODE = 'P0002';
  END IF;

  -- Provider cleanup has already completed in the application layer. This
  -- transaction is the terminal boundary: revoke every session, persist the
  -- receipt, remove all account rows, and preserve the proof outside cascade.
  UPDATE public.lm_mobile_sessions SET revoked_at = completed WHERE uid = p_uid;
  INSERT INTO public.lm_mobile_deletion_receipts(uid, operation_id, status, completed_at, capability_hash, provider_cleanup)
       VALUES (p_uid, p_operation_id, 'completed', completed, p_capability_hash, p_provider_cleanup)
  ON CONFLICT (uid, operation_id) DO UPDATE SET
    status = 'completed', completed_at = EXCLUDED.completed_at,
    capability_hash = EXCLUDED.capability_hash, provider_cleanup = EXCLUDED.provider_cleanup;
  DELETE FROM public.lm_mobile_idempotency
   WHERE uid = p_uid
     AND (p_preserve_idempotency_key IS NULL OR idempotency_key <> p_preserve_idempotency_key);
  DELETE FROM public.lm_users WHERE uid = p_uid;
  RETURN jsonb_build_object('operationId', p_operation_id, 'status', 'completed', 'completedAt', completed, 'providerCleanup', p_provider_cleanup);
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_call(
  p_uid text, p_idempotency_key text, p_now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  user_count integer;
  day_slot integer;
  claim_day date;
  last_created timestamptz;
  attempt text;
BEGIN
  PERFORM 1 FROM public.lm_users WHERE uid = p_uid FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('rateLimited', true, 'reason', 'account_not_found'); END IF;

  claim_day := (p_now AT TIME ZONE 'UTC')::date;

  IF EXISTS (
    SELECT 1 FROM public.lm_mobile_call_attempts
     WHERE uid = p_uid AND idempotency_key = p_idempotency_key
  ) THEN
    RETURN jsonb_build_object('rateLimited', true, 'reason', 'duplicate_request');
  END IF;

  SELECT count(*)::integer, max(created_at)
    INTO user_count, last_created
    FROM public.lm_mobile_call_attempts
   WHERE uid = p_uid AND day = claim_day;
  IF user_count >= 5 THEN
    RETURN jsonb_build_object('rateLimited', true, 'reason', 'daily_user_limit');
  END IF;
  IF last_created IS NOT NULL AND last_created > p_now - interval '10 minutes' THEN
    RETURN jsonb_build_object('rateLimited', true, 'reason', 'cooldown');
  END IF;

  INSERT INTO public.lm_mobile_call_day_guards(day, global_count)
       VALUES (claim_day, 0)
  ON CONFLICT (day) DO NOTHING;
  UPDATE public.lm_mobile_call_day_guards
     SET global_count = global_count + 1, updated_at = now()
   WHERE day = claim_day AND global_count < 100
  RETURNING global_count INTO day_slot;
  IF day_slot IS NULL THEN
    RETURN jsonb_build_object('rateLimited', true, 'reason', 'daily_global_limit');
  END IF;

  attempt := 'call:v1:' || replace(gen_random_uuid()::text, '-', '');
  INSERT INTO public.lm_mobile_call_attempts(attempt_id, uid, idempotency_key, day, status, created_at)
       VALUES (attempt, p_uid, p_idempotency_key, claim_day, 'claimed', p_now);
  RETURN jsonb_build_object('attemptId', attempt, 'status', 'claimed', 'createdAt', p_now);
END;
$$;

CREATE OR REPLACE FUNCTION public.delete_lm_mobile_account(
  p_uid text, p_preserve_idempotency_key text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.lm_users WHERE uid = p_uid) THEN
    RAISE EXCEPTION 'account_not_found' USING ERRCODE = 'P0002';
  END IF;
  DELETE FROM public.lm_mobile_idempotency
   WHERE uid = p_uid
     AND (p_preserve_idempotency_key IS NULL OR idempotency_key <> p_preserve_idempotency_key);
  DELETE FROM public.lm_users WHERE uid = p_uid;
  RETURN jsonb_build_object('deleted', true, 'uid', p_uid);
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lm_mobile_oauth_state(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_mobile_idempotency(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_lm_mobile_idempotency(text, text, text, jsonb, jsonb, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.rotate_lm_mobile_refresh(text, text, text, text, text, text, timestamptz, timestamptz, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.consume_lm_mobile_question(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_mobile_question(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_lm_mobile_question(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_mobile_device(text, text, text, text, text, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.finalize_lm_mobile_deletion(text, text, text, jsonb, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_mobile_call(text, text, timestamptz) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.delete_lm_mobile_account(text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_oauth_state(text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_idempotency(text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_lm_mobile_idempotency(text, text, text, jsonb, jsonb, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.rotate_lm_mobile_refresh(text, text, text, text, text, text, timestamptz, timestamptz, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.consume_lm_mobile_question(text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_question(text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_lm_mobile_question(text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_device(text, text, text, text, text, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.finalize_lm_mobile_deletion(text, text, text, jsonb, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_call(text, text, timestamptz) TO service_role;
GRANT EXECUTE ON FUNCTION public.delete_lm_mobile_account(text, text) TO service_role;
