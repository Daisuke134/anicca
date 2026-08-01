CREATE TABLE IF NOT EXISTS public.lm_event_coverage_snapshots (
  coverage_snapshot_id text PRIMARY KEY CHECK (coverage_snapshot_id ~ '^event-coverage:[0-9a-f]{64}$'),
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  timezone text NOT NULL CHECK (char_length(timezone) BETWEEN 1 AND 100),
  calculated_at timestamptz NOT NULL,
  window_start_date date NOT NULL,
  window_end_date date NOT NULL,
  horizon_days integer NOT NULL CHECK (horizon_days = 21),
  days jsonb NOT NULL CHECK (jsonb_typeof(days) = 'array' AND jsonb_array_length(days) = 21),
  open_count integer NOT NULL CHECK (open_count BETWEEN 0 AND 21),
  covered_existing_count integer NOT NULL CHECK (covered_existing_count BETWEEN 0 AND 21),
  covered_new_count integer NOT NULL CHECK (covered_new_count BETWEEN 0 AND 21),
  unavailable_count integer NOT NULL CHECK (unavailable_count BETWEEN 0 AND 21),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (window_end_date = window_start_date + 20),
  CHECK (open_count + covered_existing_count + covered_new_count + unavailable_count = 21)
);

CREATE INDEX IF NOT EXISTS lm_event_coverage_tenant_latest_idx
  ON public.lm_event_coverage_snapshots (tenant_id, calculated_at DESC, created_at DESC);

CREATE OR REPLACE VIEW public.lm_event_coverage_current AS
SELECT DISTINCT ON (tenant_id) *
FROM public.lm_event_coverage_snapshots
ORDER BY tenant_id, calculated_at DESC, created_at DESC, coverage_snapshot_id DESC;

CREATE OR REPLACE FUNCTION public.lm_event_coverage_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'event coverage snapshots are immutable';
END;
$$;

DROP TRIGGER IF EXISTS lm_event_coverage_immutable ON public.lm_event_coverage_snapshots;
CREATE TRIGGER lm_event_coverage_immutable
BEFORE UPDATE OR DELETE ON public.lm_event_coverage_snapshots
FOR EACH ROW EXECUTE FUNCTION public.lm_event_coverage_immutable();

ALTER TABLE public.lm_event_coverage_snapshots ENABLE ROW LEVEL SECURITY;
