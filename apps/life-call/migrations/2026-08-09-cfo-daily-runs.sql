-- CFO-1g2: one immutable owner-local daily run per reporting date.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM (SELECT DISTINCT uid FROM public.lm_cfo_daily_snapshots) AS snapshot_owner
    LEFT JOIN public.lm_panel_preferences AS preference ON preference.uid = snapshot_owner.uid
    WHERE preference.uid IS NULL OR preference.call_time_zone IS NULL OR NOT EXISTS (
      SELECT 1 FROM pg_timezone_names AS valid_zone WHERE valid_zone.name = preference.call_time_zone
    )
  ) THEN
    RAISE EXCEPTION 'cfo_daily_run_migration_requires_valid_timezone_preference' USING ERRCODE = '23514';
  END IF;
  IF EXISTS (
    SELECT uid, reporting_date FROM public.lm_cfo_daily_snapshots
    GROUP BY uid, reporting_date HAVING count(DISTINCT run_id) > 1
  ) THEN
    RAISE EXCEPTION 'cfo_daily_run_migration_conflicting_snapshot_runs' USING ERRCODE = '23514';
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.lm_cfo_daily_runs (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE CHECK (public_ref <> '00000000-0000-0000-0000-000000000000'::uuid),
  uid text NOT NULL REFERENCES public.lm_users(uid),
  reporting_date date NOT NULL,
  run_id uuid NOT NULL DEFAULT gen_random_uuid() CHECK (run_id <> '00000000-0000-0000-0000-000000000000'::uuid),
  time_zone text NOT NULL,
  time_zone_source text NOT NULL CHECK (time_zone_source IN ('migration_preference', 'owner_preference')),
  created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
  CONSTRAINT lm_cfo_daily_runs_owner_date_unique UNIQUE (uid, reporting_date),
  CONSTRAINT lm_cfo_daily_runs_owner_date_run_unique UNIQUE (uid, reporting_date, run_id)
);

INSERT INTO public.lm_cfo_daily_runs (uid, reporting_date, run_id, time_zone, time_zone_source)
SELECT DISTINCT snapshot.uid, snapshot.reporting_date, snapshot.run_id, preference.call_time_zone, 'migration_preference'
FROM public.lm_cfo_daily_snapshots AS snapshot
JOIN public.lm_panel_preferences AS preference ON preference.uid = snapshot.uid
JOIN pg_timezone_names AS valid_zone ON valid_zone.name = preference.call_time_zone;

ALTER TABLE public.lm_cfo_daily_snapshots
  ADD CONSTRAINT lm_cfo_daily_snapshots_daily_run_fk
  FOREIGN KEY (uid, reporting_date, run_id) REFERENCES public.lm_cfo_daily_runs (uid, reporting_date, run_id);

ALTER TABLE public.lm_cfo_daily_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY lm_cfo_daily_runs_service_select ON public.lm_cfo_daily_runs FOR SELECT TO service_role USING (true);
CREATE POLICY lm_cfo_daily_runs_service_insert ON public.lm_cfo_daily_runs FOR INSERT TO service_role WITH CHECK (true);
REVOKE ALL ON TABLE public.lm_cfo_daily_runs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_daily_runs TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_daily_runs FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_daily_runs_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_cfo_daily_run_mutation()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_cfo_daily_runs is append-only' USING ERRCODE = '55000';
END;
$$;
DROP TRIGGER IF EXISTS lm_cfo_daily_runs_append_only ON public.lm_cfo_daily_runs;
CREATE TRIGGER lm_cfo_daily_runs_append_only BEFORE UPDATE OR DELETE ON public.lm_cfo_daily_runs
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_cfo_daily_run_mutation();
REVOKE ALL ON FUNCTION public.reject_lm_cfo_daily_run_mutation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reject_lm_cfo_daily_run_mutation() TO service_role;

CREATE OR REPLACE FUNCTION public.lm_cfo_owner_local_date(p_time_zone text, p_instant timestamptz)
RETURNS date LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp
AS $$ SELECT (p_instant AT TIME ZONE p_time_zone)::date $$;
REVOKE ALL ON FUNCTION public.lm_cfo_owner_local_date(text, timestamptz) FROM PUBLIC, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.lm_claim_cfo_daily_run(p_uid text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
DECLARE
  owner_time_zone text;
  owner_reporting_date date;
  claimed public.lm_cfo_daily_runs%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR p_uid = '' THEN
    RAISE EXCEPTION 'cfo_daily_run_timezone_unavailable' USING ERRCODE = '22023';
  END IF;
  SELECT preference.call_time_zone INTO owner_time_zone
  FROM public.lm_panel_preferences AS preference
  WHERE preference.uid = p_uid AND EXISTS (
    SELECT 1 FROM pg_timezone_names AS valid_zone WHERE valid_zone.name = preference.call_time_zone
  )
  FOR UPDATE OF preference;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'cfo_daily_run_timezone_unavailable' USING ERRCODE = '22023';
  END IF;
  owner_reporting_date := (statement_timestamp() AT TIME ZONE owner_time_zone)::date;
  INSERT INTO public.lm_cfo_daily_runs (uid, reporting_date, time_zone, time_zone_source)
  VALUES (p_uid, owner_reporting_date, owner_time_zone, 'owner_preference')
  ON CONFLICT DO NOTHING RETURNING * INTO claimed;
  IF claimed.id IS NULL THEN
    SELECT * INTO claimed FROM public.lm_cfo_daily_runs
    WHERE uid = p_uid AND reporting_date = owner_reporting_date;
  END IF;
  IF claimed.id IS NULL THEN
    RAISE EXCEPTION 'cfo_daily_run_unavailable' USING ERRCODE = '40001';
  END IF;
  RETURN jsonb_build_object(
    'public_ref', claimed.public_ref,
    'reporting_date', claimed.reporting_date,
    'run_id', claimed.run_id,
    'time_zone', claimed.time_zone,
    'created_at', claimed.created_at
  );
END;
$$;
REVOKE ALL ON FUNCTION public.lm_claim_cfo_daily_run(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_claim_cfo_daily_run(text) TO service_role;
