-- Extend event coverage snapshots from the historical 21-day window to 28 days.
-- This migration is additive: immutable rows, the current view, RLS, and every
-- existing snapshot remain untouched. NOT VALID preserves historical 21-day rows
-- while enforcing the new contract for every new or changed row.

DO $$
DECLARE
  old_constraint record;
  definition text;
BEGIN
  IF to_regclass('public.lm_event_coverage_snapshots') IS NULL THEN
    RETURN;
  END IF;

  -- Older migrations used unnamed CHECK constraints. Discover them by their
  -- deparsed definitions instead of relying on generated constraint suffixes.
  FOR old_constraint IN
    SELECT c.conname, pg_get_constraintdef(c.oid) AS definition
      FROM pg_constraint AS c
      JOIN pg_class AS r ON r.oid = c.conrelid
      JOIN pg_namespace AS n ON n.oid = r.relnamespace
     WHERE n.nspname = 'public'
       AND r.relname = 'lm_event_coverage_snapshots'
       AND c.contype = 'c'
  LOOP
    definition := lower(old_constraint.definition);
    IF definition ~ 'horizon_days[[:space:]]*=[[:space:]]*21'
       OR definition ~ 'jsonb_array_length[[:space:]]*\([[:space:]]*days[[:space:]]*\)[[:space:]]*=[[:space:]]*21'
       OR definition ~ 'window_end_date[[:space:]]*=[[:space:]]*\(?[[:space:]]*window_start_date[[:space:]]*\+[[:space:]]*20[[:space:]]*\)?'
       OR definition ~ '(open_count|covered_existing_count|covered_new_count|unavailable_count)[[:space:]]+between[[:space:]]+0[[:space:]]+and[[:space:]]+21'
       OR definition ~ 'open_count.*>=.*0.*open_count.*<=.*21'
       OR definition ~ 'covered_existing_count.*>=.*0.*covered_existing_count.*<=.*21'
       OR definition ~ 'covered_new_count.*>=.*0.*covered_new_count.*<=.*21'
       OR definition ~ 'unavailable_count.*>=.*0.*unavailable_count.*<=.*21'
       OR definition ~ 'open_count.*covered_existing_count.*covered_new_count.*unavailable_count.*=[[:space:]]*21'
    THEN
      EXECUTE format(
        'ALTER TABLE public.lm_event_coverage_snapshots DROP CONSTRAINT %I',
        old_constraint.conname
      );
    END IF;
END LOOP;

  -- Keep the whole migration a no-op when the optional coverage table has not
  -- been installed. Static ALTER statements after this DO block would still
  -- execute and fail even though the guard above returned.
  ALTER TABLE public.lm_event_coverage_snapshots
    DROP CONSTRAINT IF EXISTS lm_event_coverage_horizon_days_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_days_length_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_window_end_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_open_count_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_covered_existing_count_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_covered_new_count_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_unavailable_count_28_check,
    DROP CONSTRAINT IF EXISTS lm_event_coverage_counts_sum_28_check;

  ALTER TABLE public.lm_event_coverage_snapshots
    ADD CONSTRAINT lm_event_coverage_horizon_days_28_check
      CHECK (horizon_days = 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_days_length_28_check
      CHECK (jsonb_typeof(days) = 'array' AND jsonb_array_length(days) = 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_window_end_28_check
      CHECK (window_end_date = window_start_date + 27) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_open_count_28_check
      CHECK (open_count BETWEEN 0 AND 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_covered_existing_count_28_check
      CHECK (covered_existing_count BETWEEN 0 AND 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_covered_new_count_28_check
      CHECK (covered_new_count BETWEEN 0 AND 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_unavailable_count_28_check
      CHECK (unavailable_count BETWEEN 0 AND 28) NOT VALID,
    ADD CONSTRAINT lm_event_coverage_counts_sum_28_check
      CHECK (open_count + covered_existing_count + covered_new_count + unavailable_count = 28) NOT VALID;
END;
$$;
