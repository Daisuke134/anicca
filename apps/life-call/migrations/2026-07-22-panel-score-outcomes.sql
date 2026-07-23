-- PANEL-8g: immutable outcome ledger and one-statement score snapshot.
CREATE TABLE IF NOT EXISTS public.lm_score_outcomes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  organ text NOT NULL CHECK (organ IN ('daily', 'physical', 'mental', 'financial')),
  entity_key text NOT NULL CHECK (length(entity_key) BETWEEN 1 AND 512),
  outcome_kind text NOT NULL,
  outcome_status text NOT NULL,
  revision_key uuid NOT NULL CHECK (revision_key <> '00000000-0000-0000-0000-000000000000'::uuid),
  occurred_at timestamptz NOT NULL,
  resolved_at timestamptz,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  amount_minor numeric,
  currency text,
  components jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(components) = 'object'),
  CONSTRAINT lm_score_outcomes_revision_key_unique UNIQUE (uid, organ, entity_key, outcome_kind, revision_key),
  CONSTRAINT lm_score_outcomes_amount_safe CHECK (amount_minor IS NULL OR (amount_minor = trunc(amount_minor) AND amount_minor >= 0 AND amount_minor <= 9007199254740991)),
  CONSTRAINT lm_score_outcomes_currency_shape CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
  CONSTRAINT lm_score_outcomes_financial_fields CHECK (
    (organ = 'financial' AND amount_minor IS NOT NULL AND currency IS NOT NULL)
    OR (organ <> 'financial' AND amount_minor IS NULL AND currency IS NULL)
  ),
  CONSTRAINT lm_score_outcomes_kind_status CHECK (
    (organ = 'daily' AND outcome_kind IN ('daily_travel', 'daily_call', 'daily_late') AND outcome_status IN ('required_succeeded', 'required_failed', 'required_pending', 'context_unnecessary', 'optional'))
    OR (organ = 'physical' AND outcome_kind = 'physical_need' AND outcome_status IN ('detected', 'candidate', 'search', 'unconfirmed_request', 'confirmed_booking', 'confirmed_completion', 'unresolved'))
    OR (organ = 'mental' AND outcome_kind = 'mental_trigger' AND outcome_status IN ('delivered', 'suppression_honored', 'correction_persisted', 'cap_overflow', 'unresolved'))
    OR (organ = 'financial' AND (
      (outcome_kind = 'financial_external_income' AND outcome_status = 'verified')
      OR (outcome_kind = 'financial_realized_loss' AND outcome_status = 'realized')
      OR (outcome_kind = 'financial_fee' AND outcome_status = 'charged')
      OR (outcome_kind = 'financial_user_transfer' AND outcome_status = 'confirmed')
      OR (outcome_kind IN ('financial_self_funding', 'financial_deposit', 'financial_internal_move', 'financial_unverified') AND outcome_status = 'excluded')
    ))
  )
);

CREATE INDEX IF NOT EXISTS lm_score_outcomes_period_idx
  ON public.lm_score_outcomes (uid, organ, occurred_at, recorded_at, public_ref);
CREATE INDEX IF NOT EXISTS lm_score_outcomes_winner_idx
  ON public.lm_score_outcomes (uid, organ, entity_key, outcome_kind, recorded_at DESC, revision_key DESC, public_ref DESC);

ALTER TABLE public.lm_score_outcomes ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_score_outcomes' AND policyname = 'lm_score_outcomes_service_select') THEN
    CREATE POLICY lm_score_outcomes_service_select ON public.lm_score_outcomes FOR SELECT TO service_role USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_score_outcomes' AND policyname = 'lm_score_outcomes_service_insert') THEN
    CREATE POLICY lm_score_outcomes_service_insert ON public.lm_score_outcomes FOR INSERT TO service_role WITH CHECK (true);
  END IF;
END $$;

REVOKE ALL ON TABLE public.lm_score_outcomes FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_score_outcomes TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_score_outcomes FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_score_outcomes_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_score_outcome_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_score_outcomes is append-only' USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS lm_score_outcomes_append_only ON public.lm_score_outcomes;
CREATE TRIGGER lm_score_outcomes_append_only
BEFORE UPDATE OR DELETE ON public.lm_score_outcomes
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_score_outcome_mutation();

REVOKE ALL ON FUNCTION public.reject_lm_score_outcome_mutation() FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.lm_append_score_outcome(p_outcome jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  candidate public.lm_score_outcomes%ROWTYPE;
  existing public.lm_score_outcomes%ROWTYPE;
  parsed_revision uuid;
  parsed_occurred timestamptz;
  parsed_resolved timestamptz;
  parsed_amount numeric;
  parsed_components jsonb;
BEGIN
  IF p_outcome IS NULL OR jsonb_typeof(p_outcome) <> 'object' THEN
    RAISE EXCEPTION 'invalid_score_outcome' USING ERRCODE = '22023';
  END IF;

  parsed_revision := (p_outcome->>'revision_key')::uuid;
  IF parsed_revision = '00000000-0000-0000-0000-000000000000'::uuid THEN
    RAISE EXCEPTION 'invalid_revision_key' USING ERRCODE = '22023';
  END IF;
  parsed_occurred := (p_outcome->>'occurred_at')::timestamptz;
  parsed_resolved := CASE WHEN p_outcome->>'resolved_at' IS NULL THEN NULL ELSE (p_outcome->>'resolved_at')::timestamptz END;
  parsed_amount := CASE WHEN p_outcome->>'amount_minor' IS NULL THEN NULL ELSE (p_outcome->>'amount_minor')::numeric END;
  IF parsed_amount IS NOT NULL AND (
    parsed_amount <> trunc(parsed_amount)
    OR parsed_amount < 0
    OR parsed_amount > 9007199254740991
  ) THEN
    RAISE EXCEPTION 'invalid_amount_minor' USING ERRCODE = '22023';
  END IF;
  parsed_components := COALESCE(p_outcome->'components', '{}'::jsonb);

  INSERT INTO public.lm_score_outcomes (
    uid, organ, entity_key, outcome_kind, outcome_status, revision_key,
    occurred_at, resolved_at, amount_minor, currency, components
  ) VALUES (
    p_outcome->>'uid', p_outcome->>'organ', p_outcome->>'entity_key', p_outcome->>'outcome_kind', p_outcome->>'outcome_status', parsed_revision,
    parsed_occurred, parsed_resolved, parsed_amount, p_outcome->>'currency', parsed_components
  )
  ON CONFLICT (uid, organ, entity_key, outcome_kind, revision_key) DO NOTHING
  RETURNING * INTO candidate;

  IF candidate.id IS NOT NULL THEN
    RETURN to_jsonb(candidate) - 'id';
  END IF;

  SELECT * INTO existing
  FROM public.lm_score_outcomes
  WHERE uid = p_outcome->>'uid'
    AND organ = p_outcome->>'organ'
    AND entity_key = p_outcome->>'entity_key'
    AND outcome_kind = p_outcome->>'outcome_kind'
    AND revision_key = parsed_revision;

  IF existing.id IS NOT NULL
    AND existing.outcome_status IS NOT DISTINCT FROM p_outcome->>'outcome_status'
    AND existing.occurred_at IS NOT DISTINCT FROM parsed_occurred
    AND existing.resolved_at IS NOT DISTINCT FROM parsed_resolved
    AND existing.amount_minor IS NOT DISTINCT FROM parsed_amount
    AND existing.currency IS NOT DISTINCT FROM p_outcome->>'currency'
    AND existing.components IS NOT DISTINCT FROM parsed_components THEN
    RETURN to_jsonb(existing) - 'id';
  END IF;

  RAISE EXCEPTION 'revision_key_conflict' USING ERRCODE = '23505';
END;
$$;

REVOKE ALL ON FUNCTION public.lm_append_score_outcome(jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_append_score_outcome(jsonb) TO service_role;

CREATE OR REPLACE FUNCTION public.lm_panel_score_outcome_snapshot(p_uid text, p_periods jsonb)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
WITH requested(organ, start_at, end_at) AS (
  VALUES
    ('daily', (p_periods->'daily'->>'start_at')::timestamptz, (p_periods->'daily'->>'end_at')::timestamptz),
    ('physical', (p_periods->'physical'->>'start_at')::timestamptz, (p_periods->'physical'->>'end_at')::timestamptz),
    ('mental', (p_periods->'mental'->>'start_at')::timestamptz, (p_periods->'mental'->>'end_at')::timestamptz),
    ('financial', (p_periods->'financial'->>'start_at')::timestamptz, (p_periods->'financial'->>'end_at')::timestamptz)
),
bounded AS MATERIALIZED (
  SELECT
    outcome.public_ref, outcome.uid, outcome.organ, outcome.entity_key,
    outcome.outcome_kind, outcome.outcome_status, outcome.revision_key,
    outcome.occurred_at, outcome.resolved_at, outcome.recorded_at,
    outcome.amount_minor, outcome.currency, outcome.components
  FROM public.lm_score_outcomes AS outcome
  JOIN requested ON requested.organ = outcome.organ
  WHERE outcome.uid = p_uid
    AND outcome.occurred_at >= requested.start_at
    AND outcome.occurred_at < requested.end_at
  ORDER BY outcome.organ, outcome.recorded_at, outcome.revision_key, outcome.public_ref
  LIMIT 20001
),
summary AS (
  SELECT count(*) AS row_count FROM bounded
)
SELECT CASE WHEN summary.row_count > 20000 THEN
  jsonb_build_object('overflow', true, 'rows_by_organ', '{}'::jsonb)
ELSE
  jsonb_build_object(
    'overflow', false,
    'rows_by_organ', jsonb_build_object(
      'daily', COALESCE(jsonb_agg(to_jsonb(bounded) ORDER BY bounded.recorded_at, bounded.revision_key, bounded.public_ref) FILTER (WHERE bounded.organ = 'daily'), '[]'::jsonb),
      'physical', COALESCE(jsonb_agg(to_jsonb(bounded) ORDER BY bounded.recorded_at, bounded.revision_key, bounded.public_ref) FILTER (WHERE bounded.organ = 'physical'), '[]'::jsonb),
      'mental', COALESCE(jsonb_agg(to_jsonb(bounded) ORDER BY bounded.recorded_at, bounded.revision_key, bounded.public_ref) FILTER (WHERE bounded.organ = 'mental'), '[]'::jsonb),
      'financial', COALESCE(jsonb_agg(to_jsonb(bounded) ORDER BY bounded.recorded_at, bounded.revision_key, bounded.public_ref) FILTER (WHERE bounded.organ = 'financial'), '[]'::jsonb)
    )
  )
END
FROM summary
LEFT JOIN bounded ON true
GROUP BY summary.row_count;
$$;

REVOKE ALL ON FUNCTION public.lm_panel_score_outcome_snapshot(text, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_panel_score_outcome_snapshot(text, jsonb) TO service_role;
