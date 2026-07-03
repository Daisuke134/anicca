-- C3 (VCSDD life-manager-cost-connect-reliability): lm_route_cache — route-RESULT cache so the 60s
-- scheduler tick does NOT recompute a route it already has. DISTINCT from lm_travel_log (a dedup/claim
-- ledger). Keyed by (uid, from_geo, to_geo, time_bucket): a moved event lands in a new coarse bucket →
-- recompute; a row past its ttl recomputes. Provider = 'transit' (free JP) or 'google'. Re-runnable.
-- calendar_provider stays free-text (no CHECK), so 'pipedream_gcal' needs no migration — the scheduler
-- selector (calendarProviderFilter) already includes it.

CREATE TABLE IF NOT EXISTS public.lm_route_cache (
  uid          text        NOT NULL,
  from_geo     text        NOT NULL,            -- "lat,lon" rounded to ~4dp (~11m) — the cache key coord
  to_geo       text        NOT NULL,
  time_bucket  bigint      NOT NULL,            -- coarse 10-min departure bucket (floor(epochMs/600000))
  provider     text        NOT NULL,            -- 'transit' | 'google'
  duration_secs integer    NOT NULL,
  geometry     jsonb,                           -- optional legs/route geometry for the guidance line
  computed_at  timestamptz NOT NULL DEFAULT now(),
  ttl_secs     integer     NOT NULL DEFAULT 600,
  UNIQUE (uid, from_geo, to_geo, time_bucket)   -- one cached route per (user, from, to, bucket); upsert on conflict
);

-- Prune helper (a cron may DELETE expired rows; not required for correctness — reads check ttl).
CREATE INDEX IF NOT EXISTS lm_route_cache_computed_at_idx ON public.lm_route_cache (computed_at);

-- SECURITY: enable RLS with NO policies (matches every other lm_* table). Contains uid + home/dest geo
-- = sensitive location data; the public anon key must NOT reach it. life-call uses the service_role key,
-- which BYPASSES RLS, so the backend keeps full access while the internet-exposed anon key is denied.
ALTER TABLE public.lm_route_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_route_cache FORCE ROW LEVEL SECURITY;
