-- Portable Life Manager runtime queue.
-- External-effect jobs fail closed: an expired or unknown publish/message/money attempt
-- enters reconciliation and is never retried until the provider proves it was absent.

CREATE TABLE IF NOT EXISTS public.lm_runtime_jobs (
  job_id text PRIMARY KEY CHECK (char_length(job_id) BETWEEN 1 AND 200),
  tenant_id text NOT NULL CHECK (char_length(tenant_id) BETWEEN 1 AND 200),
  loop_id text NOT NULL CHECK (char_length(loop_id) BETWEEN 1 AND 200),
  capability text NOT NULL CHECK (char_length(capability) BETWEEN 1 AND 200),
  effect_class text NOT NULL CHECK (
    effect_class IN ('none', 'publish', 'message', 'money')
  ),
  effect_key text CHECK (effect_key IS NULL OR char_length(effect_key) BETWEEN 1 AND 500),
  input_refs jsonb NOT NULL CHECK (
    jsonb_typeof(input_refs) = 'object'
    AND octet_length(input_refs::text) <= 16384
  ),
  max_attempts integer NOT NULL CHECK (max_attempts BETWEEN 1 AND 20),
  attempt integer NOT NULL DEFAULT 0 CHECK (attempt BETWEEN 0 AND max_attempts),
  status text NOT NULL DEFAULT 'queued' CHECK (
    status IN ('queued', 'running', 'reconciling', 'completed', 'dead_letter')
  ),
  available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  lease_owner text CHECK (lease_owner IS NULL OR char_length(lease_owner) BETWEEN 1 AND 200),
  lease_expires_at timestamptz,
  last_error_code text CHECK (
    last_error_code IS NULL OR char_length(last_error_code) BETWEEN 1 AND 200
  ),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  completed_at timestamptz,
  UNIQUE (job_id, tenant_id),
  UNIQUE (tenant_id, effect_key),
  CHECK (
    (effect_class = 'none' AND effect_key IS NULL)
    OR (effect_class IN ('publish', 'message', 'money') AND effect_key IS NOT NULL)
  ),
  CHECK (
    (status = 'running' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)
    OR (status <> 'running' AND lease_owner IS NULL AND lease_expires_at IS NULL)
  ),
  CHECK (
    (status = 'completed' AND completed_at IS NOT NULL)
    OR (status <> 'completed' AND completed_at IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS lm_runtime_jobs_claim_idx
  ON public.lm_runtime_jobs (capability, status, available_at, created_at);
CREATE INDEX IF NOT EXISTS lm_runtime_jobs_tenant_recent_idx
  ON public.lm_runtime_jobs (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS lm_runtime_jobs_reconciliation_idx
  ON public.lm_runtime_jobs (status, effect_class, updated_at)
  WHERE status = 'reconciling';

CREATE TABLE IF NOT EXISTS public.lm_runtime_job_receipts (
  job_id text NOT NULL,
  tenant_id text NOT NULL,
  attempt integer NOT NULL CHECK (attempt > 0),
  outcome text NOT NULL CHECK (
    outcome IN ('completed', 'failed', 'reconciled_present', 'reconciled_absent')
  ),
  effect_key text,
  receipt jsonb NOT NULL CHECK (
    jsonb_typeof(receipt) = 'object'
    AND octet_length(receipt::text) <= 16384
  ),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (job_id, attempt),
  FOREIGN KEY (job_id, tenant_id)
    REFERENCES public.lm_runtime_jobs (job_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS lm_runtime_job_receipts_tenant_idx
  ON public.lm_runtime_job_receipts (tenant_id, created_at DESC);

-- Receipt rows are immutable audit evidence. Idempotent writes return the existing row;
-- UPDATE and DELETE are always rejected.
CREATE OR REPLACE FUNCTION public.reject_lm_runtime_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'runtime job receipts are immutable';
END
$$;

DROP TRIGGER IF EXISTS lm_runtime_job_receipts_immutable
  ON public.lm_runtime_job_receipts;
CREATE TRIGGER lm_runtime_job_receipts_immutable
BEFORE UPDATE OR DELETE ON public.lm_runtime_job_receipts
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_runtime_receipt_mutation();

CREATE OR REPLACE FUNCTION public.claim_lm_runtime_jobs(
  p_worker_id text,
  p_capabilities text[],
  p_tenant_id text DEFAULT NULL,
  p_limit integer DEFAULT 1,
  p_lease_seconds integer DEFAULT 180
) RETURNS SETOF public.lm_runtime_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_worker_id IS NULL OR char_length(p_worker_id) NOT BETWEEN 1 AND 200 THEN
    RAISE EXCEPTION 'runtime worker id invalid';
  END IF;
  IF p_capabilities IS NULL OR cardinality(p_capabilities) < 1 THEN
    RAISE EXCEPTION 'runtime capabilities invalid';
  END IF;
  IF p_limit < 1 OR p_limit > 50 THEN
    RAISE EXCEPTION 'runtime claim limit invalid';
  END IF;
  IF p_lease_seconds < 30 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'runtime lease invalid';
  END IF;

  -- An expired external effect is ambiguous. Quarantine it before selecting retryable work.
  UPDATE public.lm_runtime_jobs
  SET status = 'reconciling',
      lease_owner = NULL,
      lease_expires_at = NULL,
      last_error_code = 'LEASE_EXPIRED_EFFECT_UNKNOWN',
      updated_at = clock_timestamp()
  WHERE status = 'running'
    AND lease_expires_at <= clock_timestamp()
    AND effect_class IN ('publish', 'message', 'money')
    AND (p_tenant_id IS NULL OR tenant_id = p_tenant_id);

  RETURN QUERY
  WITH candidates AS (
    SELECT job_id
    FROM public.lm_runtime_jobs
    WHERE capability = ANY (p_capabilities)
      AND (p_tenant_id IS NULL OR tenant_id = p_tenant_id)
      AND available_at <= clock_timestamp()
      AND attempt < max_attempts
      AND (
        status = 'queued'
        OR (
          status = 'running'
          AND effect_class = 'none'
          AND lease_expires_at <= clock_timestamp()
        )
      )
    ORDER BY available_at, created_at, job_id
    FOR UPDATE SKIP LOCKED
    LIMIT p_limit
  )
  UPDATE public.lm_runtime_jobs AS jobs
  SET status = 'running',
      attempt = jobs.attempt + 1,
      lease_owner = p_worker_id,
      lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds),
      last_error_code = NULL,
      updated_at = clock_timestamp()
  FROM candidates
  WHERE jobs.job_id = candidates.job_id
    AND jobs.attempt < jobs.max_attempts
  RETURNING jobs.*;
END
$$;

CREATE OR REPLACE FUNCTION public.heartbeat_lm_runtime_job(
  p_tenant_id text,
  p_job_id text,
  p_attempt integer,
  p_worker_id text,
  p_lease_seconds integer DEFAULT 180
) RETURNS SETOF public.lm_runtime_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_lease_seconds < 30 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'runtime lease invalid';
  END IF;
  RETURN QUERY
  UPDATE public.lm_runtime_jobs
  SET lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds),
      updated_at = clock_timestamp()
  WHERE tenant_id = p_tenant_id
    AND job_id = p_job_id
    AND attempt = p_attempt
    AND status = 'running'
    AND lease_owner = p_worker_id
    AND lease_expires_at > clock_timestamp()
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.complete_lm_runtime_job(
  p_tenant_id text,
  p_job_id text,
  p_attempt integer,
  p_worker_id text,
  p_receipt jsonb
) RETURNS SETOF public.lm_runtime_job_receipts
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  v_existing public.lm_runtime_job_receipts%ROWTYPE;
BEGIN
  IF jsonb_typeof(p_receipt) <> 'object' OR octet_length(p_receipt::text) > 16384 THEN
    RAISE EXCEPTION 'runtime receipt invalid';
  END IF;

  SELECT * INTO v_existing
  FROM public.lm_runtime_job_receipts
  WHERE tenant_id = p_tenant_id AND job_id = p_job_id AND attempt = p_attempt;
  IF FOUND THEN
    IF v_existing.outcome <> 'completed' OR v_existing.receipt <> p_receipt THEN
      RAISE EXCEPTION 'runtime receipt conflict';
    END IF;
    RETURN NEXT v_existing;
    RETURN;
  END IF;

  RETURN QUERY
  WITH completed AS (
    UPDATE public.lm_runtime_jobs
    SET status = 'completed',
        lease_owner = NULL,
        lease_expires_at = NULL,
        completed_at = clock_timestamp(),
        updated_at = clock_timestamp()
    WHERE tenant_id = p_tenant_id
      AND job_id = p_job_id
      AND attempt = p_attempt
      AND status = 'running'
      AND lease_owner = p_worker_id
    RETURNING job_id, tenant_id, attempt, effect_key
  )
  INSERT INTO public.lm_runtime_job_receipts (
    job_id, tenant_id, attempt, outcome, effect_key, receipt
  )
  SELECT job_id, tenant_id, attempt, 'completed', effect_key, p_receipt
  FROM completed
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.fail_lm_runtime_job(
  p_tenant_id text,
  p_job_id text,
  p_attempt integer,
  p_worker_id text,
  p_error_code text,
  p_unknown_effect boolean DEFAULT false
) RETURNS SETOF public.lm_runtime_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_status text;
BEGIN
  IF p_error_code IS NULL OR char_length(p_error_code) NOT BETWEEN 1 AND 200 THEN
    RAISE EXCEPTION 'runtime error code invalid';
  END IF;

  SELECT * INTO v_job
  FROM public.lm_runtime_jobs
  WHERE tenant_id = p_tenant_id
    AND job_id = p_job_id
    AND attempt = p_attempt
    AND status = 'running'
    AND lease_owner = p_worker_id
  FOR UPDATE;
  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF p_unknown_effect AND v_job.effect_class IN ('publish', 'message', 'money') THEN
    v_status := 'reconciling';
  ELSIF v_job.attempt < v_job.max_attempts THEN
    v_status := 'queued';
  ELSE
    v_status := 'dead_letter';
  END IF;

  IF v_status <> 'reconciling' THEN
    INSERT INTO public.lm_runtime_job_receipts (
      job_id, tenant_id, attempt, outcome, effect_key, receipt
    ) VALUES (
      v_job.job_id,
      v_job.tenant_id,
      v_job.attempt,
      'failed',
      v_job.effect_key,
      jsonb_build_object('error_code', p_error_code)
    );
  END IF;

  RETURN QUERY
  UPDATE public.lm_runtime_jobs
  SET status = v_status,
      lease_owner = NULL,
      lease_expires_at = NULL,
      last_error_code = p_error_code,
      updated_at = clock_timestamp()
  WHERE tenant_id = p_tenant_id
    AND job_id = p_job_id
    AND attempt = p_attempt
    AND status = 'running'
    AND lease_owner = p_worker_id
  RETURNING *;
END
$$;

CREATE OR REPLACE FUNCTION public.resolve_lm_runtime_effect(
  p_tenant_id text,
  p_job_id text,
  p_attempt integer,
  p_decision text,
  p_receipt jsonb
) RETURNS SETOF public.lm_runtime_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_existing public.lm_runtime_job_receipts%ROWTYPE;
  v_status text;
  v_outcome text;
BEGIN
  IF p_decision NOT IN ('present', 'absent') THEN
    RAISE EXCEPTION 'runtime reconciliation decision invalid';
  END IF;
  IF jsonb_typeof(p_receipt) <> 'object' OR octet_length(p_receipt::text) > 16384 THEN
    RAISE EXCEPTION 'runtime reconciliation receipt invalid';
  END IF;

  SELECT * INTO v_existing
  FROM public.lm_runtime_job_receipts
  WHERE tenant_id = p_tenant_id AND job_id = p_job_id AND attempt = p_attempt;
  IF FOUND THEN
    v_outcome := CASE
      WHEN p_decision = 'present' THEN 'reconciled_present'
      ELSE 'reconciled_absent'
    END;
    IF v_existing.outcome <> v_outcome OR v_existing.receipt <> p_receipt THEN
      RAISE EXCEPTION 'runtime reconciliation receipt conflict';
    END IF;
    RETURN QUERY
    SELECT *
    FROM public.lm_runtime_jobs
    WHERE tenant_id = p_tenant_id AND job_id = p_job_id;
    RETURN;
  END IF;

  SELECT * INTO v_job
  FROM public.lm_runtime_jobs
  WHERE tenant_id = p_tenant_id
    AND job_id = p_job_id
    AND attempt = p_attempt
    AND status = 'reconciling'
    AND effect_class IN ('publish', 'message', 'money')
  FOR UPDATE;
  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF p_decision = 'present' THEN
    v_status := 'completed';
    v_outcome := 'reconciled_present';
  ELSIF v_job.attempt < v_job.max_attempts THEN
    v_status := 'queued';
    v_outcome := 'reconciled_absent';
  ELSE
    v_status := 'dead_letter';
    v_outcome := 'reconciled_absent';
  END IF;

  INSERT INTO public.lm_runtime_job_receipts (
    job_id, tenant_id, attempt, outcome, effect_key, receipt
  ) VALUES (
    v_job.job_id,
    v_job.tenant_id,
    v_job.attempt,
    v_outcome,
    v_job.effect_key,
    p_receipt
  );

  RETURN QUERY
  UPDATE public.lm_runtime_jobs
  SET status = v_status,
      last_error_code = CASE
        WHEN p_decision = 'absent' THEN 'EFFECT_PROVEN_ABSENT'
        ELSE NULL
      END,
      completed_at = CASE
        WHEN p_decision = 'present' THEN clock_timestamp()
        ELSE NULL
      END,
      updated_at = clock_timestamp()
  WHERE tenant_id = p_tenant_id
    AND job_id = p_job_id
    AND attempt = p_attempt
    AND status = 'reconciling'
  RETURNING *;
END
$$;
