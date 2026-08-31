-- Task 7A: durable public opportunities and one effect-free goal job.
-- The table is a service-owned projection root; private credentials and external state stay elsewhere.

CREATE TABLE IF NOT EXISTS public.lm_money_opportunities (
  uid text NOT NULL CHECK (uid ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  opportunity_id text NOT NULL CHECK (opportunity_id ~ '^[0-9a-f]{64}$'),
  source_url text NOT NULL CHECK (
    source_url ~ '^https://[^[:space:]@/]+([/?#][^[:space:]]*)?$'
  ),
  title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 300),
  goal_statement text NOT NULL CHECK (char_length(goal_statement) BETWEEN 1 AND 4000),
  value_minor numeric NOT NULL CHECK (value_minor = trunc(value_minor) AND value_minor >= 0),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  status text NOT NULL DEFAULT 'DISCOVERED' CHECK (status IN (
    'DISCOVERED', 'QUALIFYING', 'QUALIFIED', 'CLAIMED', 'WORKING',
    'READY_FOR_EFFECT', 'QA_ACCEPTED', 'NEEDS_HUMAN', 'EFFECT_UNCERTAIN',
    'SUBMITTED', 'WON', 'CONTRACTED', 'PAYMENT_PENDING', 'INELIGIBLE',
    'EXPIRED', 'LOST', 'DELIVERED', 'PAID_SETTLED', 'REVENUE_RECORDED'
  )),
  goal_ref text NOT NULL CHECK (
    goal_ref ~ '^intent-entry://[a-z0-9][a-z0-9._-]{0,199}/[0-9a-f]{64}$'
  ),
  observed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, opportunity_id),
  UNIQUE (uid, source_url)
);

CREATE INDEX IF NOT EXISTS lm_money_opportunities_uid_status_idx
  ON public.lm_money_opportunities (uid, status, updated_at DESC);

ALTER TABLE public.lm_money_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_money_opportunities FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_money_opportunities FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_money_opportunities TO service_role;

CREATE OR REPLACE FUNCTION public.create_lm_money_opportunity(
  p_uid text,
  p_opportunity_id text,
  p_source_url text,
  p_title text,
  p_goal_statement text,
  p_value_minor numeric,
  p_currency text,
  p_observed_at timestamptz,
  p_goal_ref text
) RETURNS SETOF public.lm_money_opportunities
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_opportunity public.lm_money_opportunities%ROWTYPE;
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_job_id text;
  v_goal_refs jsonb;
  v_digest text;
BEGIN
  IF p_uid IS NULL OR p_uid <> btrim(p_uid) OR p_uid !~ '^[a-z0-9][a-z0-9._-]{0,199}$'
    OR p_opportunity_id IS NULL OR p_opportunity_id !~ '^[0-9a-f]{64}$'
    OR p_source_url IS NULL OR p_source_url <> btrim(p_source_url)
    OR p_source_url !~ '^https://[^[:space:]@/]+([/?#][^[:space:]]*)?$'
    OR p_title IS NULL OR p_title <> btrim(p_title) OR char_length(p_title) NOT BETWEEN 1 AND 300
    OR p_goal_statement IS NULL OR p_goal_statement <> btrim(p_goal_statement)
       OR char_length(p_goal_statement) NOT BETWEEN 1 AND 4000
    OR p_value_minor IS NULL OR p_value_minor <> trunc(p_value_minor) OR p_value_minor < 0
       OR p_value_minor::text !~ '^[0-9]+$'
    OR p_currency IS NULL OR p_currency !~ '^[A-Z]{3}$'
    OR p_observed_at IS NULL
    OR p_goal_ref IS NULL
    OR p_goal_ref <> 'intent-entry://' || p_uid || '/' || p_opportunity_id THEN
    RAISE EXCEPTION 'money printer opportunity input invalid';
  END IF;

  v_digest := encode(digest(p_uid || E'\n' || p_source_url, 'sha256'), 'hex');
  IF v_digest <> p_opportunity_id THEN
    RAISE EXCEPTION 'money printer opportunity identity conflict';
  END IF;
  v_job_id := 'goal:' || p_opportunity_id;
  v_goal_refs := jsonb_build_object('goal_ref', p_goal_ref);

  INSERT INTO public.lm_money_opportunities (
    uid, opportunity_id, source_url, title, goal_statement, value_minor,
    currency, status, goal_ref, observed_at
  ) VALUES (
    p_uid, p_opportunity_id, p_source_url, p_title, p_goal_statement, p_value_minor,
    p_currency, 'DISCOVERED', p_goal_ref, p_observed_at
  )
  ON CONFLICT DO NOTHING
  RETURNING * INTO v_opportunity;
  IF NOT FOUND THEN
    SELECT * INTO v_opportunity
    FROM public.lm_money_opportunities
    WHERE uid = p_uid AND opportunity_id = p_opportunity_id
    FOR UPDATE;
    IF NOT FOUND THEN
      SELECT * INTO v_opportunity
      FROM public.lm_money_opportunities
      WHERE uid = p_uid AND source_url = p_source_url
      FOR UPDATE;
    END IF;
  END IF;
  IF NOT FOUND AND v_opportunity.opportunity_id IS NULL THEN
    RAISE EXCEPTION 'money printer opportunity create conflict';
  END IF;
  IF v_opportunity.opportunity_id IS NOT NULL THEN
    IF v_opportunity.opportunity_id IS DISTINCT FROM p_opportunity_id
      OR v_opportunity.source_url IS DISTINCT FROM p_source_url
      OR v_opportunity.title IS DISTINCT FROM p_title
      OR v_opportunity.goal_statement IS DISTINCT FROM p_goal_statement
      OR v_opportunity.value_minor IS DISTINCT FROM p_value_minor
      OR v_opportunity.currency IS DISTINCT FROM p_currency
      OR v_opportunity.goal_ref IS DISTINCT FROM p_goal_ref THEN
      RAISE EXCEPTION 'money printer opportunity conflict';
    END IF;
  END IF;

  INSERT INTO public.lm_runtime_jobs (
    job_id, tenant_id, loop_id, capability, effect_class, effect_key, input_refs, max_attempts
  ) VALUES (
    v_job_id, p_uid, 'mr-bot.manager', 'general-agent.work', 'none', NULL, v_goal_refs, 1
  )
  ON CONFLICT (job_id) DO NOTHING
  RETURNING * INTO v_job;
  IF NOT FOUND THEN
    SELECT * INTO v_job
    FROM public.lm_runtime_jobs
    WHERE job_id = v_job_id
    FOR UPDATE;
  END IF;
  IF NOT FOUND
    OR v_job.tenant_id IS DISTINCT FROM p_uid
    OR v_job.loop_id IS DISTINCT FROM 'mr-bot.manager'
    OR v_job.capability IS DISTINCT FROM 'general-agent.work'
    OR v_job.effect_class IS DISTINCT FROM 'none'
    OR v_job.effect_key IS NOT NULL
    OR v_job.input_refs IS DISTINCT FROM v_goal_refs
    OR v_job.max_attempts IS DISTINCT FROM 1 THEN
    RAISE EXCEPTION 'money printer runtime job conflict';
  END IF;

  RETURN NEXT v_opportunity;
END;
$$;

REVOKE ALL ON FUNCTION public.create_lm_money_opportunity(text,text,text,text,text,numeric,text,timestamptz,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_lm_money_opportunity(text,text,text,text,text,numeric,text,timestamptz,text)
  TO service_role;
