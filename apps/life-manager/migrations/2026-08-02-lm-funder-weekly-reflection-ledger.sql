-- O1C-20: append-only, tenant-bound weekly funding strategy revisions.

CREATE TABLE IF NOT EXISTS public.lm_funder_weekly_reflection_ledger (
  tenant_id text NOT NULL,
  reflection_id text NOT NULL CHECK (reflection_id ~ '^funder-weekly-reflection:[0-9a-f]{64}$'),
  week_key date NOT NULL,
  week_start timestamptz NOT NULL,
  week_end timestamptz NOT NULL CHECK (week_end > week_start),
  reflected_at timestamptz NOT NULL CHECK (reflected_at >= week_end),
  snapshot_digest text NOT NULL CHECK (snapshot_digest ~ '^[0-9a-f]{64}$'),
  decision text NOT NULL CHECK (decision IN ('hold','change')),
  reason text NOT NULL CHECK (reason IN ('insufficient_outcomes','agent_hold','agent_revision')),
  summary_sha256 text NOT NULL CHECK (summary_sha256 ~ '^[0-9a-f]{64}$'),
  rationale_sha256 text NOT NULL CHECK (rationale_sha256 ~ '^[0-9a-f]{64}$'),
  outcome_result_ids jsonb NOT NULL CHECK (jsonb_typeof(outcome_result_ids)='array'),
  ranked_candidate_ids jsonb NOT NULL CHECK (jsonb_typeof(ranked_candidate_ids)='array'),
  pitch_directives jsonb NOT NULL CHECK (jsonb_typeof(pitch_directives)='array'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, reflection_id),
  UNIQUE (tenant_id, week_key),
  UNIQUE (tenant_id, reflection_id, week_key),
  CHECK ((decision='change' AND reason='agent_revision') OR
         (decision='hold' AND reason IN ('insufficient_outcomes','agent_hold')))
);

CREATE TABLE IF NOT EXISTS public.lm_funder_outreach_reflection_application (
  tenant_id text NOT NULL,
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  reflection_id text NOT NULL CHECK (reflection_id ~ '^funder-weekly-reflection:[0-9a-f]{64}$'),
  week_key date NOT NULL,
  ranking_position integer NOT NULL CHECK (ranking_position >= 1),
  pitch_directive_sha256 text NOT NULL CHECK (pitch_directive_sha256 ~ '^[0-9a-f]{64}$'),
  outcome_result_ids jsonb NOT NULL CHECK (
    jsonb_typeof(outcome_result_ids)='array' AND jsonb_array_length(outcome_result_ids) >= 1
  ),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id,outreach_id),
  FOREIGN KEY (tenant_id,outreach_id)
    REFERENCES public.lm_funder_outreach_ledger (tenant_id,outreach_id) ON DELETE RESTRICT,
  FOREIGN KEY (tenant_id,reflection_id,week_key)
    REFERENCES public.lm_funder_weekly_reflection_ledger (tenant_id,reflection_id,week_key) ON DELETE RESTRICT
);

CREATE OR REPLACE FUNCTION public.lm_validate_funder_outreach_reflection_application()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_reflection public.lm_funder_weekly_reflection_ledger%ROWTYPE;
  v_candidate_id text;
  v_directive jsonb;
BEGIN
  SELECT * INTO v_reflection
  FROM public.lm_funder_weekly_reflection_ledger
  WHERE tenant_id=NEW.tenant_id AND reflection_id=NEW.reflection_id AND week_key=NEW.week_key;
  SELECT candidate_id INTO v_candidate_id
  FROM public.lm_funder_outreach_ledger
  WHERE tenant_id=NEW.tenant_id AND outreach_id=NEW.outreach_id;
  IF NOT FOUND OR v_reflection.reflection_id IS NULL OR v_reflection.decision <> 'change'
    OR jsonb_array_length(v_reflection.ranked_candidate_ids) < NEW.ranking_position
    OR v_reflection.ranked_candidate_ids ->> (NEW.ranking_position - 1) IS DISTINCT FROM v_candidate_id THEN
    RAISE EXCEPTION 'funder outreach reflection application invalid';
  END IF;
  SELECT item INTO v_directive
  FROM jsonb_array_elements(v_reflection.pitch_directives) AS item
  WHERE item->>'candidate_id'=v_candidate_id;
  IF v_directive IS NULL
    OR v_directive->>'directive_sha256' IS DISTINCT FROM NEW.pitch_directive_sha256
    OR v_directive->'outcome_result_ids' IS DISTINCT FROM NEW.outcome_result_ids THEN
    RAISE EXCEPTION 'funder outreach reflection application invalid';
  END IF;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS lm_funder_outreach_reflection_validate
  ON public.lm_funder_outreach_reflection_application;
CREATE TRIGGER lm_funder_outreach_reflection_validate
BEFORE INSERT ON public.lm_funder_outreach_reflection_application
FOR EACH ROW EXECUTE FUNCTION public.lm_validate_funder_outreach_reflection_application();

CREATE OR REPLACE FUNCTION public.lm_require_current_funder_outreach_reflection()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_reflection public.lm_funder_weekly_reflection_ledger%ROWTYPE;
BEGIN
  SELECT * INTO v_reflection
  FROM public.lm_funder_weekly_reflection_ledger reflected
  WHERE tenant_id=NEW.tenant_id AND reflected_at <= NEW.sent_at AND decision='change'
    AND NOT EXISTS (
      SELECT 1 FROM public.lm_funder_outreach_reflection_application applied
      WHERE applied.tenant_id=reflected.tenant_id
        AND applied.reflection_id=reflected.reflection_id
    )
  ORDER BY reflected_at DESC, week_key DESC LIMIT 1;
  IF v_reflection.decision='change' AND NOT EXISTS (
      SELECT 1 FROM public.lm_funder_outreach_reflection_application applied
      WHERE applied.tenant_id=NEW.tenant_id AND applied.outreach_id=NEW.outreach_id
        AND applied.reflection_id=v_reflection.reflection_id
    ) THEN
    RAISE EXCEPTION 'current funder outreach reflection application required';
  END IF;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS lm_funder_outreach_requires_current_reflection
  ON public.lm_funder_outreach_ledger;
CREATE CONSTRAINT TRIGGER lm_funder_outreach_requires_current_reflection
AFTER INSERT ON public.lm_funder_outreach_ledger
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION public.lm_require_current_funder_outreach_reflection();

CREATE OR REPLACE FUNCTION public.lm_funder_weekly_reflection_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lm_funder_weekly_reflection_ledger is append-only';
END
$$;

DROP TRIGGER IF EXISTS lm_funder_weekly_reflection_no_mutation
  ON public.lm_funder_weekly_reflection_ledger;
CREATE TRIGGER lm_funder_weekly_reflection_no_mutation
BEFORE UPDATE OR DELETE ON public.lm_funder_weekly_reflection_ledger
FOR EACH ROW EXECUTE FUNCTION public.lm_funder_weekly_reflection_immutable();

DROP TRIGGER IF EXISTS lm_funder_weekly_reflection_no_truncate
  ON public.lm_funder_weekly_reflection_ledger;
CREATE TRIGGER lm_funder_weekly_reflection_no_truncate
BEFORE TRUNCATE ON public.lm_funder_weekly_reflection_ledger
FOR EACH STATEMENT EXECUTE FUNCTION public.lm_funder_weekly_reflection_immutable();

DROP TRIGGER IF EXISTS lm_funder_outreach_reflection_no_mutation
  ON public.lm_funder_outreach_reflection_application;
CREATE TRIGGER lm_funder_outreach_reflection_no_mutation
BEFORE UPDATE OR DELETE ON public.lm_funder_outreach_reflection_application
FOR EACH ROW EXECUTE FUNCTION public.lm_funder_weekly_reflection_immutable();

DROP TRIGGER IF EXISTS lm_funder_outreach_reflection_no_truncate
  ON public.lm_funder_outreach_reflection_application;
CREATE TRIGGER lm_funder_outreach_reflection_no_truncate
BEFORE TRUNCATE ON public.lm_funder_outreach_reflection_application
FOR EACH STATEMENT EXECUTE FUNCTION public.lm_funder_weekly_reflection_immutable();

ALTER TABLE public.lm_funder_weekly_reflection_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_funder_outreach_reflection_application ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_weekly_reflection_ledger FROM PUBLIC;
REVOKE ALL ON TABLE public.lm_funder_outreach_reflection_application FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON TABLE public.lm_funder_weekly_reflection_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_weekly_reflection_ledger FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_outreach_reflection_application FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_weekly_reflection_ledger FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_outreach_reflection_application FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
    EXECUTE 'REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.lm_funder_weekly_reflection_ledger FROM service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_weekly_reflection_ledger TO service_role';
    EXECUTE 'REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.lm_funder_outreach_reflection_application FROM service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_outreach_reflection_application TO service_role';
  END IF;
END
$$;
