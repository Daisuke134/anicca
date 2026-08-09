-- CFO-1g3 Task 4: forward-only append-only snapshot corrections.
-- Existing rows remain untouched; later facts are appended as new revisions.
ALTER TABLE public.lm_cfo_daily_snapshots
  ADD COLUMN IF NOT EXISTS supersedes_revision integer;

ALTER TABLE public.lm_cfo_daily_snapshots
  DROP CONSTRAINT IF EXISTS lm_cfo_daily_snapshots_revision_check,
  DROP CONSTRAINT IF EXISTS lm_cfo_daily_snapshots_owner_date_run_unique;

ALTER TABLE public.lm_cfo_daily_snapshots
  ADD CONSTRAINT lm_cfo_daily_snapshots_revision_positive CHECK (revision > 0),
  ADD CONSTRAINT lm_cfo_daily_snapshots_predecessor_contract CHECK (
    (revision = 1 AND supersedes_revision IS NULL)
    OR (revision > 1 AND supersedes_revision = revision - 1)
  ),
  ADD CONSTRAINT lm_cfo_daily_snapshots_owner_date_run_revision_unique
    UNIQUE (uid, reporting_date, run_id, revision),
  ADD CONSTRAINT lm_cfo_daily_snapshots_predecessor_fk
    FOREIGN KEY (uid, reporting_date, run_id, supersedes_revision)
    REFERENCES public.lm_cfo_daily_snapshots (uid, reporting_date, run_id, revision);

ALTER TABLE public.lm_cfo_daily_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_cfo_daily_snapshots FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_daily_snapshots TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_daily_snapshots FROM service_role;

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
  IF p_uid IS NULL OR p_uid = '' OR p_reporting_date IS NULL OR p_run_id IS NULL
    OR p_run_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
    RAISE EXCEPTION 'invalid_snapshot_identity' USING ERRCODE = '22023';
  END IF;
  IF p_report_payload IS NULL OR jsonb_typeof(p_report_payload) <> 'object'
    OR jsonb_typeof(p_report_payload->'revision') <> 'number'
    OR p_report_payload->'revision' IS DISTINCT FROM to_jsonb(1) THEN
    RAISE EXCEPTION 'invalid_report_payload' USING ERRCODE = '22023';
  END IF;
  IF p_source_bundle IS NULL OR jsonb_typeof(p_source_bundle) <> 'object' THEN
    RAISE EXCEPTION 'invalid_source_bundle' USING ERRCODE = '22023';
  END IF;
  IF p_report_payload->>'reportingDate' IS DISTINCT FROM p_reporting_date::text
    OR p_report_payload->>'currency' IS DISTINCT FROM 'JPY' THEN
    RAISE EXCEPTION 'invalid_report_contract' USING ERRCODE = '22023';
  END IF;
  IF p_source_bundle->'source'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg'
    OR p_source_bundle->'state'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg' THEN
    RAISE EXCEPTION 'invalid_source_contract' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.lm_cfo_daily_snapshots
    (uid, reporting_date, run_id, revision, supersedes_revision, report_payload, source_bundle)
  VALUES (p_uid, p_reporting_date, p_run_id, 1, NULL, p_report_payload, p_source_bundle)
  ON CONFLICT DO NOTHING
  RETURNING * INTO candidate;

  IF candidate.id IS NULL THEN
    SELECT * INTO existing
    FROM public.lm_cfo_daily_snapshots
    WHERE uid = p_uid AND reporting_date = p_reporting_date AND run_id = p_run_id AND revision = 1;
    IF existing.id IS NULL THEN
      RAISE EXCEPTION 'reporting_date_conflict' USING ERRCODE = '23505';
    END IF;
    IF existing.report_payload IS DISTINCT FROM p_report_payload
      OR existing.source_bundle IS DISTINCT FROM p_source_bundle THEN
      RAISE EXCEPTION 'run_id_conflict' USING ERRCODE = '23505';
    END IF;
    candidate := existing;
  END IF;

  RETURN jsonb_build_object(
    'public_ref', candidate.public_ref,
    'reporting_date', candidate.reporting_date,
    'run_id', candidate.run_id,
    'revision', candidate.revision,
    'supersedes_revision', candidate.supersedes_revision,
    'created_at', candidate.created_at
  );
END;
$$;
REVOKE ALL ON FUNCTION public.lm_append_cfo_daily_snapshot(text, date, uuid, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_append_cfo_daily_snapshot(text, date, uuid, jsonb, jsonb) TO service_role;

CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot_revision(
  p_uid text, p_reporting_date date, p_run_id uuid, p_revision integer,
  p_supersedes_revision integer, p_report_payload jsonb, p_source_bundle jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  predecessor public.lm_cfo_daily_snapshots%ROWTYPE;
  candidate public.lm_cfo_daily_snapshots%ROWTYPE;
  existing public.lm_cfo_daily_snapshots%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR p_uid = '' OR p_reporting_date IS NULL OR p_run_id IS NULL
    OR p_run_id = '00000000-0000-0000-0000-000000000000'::uuid
    OR p_revision IS NULL OR p_revision <= 0
    OR p_supersedes_revision IS DISTINCT FROM p_revision - 1 THEN
    RAISE EXCEPTION 'invalid_snapshot_revision' USING ERRCODE = '22023';
  END IF;
  IF p_report_payload IS NULL OR jsonb_typeof(p_report_payload) <> 'object'
    OR jsonb_typeof(p_report_payload->'revision') <> 'number'
    OR p_report_payload->'revision' IS DISTINCT FROM to_jsonb(p_revision)
    OR p_report_payload->>'reportingDate' IS DISTINCT FROM p_reporting_date::text
    OR p_report_payload->>'currency' IS DISTINCT FROM 'JPY' THEN
    RAISE EXCEPTION 'invalid_report_contract' USING ERRCODE = '22023';
  END IF;
  IF p_source_bundle IS NULL OR jsonb_typeof(p_source_bundle) <> 'object'
    OR p_source_bundle->'source'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg'
    OR p_source_bundle->'state'->>'sourceId' IS DISTINCT FROM 'moneytree_mufg' THEN
    RAISE EXCEPTION 'invalid_source_contract' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO predecessor
  FROM public.lm_cfo_daily_snapshots
  WHERE uid = p_uid AND reporting_date = p_reporting_date AND run_id = p_run_id
    AND revision = p_supersedes_revision
  FOR UPDATE;
  IF predecessor.id IS NULL THEN
    RAISE EXCEPTION 'cfo_snapshot_predecessor_missing' USING ERRCODE = '23503';
  END IF;

  INSERT INTO public.lm_cfo_daily_snapshots
    (uid, reporting_date, run_id, revision, supersedes_revision, report_payload, source_bundle)
  VALUES (p_uid, p_reporting_date, p_run_id, p_revision, p_supersedes_revision, p_report_payload, p_source_bundle)
  ON CONFLICT DO NOTHING
  RETURNING * INTO candidate;

  IF candidate.id IS NULL THEN
    SELECT * INTO existing
    FROM public.lm_cfo_daily_snapshots
    WHERE uid = p_uid AND reporting_date = p_reporting_date AND run_id = p_run_id AND revision = p_revision;
    IF existing.id IS NULL
      OR existing.report_payload IS DISTINCT FROM p_report_payload
      OR existing.source_bundle IS DISTINCT FROM p_source_bundle
      OR existing.supersedes_revision IS DISTINCT FROM p_supersedes_revision THEN
      RAISE EXCEPTION 'cfo_snapshot_revision_conflict' USING ERRCODE = '23505';
    END IF;
    candidate := existing;
  END IF;

  RETURN jsonb_build_object(
    'public_ref', candidate.public_ref,
    'reporting_date', candidate.reporting_date,
    'run_id', candidate.run_id,
    'revision', candidate.revision,
    'supersedes_revision', candidate.supersedes_revision,
    'created_at', candidate.created_at
  );
END;
$$;
REVOKE ALL ON FUNCTION public.lm_append_cfo_daily_snapshot_revision(text, date, uuid, integer, integer, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_append_cfo_daily_snapshot_revision(text, date, uuid, integer, integer, jsonb, jsonb) TO service_role;
