-- Official Symphony owns agent execution rounds; the Life Manager runtime job remains authoritative.
-- waiting_agent releases the worker lease while one isolated Symphony round is in flight.

ALTER TABLE public.lm_runtime_jobs
  DROP CONSTRAINT IF EXISTS lm_runtime_jobs_status_check;
ALTER TABLE public.lm_runtime_jobs
  ADD CONSTRAINT lm_runtime_jobs_status_check CHECK (
    status IN (
      'queued', 'running', 'waiting_agent', 'waiting_human',
      'reconciling', 'completed', 'dead_letter'
    )
  );

CREATE TABLE IF NOT EXISTS public.lm_symphony_dispatches (
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  dispatch_id text NOT NULL CHECK (dispatch_id ~ '^[0-9a-f]{64}$'),
  job_id text NOT NULL CHECK (char_length(job_id) BETWEEN 1 AND 200),
  round integer NOT NULL CHECK (round BETWEEN 1 AND 1000000),
  status text NOT NULL CHECK (status IN ('claimed', 'mirrored', 'result_ready', 'consumed', 'failed')),
  issue_ref text CHECK (
    issue_ref IS NULL OR issue_ref ~ '^github-issue://Daisuke134/life-manager-workrooms/[1-9][0-9]*$'
  ),
  result_ref text CHECK (
    result_ref IS NULL OR result_ref ~ '^github-comment://Daisuke134/life-manager-workrooms/[1-9][0-9]*/[1-9][0-9]*$'
  ),
  result_hash text CHECK (result_hash IS NULL OR result_hash ~ '^[0-9a-f]{64}$'),
  result_payload jsonb CHECK (
    result_payload IS NULL OR (
      jsonb_typeof(result_payload) = 'object'
      AND octet_length(result_payload::text) <= 16384
    )
  ),
  failure_code text CHECK (
    failure_code IS NULL OR char_length(failure_code) BETWEEN 1 AND 200
  ),
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  mirrored_at timestamptz,
  result_ready_at timestamptz,
  consumed_at timestamptz,
  failed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, dispatch_id),
  UNIQUE (tenant_id, job_id, round),
  FOREIGN KEY (job_id, tenant_id)
    REFERENCES public.lm_runtime_jobs (job_id, tenant_id),
  CHECK (
    (status = 'claimed' AND issue_ref IS NULL AND result_ref IS NULL AND result_hash IS NULL
      AND result_payload IS NULL AND failure_code IS NULL AND mirrored_at IS NULL
      AND result_ready_at IS NULL AND consumed_at IS NULL AND failed_at IS NULL)
    OR (status = 'mirrored' AND issue_ref IS NOT NULL AND result_ref IS NULL AND result_hash IS NULL
      AND result_payload IS NULL AND failure_code IS NULL AND mirrored_at IS NOT NULL
      AND result_ready_at IS NULL AND consumed_at IS NULL AND failed_at IS NULL)
    OR (status = 'result_ready' AND issue_ref IS NOT NULL AND result_ref IS NOT NULL
      AND result_hash IS NOT NULL AND result_payload IS NOT NULL AND failure_code IS NULL
      AND mirrored_at IS NOT NULL AND result_ready_at IS NOT NULL
      AND consumed_at IS NULL AND failed_at IS NULL)
    OR (status = 'consumed' AND issue_ref IS NOT NULL AND result_ref IS NOT NULL
      AND result_hash IS NOT NULL AND result_payload IS NOT NULL AND failure_code IS NULL
      AND mirrored_at IS NOT NULL AND result_ready_at IS NOT NULL
      AND consumed_at IS NOT NULL AND failed_at IS NULL)
    OR (status = 'failed' AND failure_code IS NOT NULL AND failed_at IS NOT NULL AND consumed_at IS NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS lm_symphony_dispatches_open_job_idx
  ON public.lm_symphony_dispatches (tenant_id, job_id)
  WHERE status IN ('claimed', 'mirrored', 'result_ready');
CREATE INDEX IF NOT EXISTS lm_symphony_dispatches_tenant_status_idx
  ON public.lm_symphony_dispatches (tenant_id, status, updated_at DESC);

ALTER TABLE public.lm_symphony_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_symphony_dispatches FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_symphony_dispatches FROM PUBLIC, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.claim_lm_symphony_job(p_tenant_id text)
RETURNS SETOF public.lm_symphony_dispatches
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_round integer;
  v_dispatch_id text;
  v_dispatch public.lm_symphony_dispatches%ROWTYPE;
BEGIN
  IF p_tenant_id IS NULL OR p_tenant_id !~ '^[a-z0-9][a-z0-9._-]{0,199}$' THEN
    RAISE EXCEPTION 'symphony tenant invalid';
  END IF;

  SELECT * INTO v_job
  FROM public.lm_runtime_jobs AS jobs
  WHERE jobs.tenant_id = p_tenant_id
    AND jobs.loop_id = 'life-manager.manager'
    AND jobs.capability = 'general-agent.work'
    AND jobs.effect_class = 'none'
    AND jobs.status = 'queued'
    AND jobs.available_at <= clock_timestamp()
    AND jobs.attempt < jobs.max_attempts
    AND NOT EXISTS (
      SELECT 1 FROM public.lm_symphony_dispatches AS dispatches
      WHERE dispatches.tenant_id = jobs.tenant_id
        AND dispatches.job_id = jobs.job_id
        AND dispatches.status IN ('claimed', 'mirrored', 'result_ready')
    )
  ORDER BY jobs.available_at, jobs.created_at, jobs.job_id
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN; END IF;

  SELECT COALESCE(MAX(dispatches.round), 0) + 1 INTO v_round
  FROM public.lm_symphony_dispatches AS dispatches
  WHERE dispatches.tenant_id = v_job.tenant_id AND dispatches.job_id = v_job.job_id;
  v_dispatch_id := encode(digest(
    v_job.tenant_id || E'\n' || v_job.job_id || E'\n' || v_round::text,
    'sha256'
  ), 'hex');

  UPDATE public.lm_runtime_jobs
  SET status = 'waiting_agent',
      lease_owner = NULL,
      lease_expires_at = NULL,
      last_error_code = NULL,
      updated_at = clock_timestamp()
  WHERE tenant_id = v_job.tenant_id AND job_id = v_job.job_id AND status = 'queued';
  IF NOT FOUND THEN RAISE EXCEPTION 'symphony runtime job claim lost'; END IF;

  INSERT INTO public.lm_symphony_dispatches (
    tenant_id, dispatch_id, job_id, round, status
  ) VALUES (
    v_job.tenant_id, v_dispatch_id, v_job.job_id, v_round, 'claimed'
  ) RETURNING * INTO v_dispatch;
  RETURN NEXT v_dispatch;
END
$$;

REVOKE ALL ON FUNCTION public.claim_lm_symphony_job(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_symphony_job(text) TO service_role;

CREATE OR REPLACE FUNCTION public.record_lm_symphony_issue(
  p_tenant_id text,
  p_dispatch_id text,
  p_issue_ref text
) RETURNS SETOF public.lm_symphony_dispatches
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_dispatch public.lm_symphony_dispatches%ROWTYPE;
BEGIN
  IF p_tenant_id IS NULL OR p_tenant_id !~ '^[a-z0-9][a-z0-9._-]{0,199}$'
    OR p_dispatch_id IS NULL OR p_dispatch_id !~ '^[0-9a-f]{64}$'
    OR p_issue_ref IS NULL
    OR p_issue_ref !~ '^github-issue://Daisuke134/life-manager-workrooms/[1-9][0-9]*$' THEN
    RAISE EXCEPTION 'symphony issue input invalid';
  END IF;

  SELECT * INTO v_dispatch
  FROM public.lm_symphony_dispatches
  WHERE tenant_id = p_tenant_id AND dispatch_id = p_dispatch_id
  FOR UPDATE;
  IF NOT FOUND THEN RETURN; END IF;
  IF v_dispatch.status = 'mirrored' AND v_dispatch.issue_ref = p_issue_ref THEN
    RETURN NEXT v_dispatch;
    RETURN;
  END IF;
  IF v_dispatch.status <> 'claimed' OR v_dispatch.issue_ref IS NOT NULL THEN
    RAISE EXCEPTION 'symphony issue conflict';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.lm_runtime_jobs
    WHERE tenant_id = p_tenant_id AND job_id = v_dispatch.job_id AND status = 'waiting_agent'
  ) THEN
    RAISE EXCEPTION 'symphony issue runtime job unavailable';
  END IF;

  UPDATE public.lm_symphony_dispatches
  SET status = 'mirrored',
      issue_ref = p_issue_ref,
      mirrored_at = clock_timestamp(),
      updated_at = clock_timestamp()
  WHERE tenant_id = p_tenant_id AND dispatch_id = p_dispatch_id
    AND status = 'claimed' AND issue_ref IS NULL
  RETURNING * INTO v_dispatch;
  IF NOT FOUND THEN RAISE EXCEPTION 'symphony issue conflict'; END IF;
  RETURN NEXT v_dispatch;
END
$$;

REVOKE ALL ON FUNCTION public.record_lm_symphony_issue(text,text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_lm_symphony_issue(text,text,text) TO service_role;
