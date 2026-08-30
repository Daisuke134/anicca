-- Serialize one tenant's Symphony claims, cap open rounds, and poll mirrors fairly.

ALTER TABLE public.lm_symphony_dispatches
  ADD COLUMN IF NOT EXISTS last_polled_at timestamptz;

CREATE OR REPLACE FUNCTION public.claim_lm_symphony_job(p_tenant_id text)
RETURNS SETOF public.lm_symphony_dispatches
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_dispatch public.lm_symphony_dispatches%ROWTYPE;
  v_round integer;
  v_dispatch_id text;
  v_open_count integer;
BEGIN
  IF p_tenant_id IS NULL OR p_tenant_id !~ '^[a-z0-9][a-z0-9._-]{0,199}$' THEN
    RAISE EXCEPTION 'symphony tenant invalid';
  END IF;

  PERFORM 1
  FROM public.lm_users AS tenants
  WHERE tenants.uid = p_tenant_id
  FOR UPDATE SKIP LOCKED;
  IF NOT FOUND THEN RETURN; END IF;

  SELECT * INTO v_dispatch
  FROM public.lm_symphony_dispatches AS dispatches
  WHERE dispatches.tenant_id = p_tenant_id
    AND dispatches.status IN ('claimed', 'result_ready', 'consumed')
    AND dispatches.issue_closed_at IS NULL
  ORDER BY dispatches.claimed_at, dispatches.dispatch_id
  FOR UPDATE
  LIMIT 1;
  IF FOUND THEN
    RETURN NEXT v_dispatch;
    RETURN;
  END IF;

  SELECT count(*) INTO v_open_count
  FROM public.lm_symphony_dispatches AS dispatches
  WHERE dispatches.tenant_id = p_tenant_id
    AND dispatches.status IN ('claimed', 'mirrored', 'result_ready', 'consumed')
    AND dispatches.issue_closed_at IS NULL;

  IF v_open_count < 2 THEN
    SELECT * INTO v_job
    FROM public.lm_runtime_jobs AS jobs
    WHERE jobs.tenant_id = p_tenant_id
      AND jobs.loop_id = 'life-manager.manager'
      AND jobs.capability = 'general-agent.work'
      AND jobs.effect_class = 'none'
      AND jobs.status = 'queued'
      AND jobs.available_at <= clock_timestamp()
      AND jobs.attempt < jobs.max_attempts
      AND EXISTS (
        SELECT 1
        FROM public.lm_money_opportunities AS opportunities
        WHERE opportunities.uid = jobs.tenant_id
          AND jobs.job_id = 'goal:' || opportunities.opportunity_id
      )
      AND NOT EXISTS (
        SELECT 1 FROM public.lm_symphony_dispatches AS dispatches
        WHERE dispatches.tenant_id = jobs.tenant_id
          AND dispatches.job_id = jobs.job_id
          AND dispatches.status IN ('claimed', 'mirrored', 'result_ready')
      )
    ORDER BY jobs.available_at, jobs.created_at, jobs.job_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1;
    IF FOUND THEN
      SELECT COALESCE(MAX(dispatches.round), 0) + 1 INTO v_round
      FROM public.lm_symphony_dispatches AS dispatches
      WHERE dispatches.tenant_id = v_job.tenant_id AND dispatches.job_id = v_job.job_id;
      v_dispatch_id := encode(digest(
        v_job.tenant_id || E'\n' || v_job.job_id || E'\n' || v_round::text,
        'sha256'
      ), 'hex');

      UPDATE public.lm_runtime_jobs
      SET status = 'waiting_agent', lease_owner = NULL, lease_expires_at = NULL,
          last_error_code = NULL, updated_at = clock_timestamp()
      WHERE tenant_id = v_job.tenant_id AND job_id = v_job.job_id AND status = 'queued';
      IF NOT FOUND THEN RAISE EXCEPTION 'symphony runtime job claim lost'; END IF;

      INSERT INTO public.lm_symphony_dispatches (tenant_id, dispatch_id, job_id, round, status)
      VALUES (v_job.tenant_id, v_dispatch_id, v_job.job_id, v_round, 'claimed')
      RETURNING * INTO v_dispatch;
      RETURN NEXT v_dispatch;
      RETURN;
    END IF;
  END IF;

  SELECT * INTO v_dispatch
  FROM public.lm_symphony_dispatches AS dispatches
  WHERE dispatches.tenant_id = p_tenant_id
    AND dispatches.status = 'mirrored'
    AND dispatches.issue_closed_at IS NULL
  ORDER BY COALESCE(dispatches.last_polled_at, dispatches.mirrored_at, dispatches.claimed_at),
    dispatches.claimed_at, dispatches.dispatch_id
  FOR UPDATE
  LIMIT 1;
  IF FOUND THEN
    UPDATE public.lm_symphony_dispatches
    SET last_polled_at = clock_timestamp(), updated_at = clock_timestamp()
    WHERE tenant_id = p_tenant_id AND dispatch_id = v_dispatch.dispatch_id
      AND status = 'mirrored' AND issue_closed_at IS NULL
    RETURNING * INTO v_dispatch;
    RETURN NEXT v_dispatch;
  END IF;
END
$$;

REVOKE ALL ON FUNCTION public.claim_lm_symphony_job(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_symphony_job(text) TO service_role;
