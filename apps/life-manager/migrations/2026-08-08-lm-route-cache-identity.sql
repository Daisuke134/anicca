-- lm_route_cache identity follow-up.
--
-- This migration is intentionally additive and must run after either order of
-- 2026-08-08-lm-provider-cost.sql and 2026-08-08-lm-mobile-v1.sql.  Existing
-- rows are retained. New writers use the tenant-scoped identity
-- (uid, cache_key) and the canonical structured payload route_result.

CREATE TABLE IF NOT EXISTS public.lm_route_cache (
  uid text,
  from_geo text,
  to_geo text,
  time_bucket bigint,
  provider text,
  duration_secs integer,
  geometry jsonb,
  computed_at timestamptz,
  ttl_secs integer,
  cache_key text,
  route jsonb,
  route_result jsonb,
  legacy_cache_key text,
  event_anchor text,
  timezone text,
  direction text,
  route_mode text
);

ALTER TABLE public.lm_route_cache
  ADD COLUMN IF NOT EXISTS cache_key text,
  ADD COLUMN IF NOT EXISTS route jsonb,
  ADD COLUMN IF NOT EXISTS route_result jsonb,
  ADD COLUMN IF NOT EXISTS legacy_cache_key text,
  ADD COLUMN IF NOT EXISTS event_anchor text,
  ADD COLUMN IF NOT EXISTS timezone text,
  ADD COLUMN IF NOT EXISTS direction text,
  ADD COLUMN IF NOT EXISTS route_mode text;

-- The mobile migration originally called the structured payload `route`.
-- Backfill only the canonical column; keep `route` untouched for rollback and
-- old readers. This is deliberately not a DELETE/TRUNCATE migration.
UPDATE public.lm_route_cache
   SET route_result = route
 WHERE route_result IS NULL
   AND route IS NOT NULL;

-- The old writers send an unscoped digest. The old mobile writer uses
-- `ON CONFLICT (uid,cache_key)` and route-only payloads; the old provider
-- writer uses `ON CONFLICT (cache_key)` and a route_result payload. The global
-- arbiter must remain available for the old provider's conflict inference, but
-- it must never see the same raw digest for two tenants. Namespace both old
-- payloads before either unique index sees them, while retaining the raw key
-- for migration-period readers and diagnostics. Canonical v2 writers are not
-- rewritten by this trigger.
CREATE OR REPLACE FUNCTION public.lm_route_cache_namespace_legacy_mobile()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.uid IS NOT NULL
     AND NEW.cache_key IS NOT NULL
     AND NEW.cache_key NOT LIKE 'v2:%'
     AND NEW.cache_key NOT LIKE 'legacy-provider-v1:%'
     AND NEW.cache_key NOT LIKE 'legacy-mobile-v1:%'
     AND (NEW.route_result IS NOT NULL OR NEW.route IS NOT NULL) THEN
    NEW.legacy_cache_key := NEW.cache_key;
    IF NEW.route_result IS NULL THEN
      NEW.cache_key := 'legacy-mobile-v1:' || md5(NEW.uid || chr(0) || NEW.cache_key);
    ELSE
      NEW.cache_key := 'legacy-provider-v1:' || md5(NEW.uid || chr(0) || NEW.cache_key);
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_route_cache_namespace_legacy_mobile ON public.lm_route_cache;
CREATE TRIGGER lm_route_cache_namespace_legacy_mobile
BEFORE INSERT OR UPDATE OF uid, cache_key, route, route_result
ON public.lm_route_cache
FOR EACH ROW
EXECUTE FUNCTION public.lm_route_cache_namespace_legacy_mobile();

-- Remove only the pre-cache-key identity. The old provider and mobile conflict
-- targets must remain during the rolling window: old provider instances still
-- send `on_conflict=cache_key`, while old mobile instances still send
-- `on_conflict=uid,cache_key` and a route-only payload. The old rows remain in
-- place, including rows whose cache_key is NULL.
ALTER TABLE public.lm_route_cache
  DROP CONSTRAINT IF EXISTS lm_route_cache_uid_from_geo_to_geo_time_bucket_key;
DROP INDEX IF EXISTS public.lm_route_cache_uid_from_geo_to_geo_time_bucket_key;

-- Compatibility target for the old provider writer. Keep this index until all
-- old provider instances have drained; a later cleanup migration may remove it
-- after the canonical tenant-scoped writer is the only writer.
CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_cache_key_idx
  ON public.lm_route_cache (cache_key);

-- Compatibility target for the old mobile writer. Keep the named index as well
-- as the canonical index below so either migration order remains safe and both
-- conflict clauses can be inferred during a rolling deployment.
CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_mobile_key_unique
  ON public.lm_route_cache (uid, cache_key);

-- Non-partial means `on_conflict=uid,cache_key` is an exact inference target.
-- NULL cache_key values on retained legacy rows are allowed by PostgreSQL's
-- normal unique-index semantics; all new writers send a non-null key.
CREATE UNIQUE INDEX IF NOT EXISTS lm_route_cache_uid_cache_key_unique
  ON public.lm_route_cache (uid, cache_key);

CREATE INDEX IF NOT EXISTS lm_route_cache_uid_computed_at_idx
  ON public.lm_route_cache (uid, computed_at);

-- Staged validation: validate canonical rows without a rolling column rewrite,
-- which would lock or reject retained legacy rows during deployment. A null
-- cache_key marks a legacy row; once a key is present every durable field and
-- either the canonical structured result or the legacy route payload must be
-- present. The latter keeps route-only old mobile writers valid until cleanup.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conrelid = 'public.lm_route_cache'::regclass
       AND conname = 'lm_route_cache_canonical_fields_check'
  ) THEN
    ALTER TABLE public.lm_route_cache
      ADD CONSTRAINT lm_route_cache_canonical_fields_check
      CHECK (
        cache_key IS NULL
        OR (
          uid IS NOT NULL
          AND from_geo IS NOT NULL
          AND to_geo IS NOT NULL
          AND time_bucket IS NOT NULL
          AND provider IS NOT NULL
          AND duration_secs IS NOT NULL
          AND computed_at IS NOT NULL
          AND ttl_secs IS NOT NULL
          AND (route_result IS NOT NULL OR route IS NOT NULL)
        )
      ) NOT VALID;
  END IF;
END $$;

ALTER TABLE public.lm_route_cache
  VALIDATE CONSTRAINT lm_route_cache_canonical_fields_check;
