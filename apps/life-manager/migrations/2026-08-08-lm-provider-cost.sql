-- Provider cost guard shared schema.  This migration is additive and safe to
-- apply after the older lm_api_cost/lm_route_cache migrations.

CREATE TABLE IF NOT EXISTS public.lm_geocode_cache (
  address_key  text PRIMARY KEY CHECK (char_length(address_key) > 0),
  lat          double precision NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lng          double precision NOT NULL CHECK (lng BETWEEN -180 AND 180),
  provider     text NOT NULL,
  resolved_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_geocode_cache_resolved_at_idx
  ON public.lm_geocode_cache (resolved_at);

ALTER TABLE public.lm_geocode_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_geocode_cache FORCE ROW LEVEL SECURITY;

-- Route cache v2: the previous unique identity omitted the event anchor,
-- timezone, direction, and mode.  Keep old rows readable, but make new rows
-- use the complete opaque key and retain the structured provider result.
ALTER TABLE public.lm_route_cache
  ADD COLUMN IF NOT EXISTS cache_key text,
  ADD COLUMN IF NOT EXISTS route_result jsonb,
  ADD COLUMN IF NOT EXISTS event_anchor text,
  ADD COLUMN IF NOT EXISTS timezone text,
  ADD COLUMN IF NOT EXISTS direction text,
  ADD COLUMN IF NOT EXISTS route_mode text;

ALTER TABLE public.lm_route_cache
  DROP CONSTRAINT IF EXISTS lm_route_cache_uid_from_geo_to_geo_time_bucket_key;

CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_cache_key_idx
  ON public.lm_route_cache (cache_key)
  WHERE cache_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS lm_route_cache_context_idx
  ON public.lm_route_cache (uid, event_anchor, timezone, direction, route_mode);

-- Extend the old ledger without rewriting existing rows.  Actual billing is
-- deliberately nullable: unavailable provider billing is represented by the
-- enum value `unknown`, never by a fabricated zero.
ALTER TABLE public.lm_api_cost
  ADD COLUMN IF NOT EXISTS provider text,
  ADD COLUMN IF NOT EXISTS sku text,
  ADD COLUMN IF NOT EXISTS operation text,
  ADD COLUMN IF NOT EXISTS request_id text,
  ADD COLUMN IF NOT EXISTS pricing_version text,
  ADD COLUMN IF NOT EXISTS estimated_usd numeric,
  ADD COLUMN IF NOT EXISTS actual_billed_usd numeric,
  ADD COLUMN IF NOT EXISTS actual_status text,
  ADD COLUMN IF NOT EXISTS failed_at timestamptz,
  ADD COLUMN IF NOT EXISTS failure_reason text;

UPDATE public.lm_api_cost
SET estimated_usd = est_usd
WHERE estimated_usd IS NULL AND est_usd IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_api_cost_uid_ts_idx
  ON public.lm_api_cost (uid, ts);
CREATE INDEX IF NOT EXISTS lm_api_cost_provider_ts_idx
  ON public.lm_api_cost (provider, ts);
