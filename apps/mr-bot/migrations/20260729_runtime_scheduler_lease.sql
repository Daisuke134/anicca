CREATE TABLE IF NOT EXISTS public.lm_runtime_scheduler_leases (
  scheduler_key text PRIMARY KEY CHECK (char_length(scheduler_key) BETWEEN 1 AND 100),
  owner_id text NOT NULL CHECK (char_length(owner_id) BETWEEN 1 AND 200),
  holder_token text NOT NULL UNIQUE CHECK (char_length(holder_token) BETWEEN 1 AND 300),
  lease_expires_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION public.claim_lm_runtime_scheduler_owner(
  p_scheduler_key text,
  p_owner_id text,
  p_holder_token text,
  p_lease_seconds integer DEFAULT 30
) RETURNS SETOF public.lm_runtime_scheduler_leases
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_lease_seconds < 10 OR p_lease_seconds > 120 THEN
    RAISE EXCEPTION 'scheduler lease out of bounds';
  END IF;
  RETURN QUERY
  INSERT INTO public.lm_runtime_scheduler_leases (
    scheduler_key, owner_id, holder_token, lease_expires_at
  ) VALUES (
    p_scheduler_key,
    p_owner_id,
    p_holder_token,
    clock_timestamp() + make_interval(secs => p_lease_seconds)
  )
  ON CONFLICT (scheduler_key) DO UPDATE
  SET owner_id = EXCLUDED.owner_id,
      holder_token = EXCLUDED.holder_token,
      lease_expires_at = EXCLUDED.lease_expires_at,
      updated_at = clock_timestamp()
  WHERE public.lm_runtime_scheduler_leases.lease_expires_at <= clock_timestamp()
    OR public.lm_runtime_scheduler_leases.holder_token = EXCLUDED.holder_token
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.heartbeat_lm_runtime_scheduler_owner(
  p_scheduler_key text,
  p_holder_token text,
  p_lease_seconds integer DEFAULT 30
) RETURNS SETOF public.lm_runtime_scheduler_leases
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_lease_seconds < 10 OR p_lease_seconds > 120 THEN
    RAISE EXCEPTION 'scheduler lease out of bounds';
  END IF;
  RETURN QUERY
  UPDATE public.lm_runtime_scheduler_leases
  SET lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds),
      updated_at = clock_timestamp()
  WHERE scheduler_key = p_scheduler_key
    AND holder_token = p_holder_token
    AND lease_expires_at > clock_timestamp()
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.release_lm_runtime_scheduler_owner(
  p_scheduler_key text,
  p_holder_token text
) RETURNS boolean
LANGUAGE sql
SET search_path = public, pg_temp
AS $$
  WITH released AS (
    UPDATE public.lm_runtime_scheduler_leases
    SET lease_expires_at = clock_timestamp(),
        updated_at = clock_timestamp()
    WHERE scheduler_key = p_scheduler_key
      AND holder_token = p_holder_token
    RETURNING 1
  )
  SELECT EXISTS (SELECT 1 FROM released);
$$;
