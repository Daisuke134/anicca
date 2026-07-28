-- BROWSER-GEN-1: durable, tenant-bound cloud browser queue in Railway-private Postgres.
-- The raw Telegram prompt and all credentials are intentionally absent. The queue stores a hash
-- for provenance plus the classifier's bounded, execution-safe goal. The authenticated tenant
-- binding is established against Supabase before enqueue; this private queue stores only that uid.

CREATE TABLE IF NOT EXISTS public.lm_browser_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  uid text NOT NULL,
  telegram_chat_id text NOT NULL CHECK (char_length(telegram_chat_id) BETWEEN 1 AND 100),
  telegram_message_id text NOT NULL CHECK (char_length(telegram_message_id) BETWEEN 1 AND 100),
  telegram_update_id text NOT NULL CHECK (char_length(telegram_update_id) BETWEEN 1 AND 100),
  prompt_hash text NOT NULL CHECK (
    length(prompt_hash) = 64 AND prompt_hash ~ '^[0-9a-f]{64}$'
  ),
  goal text NOT NULL CHECK (char_length(goal) BETWEEN 1 AND 1000),
  locale text NOT NULL CHECK (locale IN ('en', 'ja')),
  action_kind text NOT NULL CHECK (char_length(action_kind) BETWEEN 1 AND 100),
  requires_login boolean NOT NULL DEFAULT false,
  status text NOT NULL CHECK (
    status IN ('queued', 'claimed', 'completed', 'possibly_completed', 'handoff_required', 'failed')
  ),
  trace jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (
    jsonb_typeof(trace) = 'array'
    AND jsonb_array_length(trace) <= 100
    AND octet_length(trace::text) <= 65536
  ),
  receipt jsonb CHECK (
    receipt IS NULL
    OR (
      jsonb_typeof(receipt) = 'object'
      AND octet_length(receipt::text) <= 16384
    )
  ),
  telegram_result_message_id bigint CHECK (
    telegram_result_message_id IS NULL OR telegram_result_message_id > 0
  ),
  claimed_at timestamptz,
  lease_expires_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (uid, telegram_chat_id, telegram_message_id),
  CHECK (
    (status = 'queued' AND claimed_at IS NULL AND lease_expires_at IS NULL AND finished_at IS NULL)
    OR (status = 'claimed' AND claimed_at IS NOT NULL AND lease_expires_at IS NOT NULL AND finished_at IS NULL)
    OR (status IN ('completed', 'possibly_completed', 'handoff_required', 'failed')
      AND claimed_at IS NOT NULL AND finished_at IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS lm_browser_jobs_claim_idx
  ON public.lm_browser_jobs (status, lease_expires_at, created_at);
CREATE INDEX IF NOT EXISTS lm_browser_jobs_tenant_recent_idx
  ON public.lm_browser_jobs (uid, created_at DESC);

CREATE OR REPLACE FUNCTION public.claim_lm_browser_job(
  p_lease_seconds integer DEFAULT 180
) RETURNS SETOF public.lm_browser_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  v_id uuid;
BEGIN
  IF p_lease_seconds < 30 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'browser job lease out of bounds';
  END IF;

  SELECT id INTO v_id
  FROM public.lm_browser_jobs
  WHERE status = 'queued'
    OR (status = 'claimed' AND lease_expires_at <= clock_timestamp())
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;

  IF v_id IS NULL THEN
    RETURN;
  END IF;

  RETURN QUERY
  UPDATE public.lm_browser_jobs
  SET status = 'claimed',
      claimed_at = clock_timestamp(),
      lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds),
      updated_at = clock_timestamp()
  WHERE id = v_id
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.append_lm_browser_job_trace(
  p_job_id uuid,
  p_stage text,
  p_meta jsonb DEFAULT '{}'::jsonb
) RETURNS SETOF public.lm_browser_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_stage NOT IN (
    'claimed', 'discovery', 'selected', 'action_started',
    'action_observed', 'provider_readback', 'telegram_sent',
    'evidence_sent', 'steel_released'
  ) THEN
    RAISE EXCEPTION 'invalid browser trace stage';
  END IF;
  IF jsonb_typeof(COALESCE(p_meta, '{}'::jsonb)) <> 'object'
    OR octet_length(COALESCE(p_meta, '{}'::jsonb)::text) > 8192 THEN
    RAISE EXCEPTION 'invalid browser trace metadata';
  END IF;

  RETURN QUERY
  UPDATE public.lm_browser_jobs
  SET trace = trace || jsonb_build_array(jsonb_build_object(
        'stage', p_stage,
        'at', clock_timestamp(),
        'meta', COALESCE(p_meta, '{}'::jsonb)
      )),
      updated_at = clock_timestamp()
  WHERE id = p_job_id
    AND jsonb_array_length(trace) < 100
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.finish_lm_browser_job(
  p_job_id uuid,
  p_status text,
  p_receipt jsonb,
  p_telegram_message_id bigint DEFAULT NULL
) RETURNS SETOF public.lm_browser_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_status NOT IN ('completed', 'possibly_completed', 'handoff_required', 'failed') THEN
    RAISE EXCEPTION 'invalid browser terminal status';
  END IF;
  IF jsonb_typeof(p_receipt) <> 'object' OR octet_length(p_receipt::text) > 16384 THEN
    RAISE EXCEPTION 'invalid browser receipt';
  END IF;

  RETURN QUERY
  UPDATE public.lm_browser_jobs
  SET status = p_status,
      receipt = p_receipt,
      telegram_result_message_id = p_telegram_message_id,
      lease_expires_at = NULL,
      finished_at = clock_timestamp(),
      updated_at = clock_timestamp()
  WHERE id = p_job_id AND status = 'claimed'
  RETURNING *;
END
$$;
