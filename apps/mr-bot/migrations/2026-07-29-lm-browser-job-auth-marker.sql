-- BROWSER-AUTH-1: bind a per-run opaque marker hash to a durable browser job.
-- The marker itself never enters Postgres, a trace, or a receipt.

ALTER TABLE public.lm_browser_jobs
  ADD COLUMN IF NOT EXISTS auth_marker_hash text;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_auth_marker_hash_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_auth_marker_hash_check CHECK (
        auth_marker_hash IS NULL
        OR (length(auth_marker_hash) = 64 AND auth_marker_hash ~ '^[0-9a-f]{64}$')
      ) NOT VALID;
  END IF;
END
$$;

ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_auth_marker_hash_check;

CREATE OR REPLACE FUNCTION public.claim_lm_browser_job_by_id(
  p_job_id uuid,
  p_lease_seconds integer DEFAULT 180
) RETURNS SETOF public.lm_browser_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_lease_seconds < 30 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'browser job lease out of bounds';
  END IF;

  RETURN QUERY
  UPDATE public.lm_browser_jobs
  SET status = 'claimed',
      claimed_at = clock_timestamp(),
      lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds),
      updated_at = clock_timestamp()
  WHERE id = p_job_id
    AND (status = 'queued' OR (status = 'claimed' AND lease_expires_at <= clock_timestamp()))
  RETURNING *;
END
$$;
