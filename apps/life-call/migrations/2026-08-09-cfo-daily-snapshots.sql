-- CFO-1g: one immutable native-JPY Moneytree daily snapshot per owner/date.
CREATE TABLE IF NOT EXISTS public.lm_cfo_daily_snapshots (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  uid text NOT NULL REFERENCES public.lm_users(uid),
  reporting_date date NOT NULL,
  run_id uuid NOT NULL CHECK (run_id <> '00000000-0000-0000-0000-000000000000'::uuid),
  revision integer NOT NULL DEFAULT 1 CHECK (revision = 1),
  report_payload jsonb NOT NULL,
  source_bundle jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CONSTRAINT lm_cfo_daily_snapshots_owner_date_revision_unique UNIQUE (uid, reporting_date, revision),
  CONSTRAINT lm_cfo_daily_snapshots_owner_date_run_unique UNIQUE (uid, reporting_date, run_id),
  CONSTRAINT lm_cfo_daily_snapshots_report_shape CHECK ((
    jsonb_typeof(report_payload) = 'object'
    AND report_payload->>'reportingDate' = reporting_date::text
    AND report_payload->>'revision' = revision::text
    AND report_payload->>'currency' = 'JPY'
  ) IS TRUE),
  CONSTRAINT lm_cfo_daily_snapshots_source_shape CHECK ((
    jsonb_typeof(source_bundle) = 'object'
    AND jsonb_typeof(source_bundle->'source') = 'object'
    AND jsonb_typeof(source_bundle->'state') = 'object'
    AND source_bundle->'source'->>'sourceId' = 'moneytree_mufg'
    AND source_bundle->'state'->>'sourceId' = 'moneytree_mufg'
  ) IS TRUE)
);

ALTER TABLE public.lm_cfo_daily_snapshots ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_cfo_daily_snapshots' AND policyname = 'lm_cfo_daily_snapshots_service_select') THEN
    CREATE POLICY lm_cfo_daily_snapshots_service_select ON public.lm_cfo_daily_snapshots FOR SELECT TO service_role USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_cfo_daily_snapshots' AND policyname = 'lm_cfo_daily_snapshots_service_insert') THEN
    CREATE POLICY lm_cfo_daily_snapshots_service_insert ON public.lm_cfo_daily_snapshots FOR INSERT TO service_role WITH CHECK (true);
  END IF;
END $$;

REVOKE ALL ON TABLE public.lm_cfo_daily_snapshots FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_daily_snapshots TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_daily_snapshots FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_daily_snapshots_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_cfo_daily_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_cfo_daily_snapshots is append-only' USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS lm_cfo_daily_snapshots_append_only ON public.lm_cfo_daily_snapshots;
CREATE TRIGGER lm_cfo_daily_snapshots_append_only
BEFORE UPDATE OR DELETE ON public.lm_cfo_daily_snapshots
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_cfo_daily_snapshot_mutation();
REVOKE ALL ON FUNCTION public.reject_lm_cfo_daily_snapshot_mutation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reject_lm_cfo_daily_snapshot_mutation() TO service_role;

CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot(
  p_uid text, p_reporting_date date, p_run_id uuid, p_report_payload jsonb, p_source_bundle jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  candidate public.lm_cfo_daily_snapshots%ROWTYPE;
  existing public.lm_cfo_daily_snapshots%ROWTYPE;
BEGIN
  IF p_reporting_date IS NULL OR p_run_id IS NULL OR p_run_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
    RAISE EXCEPTION 'invalid_snapshot_identity' USING ERRCODE = '22023';
  END IF;
  IF p_report_payload IS NULL OR jsonb_typeof(p_report_payload) <> 'object' THEN
    RAISE EXCEPTION 'invalid_report_payload' USING ERRCODE = '22023';
  END IF;
  IF p_source_bundle IS NULL OR jsonb_typeof(p_source_bundle) <> 'object' THEN
    RAISE EXCEPTION 'invalid_source_bundle' USING ERRCODE = '22023';
  END IF;
  IF p_report_payload->>'reportingDate' IS DISTINCT FROM p_reporting_date::text
    OR p_report_payload->>'revision' IS DISTINCT FROM '1'
    OR p_report_payload->>'currency' IS DISTINCT FROM 'JPY' THEN
    RAISE EXCEPTION 'invalid_report_contract' USING ERRCODE = '22023';
  END IF;
  IF p_source_bundle->'source'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg'
    OR p_source_bundle->'state'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg' THEN
    RAISE EXCEPTION 'invalid_source_contract' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.lm_cfo_daily_snapshots
    (uid, reporting_date, run_id, revision, report_payload, source_bundle)
  VALUES (p_uid, p_reporting_date, p_run_id, 1, p_report_payload, p_source_bundle)
  ON CONFLICT DO NOTHING
  RETURNING * INTO candidate;

  IF candidate.id IS NOT NULL THEN
    RETURN to_jsonb(candidate) - 'id' - 'uid' - 'report_payload' - 'source_bundle';
  END IF;

  SELECT * INTO existing
  FROM public.lm_cfo_daily_snapshots
  WHERE uid = p_uid AND reporting_date = p_reporting_date AND run_id = p_run_id;

  IF existing.id IS NOT NULL THEN
    IF existing.report_payload IS NOT DISTINCT FROM p_report_payload
      AND existing.source_bundle IS NOT DISTINCT FROM p_source_bundle THEN
      RETURN to_jsonb(existing) - 'id' - 'uid' - 'report_payload' - 'source_bundle';
    END IF;
    RAISE EXCEPTION 'run_id_conflict' USING ERRCODE = '23505';
  END IF;

  RAISE EXCEPTION 'reporting_date_conflict' USING ERRCODE = '23505';
END;
$$;

REVOKE ALL ON FUNCTION public.lm_append_cfo_daily_snapshot(text, date, uuid, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_append_cfo_daily_snapshot(text, date, uuid, jsonb, jsonb) TO service_role;
