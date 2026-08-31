-- Unknown-aging for the reconciliation quarantine (extends 20260729_runtime_jobs.sql).
-- A reconciling external effect whose provider cannot answer stays quarantined, but not
-- forever: each unknown reconcile result increments a durable counter, and when the
-- counter reaches the caller-supplied bound (runtime constant = 5) the job dead-letters
-- with RECONCILE_UNKNOWN_EXHAUSTED so an operator sees it instead of a silent loop.
-- Resolution (present or absent) resets the counter so a later reconciliation lifecycle
-- starts its own aging window.

ALTER TABLE public.lm_runtime_jobs
  ADD COLUMN IF NOT EXISTS reconcile_attempts integer NOT NULL DEFAULT 0
    CHECK (reconcile_attempts >= 0);

-- One unknown reconcile result for one reconciling attempt. Returns the updated job row;
-- returns nothing when the job is no longer reconciling (already resolved or dead).
CREATE OR REPLACE FUNCTION public.age_lm_runtime_reconciliation(
  p_tenant_id text,
  p_job_id text,
  p_attempt integer,
  p_max_unknown integer DEFAULT 5
) RETURNS SETOF public.lm_runtime_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
  v_job public.lm_runtime_jobs%ROWTYPE;
BEGIN
  IF p_max_unknown < 1 OR p_max_unknown > 20 THEN
    RAISE EXCEPTION 'runtime unknown limit invalid';
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

  IF v_job.reconcile_attempts + 1 >= p_max_unknown THEN
    -- The receipt slot for this attempt is free: a reconciling attempt has no receipt
    -- until it is resolved, and this path replaces resolution with dead-lettering.
    INSERT INTO public.lm_runtime_job_receipts (
      job_id, tenant_id, attempt, outcome, effect_key, receipt
    ) VALUES (
      v_job.job_id,
      v_job.tenant_id,
      v_job.attempt,
      'failed',
      v_job.effect_key,
      jsonb_build_object(
        'error_code', 'RECONCILE_UNKNOWN_EXHAUSTED',
        'unknown_results', v_job.reconcile_attempts + 1
      )
    );
    RETURN QUERY
    UPDATE public.lm_runtime_jobs
    SET status = 'dead_letter',
        reconcile_attempts = reconcile_attempts + 1,
        last_error_code = 'RECONCILE_UNKNOWN_EXHAUSTED',
        updated_at = clock_timestamp()
    WHERE tenant_id = p_tenant_id
      AND job_id = p_job_id
      AND attempt = p_attempt
      AND status = 'reconciling'
    RETURNING *;
  ELSE
    RETURN QUERY
    UPDATE public.lm_runtime_jobs
    SET reconcile_attempts = reconcile_attempts + 1,
        updated_at = clock_timestamp()
    WHERE tenant_id = p_tenant_id
      AND job_id = p_job_id
      AND attempt = p_attempt
      AND status = 'reconciling'
    RETURNING *;
  END IF;
END
$$;

-- Supersedes the 20260729 definition: identical behavior plus reconcile_attempts = 0 on
-- resolution, so the aging window is scoped to one reconciliation lifecycle.
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
      reconcile_attempts = 0,
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
