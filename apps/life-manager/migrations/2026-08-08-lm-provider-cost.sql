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
