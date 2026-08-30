-- Additive recovery fence for the local bridge process boundary.
-- A consumed dispatch remains recoverable until the bridge has read the
-- provider CLOSED state and durably acknowledged that fact here.

ALTER TABLE public.lm_symphony_dispatches
  ADD COLUMN IF NOT EXISTS issue_closed_at timestamptz;

ALTER TABLE public.lm_symphony_dispatches
  DROP CONSTRAINT IF EXISTS lm_symphony_dispatches_issue_closed_at_check;

ALTER TABLE public.lm_symphony_dispatches
  ADD CONSTRAINT lm_symphony_dispatches_issue_closed_at_check
  CHECK (issue_closed_at IS NULL OR status = 'consumed');

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

  SELECT * INTO v_dispatch
  FROM public.lm_symphony_dispatches AS dispatches
  WHERE dispatches.tenant_id = p_tenant_id
    AND dispatches.status IN ('claimed', 'mirrored', 'result_ready', 'consumed')
    AND dispatches.issue_closed_at IS NULL
  ORDER BY dispatches.claimed_at, dispatches.dispatch_id
  FOR UPDATE
  LIMIT 1;
  IF FOUND THEN
    RETURN NEXT v_dispatch;
    RETURN;
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

CREATE OR REPLACE FUNCTION public.ack_lm_symphony_issue_closed(
  p_tenant_id text,
  p_dispatch_id text,
  p_issue_ref text,
  p_result_ref text,
  p_result_hash text
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
    OR p_issue_ref !~ '^github-issue://Daisuke134/life-manager-workrooms/[1-9][0-9]*$'
    OR p_result_ref IS NULL
    OR p_result_ref !~ '^github-comment://Daisuke134/life-manager-workrooms/[1-9][0-9]*/[1-9][0-9]*$'
    OR p_result_hash IS NULL OR p_result_hash !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'symphony issue close input invalid';
  END IF;

  SELECT * INTO v_dispatch
  FROM public.lm_symphony_dispatches
  WHERE tenant_id = p_tenant_id AND dispatch_id = p_dispatch_id
  FOR UPDATE;
  IF NOT FOUND THEN RETURN; END IF;

  IF v_dispatch.status <> 'consumed'
    OR v_dispatch.issue_ref <> p_issue_ref
    OR v_dispatch.result_ref <> p_result_ref
    OR v_dispatch.result_hash <> p_result_hash THEN
    RAISE EXCEPTION 'symphony issue close conflict';
  END IF;

  IF v_dispatch.issue_closed_at IS NULL THEN
    UPDATE public.lm_symphony_dispatches
    SET issue_closed_at = clock_timestamp(),
        updated_at = clock_timestamp()
    WHERE tenant_id = p_tenant_id
      AND dispatch_id = p_dispatch_id
      AND status = 'consumed'
      AND issue_ref = p_issue_ref
      AND result_ref = p_result_ref
      AND result_hash = p_result_hash
      AND issue_closed_at IS NULL
    RETURNING * INTO v_dispatch;
    IF NOT FOUND THEN RAISE EXCEPTION 'symphony issue close conflict'; END IF;
  END IF;

  RETURN NEXT v_dispatch;
END
$$;

REVOKE ALL ON FUNCTION public.ack_lm_symphony_issue_closed(text,text,text,text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ack_lm_symphony_issue_closed(text,text,text,text,text) TO service_role;
