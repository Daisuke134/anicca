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

-- Supabase's `on_conflict=cache_key` requires a non-partial unique index. A
-- regular unique index still permits multiple legacy NULL keys in PostgreSQL.
DROP INDEX IF EXISTS public.lm_route_cache_cache_key_idx;
CREATE UNIQUE INDEX lm_route_cache_cache_key_idx
  ON public.lm_route_cache (cache_key);
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
  ADD COLUMN IF NOT EXISTS cost_classification text,
  ADD COLUMN IF NOT EXISTS failed_at timestamptz,
  ADD COLUMN IF NOT EXISTS failure_reason text,
  ADD COLUMN IF NOT EXISTS metadata jsonb;

-- Normalize the first version of this gate (`measured|estimated|unknown` in
-- actual_status) before installing the stricter two-state status contract.
-- The old distinction is retained in the new classification column.
UPDATE public.lm_api_cost
SET cost_classification = CASE
  WHEN actual_status = 'measured' OR (actual_status = 'known' AND actual_billed_usd IS NOT NULL) THEN 'measured'
  WHEN actual_status = 'estimated' OR estimated_usd IS NOT NULL THEN 'estimated'
  ELSE 'unknown'
END
WHERE cost_classification IS NULL;

UPDATE public.lm_api_cost
SET actual_status = CASE
  WHEN actual_status = 'measured' OR actual_billed_usd IS NOT NULL THEN 'known'
  ELSE 'unknown'
END
WHERE actual_status IS NULL OR actual_status NOT IN ('known', 'unknown');

DO $$
BEGIN
  ALTER TABLE public.lm_api_cost DROP CONSTRAINT IF EXISTS lm_api_cost_actual_status_check;
  ALTER TABLE public.lm_api_cost
    ADD CONSTRAINT lm_api_cost_actual_status_check
    CHECK (actual_status IN ('known', 'unknown'));
  ALTER TABLE public.lm_api_cost DROP CONSTRAINT IF EXISTS lm_api_cost_cost_classification_check;
  ALTER TABLE public.lm_api_cost
    ADD CONSTRAINT lm_api_cost_cost_classification_check
    CHECK (cost_classification IN ('measured', 'estimated', 'fixed', 'unknown'));
END $$;

UPDATE public.lm_api_cost
SET estimated_usd = est_usd
WHERE estimated_usd IS NULL AND est_usd IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_api_cost_uid_ts_idx
  ON public.lm_api_cost (uid, ts);
CREATE INDEX IF NOT EXISTS lm_api_cost_provider_ts_idx
  ON public.lm_api_cost (provider, ts);
CREATE UNIQUE INDEX IF NOT EXISTS lm_api_cost_provider_request_idx
  ON public.lm_api_cost (provider, request_id)
  WHERE request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.lm_provider_cost_failures (
  id           bigint generated always as identity primary key,
  failed_at    timestamptz NOT NULL DEFAULT now(),
  uid          text,
  provider     text NOT NULL,
  sku          text NOT NULL,
  operation    text NOT NULL,
  request_id   text NOT NULL,
  quantity     numeric,
  unit         text,
  error        jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS lm_provider_cost_failures_failed_at_idx
  ON public.lm_provider_cost_failures (failed_at);
ALTER TABLE public.lm_provider_cost_failures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_provider_cost_failures FORCE ROW LEVEL SECURITY;

-- Atomic budget claims. The ledger remains the audit source of truth; claims
-- reserve projected spend before a paid provider request leaves the process.
CREATE TABLE IF NOT EXISTS public.lm_provider_budget_claims (
  uid            text NOT NULL,
  budget_day     date NOT NULL,
  provider       text NOT NULL,
  operation      text NOT NULL,
  request_id     text NOT NULL,
  projected_usd  numeric NOT NULL DEFAULT 0 CHECK (projected_usd >= 0),
  is_voice       boolean NOT NULL DEFAULT false,
  claimed_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, budget_day, request_id)
);
ALTER TABLE public.lm_provider_budget_claims
  ADD COLUMN IF NOT EXISTS is_voice boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS lm_provider_budget_claims_global_idx
  ON public.lm_provider_budget_claims (budget_day, provider, operation);
ALTER TABLE public.lm_provider_budget_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_provider_budget_claims FORCE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.lm_provider_voice_buckets (
  scope        text NOT NULL CHECK (scope IN ('user', 'global')),
  uid          text NOT NULL DEFAULT '',
  budget_day   date NOT NULL,
  settled_usd  numeric NOT NULL DEFAULT 0 CHECK (settled_usd >= 0),
  reserved_usd numeric NOT NULL DEFAULT 0 CHECK (reserved_usd >= 0),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (scope, uid, budget_day),
  CHECK ((scope = 'global' AND uid = '') OR (scope = 'user' AND uid <> ''))
);
CREATE INDEX IF NOT EXISTS lm_provider_voice_buckets_day_idx
  ON public.lm_provider_voice_buckets (budget_day, scope);
ALTER TABLE public.lm_provider_voice_buckets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_provider_voice_buckets FORCE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.lm_provider_voice_settlements (
  request_id  text PRIMARY KEY,
  uid         text NOT NULL,
  budget_day  date NOT NULL,
  amount_usd  numeric NOT NULL CHECK (amount_usd >= 0),
  reservation_request_id text,
  settled_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.lm_provider_voice_settlements
  ADD COLUMN IF NOT EXISTS reservation_request_id text;
-- A reservation may be settled by a delayed CDR after midnight.  The
-- reservation identity therefore cannot include the settlement day: the same
-- uid + reservation must be one settlement even when CDR IDs differ.
DROP INDEX IF EXISTS public.lm_provider_voice_settlement_reservation_idx;
CREATE UNIQUE INDEX IF NOT EXISTS lm_provider_voice_settlement_reservation_idx
  ON public.lm_provider_voice_settlements (uid, reservation_request_id);
ALTER TABLE public.lm_provider_voice_settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_provider_voice_settlements FORCE ROW LEVEL SECURITY;

-- The user and global rows are locked in one deterministic order. This makes
-- reservations race-safe across Railway instances; a boolean REST insert is
-- insufficient because two workers could both pass the pre-read cap check.
-- The 9-argument function shipped in the first version cannot be replaced with
-- a different signature in PostgreSQL, so remove it before installing the
-- version that also receives the atomic daily-cap parameters.
DROP FUNCTION IF EXISTS public.lm_claim_provider_budget(text, date, text, text, text, numeric, boolean, numeric, numeric);
CREATE OR REPLACE FUNCTION public.lm_claim_provider_budget(
  p_uid text,
  p_budget_day date,
  p_provider text,
  p_operation text,
  p_request_id text,
  p_projected_usd numeric,
  p_is_voice boolean,
  p_user_voice_cap numeric,
  p_global_voice_cap numeric,
  p_daily_cap numeric,
  p_enforce_daily_cap boolean
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid text := nullif(trim(p_uid), '');
  v_day date := coalesce(p_budget_day, current_date);
  v_user_settled numeric := 0;
  v_user_reserved numeric := 0;
  v_global_settled numeric := 0;
  v_global_reserved numeric := 0;
  v_daily_spend numeric := 0;
  v_outstanding_reserved numeric := 0;
  v_projected numeric := coalesce(p_projected_usd, 0);
  v_existing_projected numeric := NULL;
  v_claimed_request_id text := NULL;
BEGIN
  IF v_uid IS NULL OR nullif(trim(p_request_id), '') IS NULL OR v_projected < 0 THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'invalid_claim');
  END IF;

  -- Always create/lock the user row. Non-voice claims use this row as the
  -- per-user mutex for their atomic daily cap; voice claims also lock global
  -- after user so every instance observes the same lock order.
  INSERT INTO lm_provider_voice_buckets(scope, uid, budget_day)
    VALUES ('user', v_uid, v_day)
    ON CONFLICT (scope, uid, budget_day) DO NOTHING;
  SELECT settled_usd, reserved_usd INTO v_user_settled, v_user_reserved
    FROM lm_provider_voice_buckets
    WHERE scope = 'user' AND uid = v_uid AND budget_day = v_day
    FOR UPDATE;
  IF coalesce(p_is_voice, false) THEN
    INSERT INTO lm_provider_voice_buckets(scope, uid, budget_day)
      VALUES ('global', '', v_day)
      ON CONFLICT (scope, uid, budget_day) DO NOTHING;
    SELECT settled_usd, reserved_usd INTO v_global_settled, v_global_reserved
      FROM lm_provider_voice_buckets
      WHERE scope = 'global' AND uid = '' AND budget_day = v_day
      FOR UPDATE;
  END IF;

  SELECT projected_usd INTO v_existing_projected
    FROM lm_provider_budget_claims
    WHERE uid = v_uid AND budget_day = v_day AND request_id = p_request_id
    FOR SHARE;
  IF FOUND THEN
    RETURN jsonb_build_object('allowed', true, 'duplicate', true, 'request_id', p_request_id,
      'projected_usd', v_existing_projected);
  END IF;

  -- Settled spend is read from the ledger inside this transaction. Unknown
  -- rows contribute their persisted estimate only; null remains unknown and
  -- contributes nothing. A call-session estimate is superseded by a known CDR
  -- for the same reservation, preventing one call from being counted twice.
  SELECT coalesce(sum(
    CASE
      WHEN l.actual_status = 'known' AND l.actual_billed_usd IS NOT NULL THEN l.actual_billed_usd
      WHEN l.actual_status = 'unknown' THEN coalesce(l.estimated_usd, l.est_usd, 0)
      ELSE 0
    END
  ), 0)
  INTO v_daily_spend
  FROM lm_api_cost l
  WHERE l.uid = v_uid
    AND l.ts >= v_day::timestamptz
    AND l.ts < (v_day + 1)::timestamptz
    AND NOT (
      l.operation = 'call_session'
      AND l.actual_status = 'unknown'
      AND EXISTS (
        SELECT 1 FROM lm_api_cost cdr
        WHERE cdr.uid = l.uid
          AND cdr.operation = 'call_cdr'
          AND coalesce(cdr.metadata, cdr.meta)->>'reservationRequestId' = l.request_id
      )
    );

  -- Non-voice claims remain outstanding until their exact provider request is
  -- represented in the ledger. Voice claims use the locked bucket, whose
  -- reserved_usd is released by lm_settle_provider_voice.
  SELECT coalesce(sum(c.projected_usd), 0)
  INTO v_outstanding_reserved
  FROM lm_provider_budget_claims c
  WHERE c.uid = v_uid
    AND c.budget_day = v_day
    AND c.is_voice = false
    AND NOT EXISTS (
      SELECT 1 FROM lm_api_cost l
      WHERE l.uid = c.uid
        AND l.provider = c.provider
        AND l.request_id = c.request_id
    );
  v_outstanding_reserved := v_outstanding_reserved + CASE WHEN coalesce(p_is_voice, false) THEN v_user_reserved ELSE 0 END;

  IF coalesce(p_enforce_daily_cap, true)
     AND coalesce(p_daily_cap, 0) > 0
     AND v_daily_spend + v_outstanding_reserved + v_projected >= p_daily_cap THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'daily_provider_cap');
  END IF;

  IF coalesce(p_is_voice, false) AND v_user_settled + v_user_reserved + v_projected >= coalesce(p_user_voice_cap, 0) THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'voice_user_cap');
  END IF;
  IF coalesce(p_is_voice, false) AND v_global_settled + v_global_reserved + v_projected >= coalesce(p_global_voice_cap, 0) THEN
    RETURN jsonb_build_object('allowed', false, 'reason', 'voice_global_cap');
  END IF;

  INSERT INTO lm_provider_budget_claims(uid, budget_day, provider, operation, request_id, projected_usd, is_voice)
    VALUES (v_uid, v_day, coalesce(nullif(trim(p_provider), ''), 'unknown'), coalesce(nullif(trim(p_operation), ''), 'unknown'), p_request_id, v_projected, coalesce(p_is_voice, false))
    ON CONFLICT (uid, budget_day, request_id) DO NOTHING
    RETURNING request_id INTO v_claimed_request_id;
  IF NOT FOUND THEN
    SELECT projected_usd INTO v_existing_projected
      FROM lm_provider_budget_claims
      WHERE uid = v_uid AND budget_day = v_day AND request_id = p_request_id;
    RETURN jsonb_build_object('allowed', true, 'duplicate', true, 'request_id', p_request_id,
      'projected_usd', coalesce(v_existing_projected, v_projected));
  END IF;
  IF coalesce(p_is_voice, false) THEN
    UPDATE lm_provider_voice_buckets
      SET reserved_usd = reserved_usd + v_projected, updated_at = now()
      WHERE scope = 'user' AND uid = v_uid AND budget_day = v_day;
    UPDATE lm_provider_voice_buckets
      SET reserved_usd = reserved_usd + v_projected, updated_at = now()
      WHERE scope = 'global' AND uid = '' AND budget_day = v_day;
  END IF;
  RETURN jsonb_build_object('allowed', true, 'duplicate', false, 'request_id', p_request_id);
END;
$$;

-- CDR/usage imports settle an actual voice amount exactly once and release the
-- matching reservation when the caller supplies its claim request id.
CREATE OR REPLACE FUNCTION public.lm_settle_provider_voice(
  p_uid text,
  p_budget_day date,
  p_request_id text,
  p_actual_usd numeric,
  p_reservation_request_id text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid text := nullif(trim(p_uid), '');
  v_day date := coalesce(p_budget_day, current_date);
  v_amount numeric := coalesce(p_actual_usd, 0);
  v_reservation_request_id text := nullif(trim(p_reservation_request_id), '');
  v_reservation_day date := coalesce(p_budget_day, current_date);
  v_reserved numeric := 0;
  v_inserted boolean := false;
BEGIN
  IF v_uid IS NULL OR nullif(trim(p_request_id), '') IS NULL OR v_amount < 0 THEN
    RETURN jsonb_build_object('settled', false, 'reason', 'invalid_settlement');
  END IF;

  -- Imports can arrive after midnight. Resolve the original claim day by the
  -- stable reservation identity instead of assuming it is today's settlement
  -- day; the reservation bucket must be released where it was claimed.
  IF v_reservation_request_id IS NOT NULL THEN
    SELECT c.budget_day, c.projected_usd
      INTO v_reservation_day, v_reserved
      FROM lm_provider_budget_claims c
      WHERE c.uid = v_uid
        AND c.request_id = v_reservation_request_id
        AND c.is_voice = true
      ORDER BY c.claimed_at ASC, c.budget_day ASC
      LIMIT 1;
    v_reservation_day := coalesce(v_reservation_day, v_day);
    v_reserved := coalesce(v_reserved, 0);
  END IF;

  -- Lock both affected days in date order, and user before global on each
  -- day, so delayed settlement cannot deadlock with a new reservation.
  IF v_reservation_day < v_day THEN
    INSERT INTO lm_provider_voice_buckets(scope, uid, budget_day)
      VALUES ('user', v_uid, v_reservation_day), ('global', '', v_reservation_day)
      ON CONFLICT (scope, uid, budget_day) DO NOTHING;
    PERFORM 1 FROM lm_provider_voice_buckets
      WHERE scope = 'user' AND uid = v_uid AND budget_day = v_reservation_day FOR UPDATE;
    PERFORM 1 FROM lm_provider_voice_buckets
      WHERE scope = 'global' AND uid = '' AND budget_day = v_reservation_day FOR UPDATE;
  END IF;
  INSERT INTO lm_provider_voice_buckets(scope, uid, budget_day)
    VALUES ('user', v_uid, v_day), ('global', '', v_day)
    ON CONFLICT (scope, uid, budget_day) DO NOTHING;
  PERFORM 1 FROM lm_provider_voice_buckets
    WHERE scope = 'user' AND uid = v_uid AND budget_day = v_day FOR UPDATE;
  PERFORM 1 FROM lm_provider_voice_buckets
    WHERE scope = 'global' AND uid = '' AND budget_day = v_day FOR UPDATE;

  IF v_reservation_day > v_day THEN
    INSERT INTO lm_provider_voice_buckets(scope, uid, budget_day)
      VALUES ('user', v_uid, v_reservation_day), ('global', '', v_reservation_day)
      ON CONFLICT (scope, uid, budget_day) DO NOTHING;
    PERFORM 1 FROM lm_provider_voice_buckets
      WHERE scope = 'user' AND uid = v_uid AND budget_day = v_reservation_day FOR UPDATE;
    PERFORM 1 FROM lm_provider_voice_buckets
      WHERE scope = 'global' AND uid = '' AND budget_day = v_reservation_day FOR UPDATE;
  END IF;

  -- A CDR id is not the reservation identity.  A replay with a new CDR id
  -- must hit the reservation conflict target and return a durable duplicate
  -- receipt rather than raising a second unique violation.
  IF v_reservation_request_id IS NOT NULL THEN
    BEGIN
      INSERT INTO lm_provider_voice_settlements(request_id, uid, budget_day, amount_usd, reservation_request_id)
        VALUES (p_request_id, v_uid, v_day, v_amount, v_reservation_request_id)
        ON CONFLICT (uid, reservation_request_id) DO NOTHING;
      v_inserted := FOUND;
    EXCEPTION WHEN unique_violation THEN
      v_inserted := false;
    END;
  ELSE
    INSERT INTO lm_provider_voice_settlements(request_id, uid, budget_day, amount_usd, reservation_request_id)
      VALUES (p_request_id, v_uid, v_day, v_amount, NULL)
      ON CONFLICT (request_id) DO NOTHING;
    v_inserted := FOUND;
  END IF;
  IF NOT v_inserted THEN
    RETURN jsonb_build_object('settled', true, 'duplicate', true);
  END IF;
  UPDATE lm_provider_voice_buckets
    SET settled_usd = settled_usd + v_amount,
        reserved_usd = CASE WHEN v_reservation_day = v_day
          THEN greatest(0, reserved_usd - v_reserved) ELSE reserved_usd END,
        updated_at = now()
    WHERE scope = 'user' AND uid = v_uid AND budget_day = v_day;
  UPDATE lm_provider_voice_buckets
    SET settled_usd = settled_usd + v_amount,
        reserved_usd = CASE WHEN v_reservation_day = v_day
          THEN greatest(0, reserved_usd - v_reserved) ELSE reserved_usd END,
        updated_at = now()
    WHERE scope = 'global' AND uid = '' AND budget_day = v_day;
  IF v_reservation_day <> v_day AND v_reserved > 0 THEN
    UPDATE lm_provider_voice_buckets
      SET reserved_usd = greatest(0, reserved_usd - v_reserved), updated_at = now()
      WHERE scope = 'user' AND uid = v_uid AND budget_day = v_reservation_day;
    UPDATE lm_provider_voice_buckets
      SET reserved_usd = greatest(0, reserved_usd - v_reserved), updated_at = now()
      WHERE scope = 'global' AND uid = '' AND budget_day = v_reservation_day;
  END IF;
  RETURN jsonb_build_object('settled', true, 'duplicate', false);
END;
$$;

-- These functions mutate reservations and billing buckets.  SECURITY DEFINER
-- must never make them callable by browser roles; only the server-side
-- service-role key may invoke them.
REVOKE ALL ON FUNCTION public.lm_claim_provider_budget(text, date, text, text, text, numeric, boolean, numeric, numeric, numeric, boolean)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_claim_provider_budget(text, date, text, text, text, numeric, boolean, numeric, numeric, numeric, boolean)
  TO service_role;
REVOKE ALL ON FUNCTION public.lm_settle_provider_voice(text, date, text, numeric, text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_settle_provider_voice(text, date, text, numeric, text)
  TO service_role;
