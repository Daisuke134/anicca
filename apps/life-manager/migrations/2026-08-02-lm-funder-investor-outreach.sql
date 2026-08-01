-- O1C-19: append-only pre-send fence for the tenant/Tokyo-date five-message cap.

-- Upgrade path for databases where O1C-09 has already been applied. A migration
-- runner may execute only this new file, so do not rely on replaying the old file.
ALTER TABLE public.lm_funder_outreach_ledger
  ADD COLUMN IF NOT EXISTS investor_kind text,
  ADD COLUMN IF NOT EXISTS thesis_evidence_sha256 text,
  ADD COLUMN IF NOT EXISTS company_evidence_sha256 text,
  ADD COLUMN IF NOT EXISTS personalization_sha256 text,
  ADD COLUMN IF NOT EXISTS daily_slot smallint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.lm_funder_outreach_ledger'::regclass
      AND conname='lm_funder_outreach_investor_proof_v2_check'
  ) THEN
    ALTER TABLE public.lm_funder_outreach_ledger
      ADD CONSTRAINT lm_funder_outreach_investor_proof_v2_check CHECK (
        num_nonnulls(investor_kind,thesis_evidence_sha256,company_evidence_sha256,
          personalization_sha256,daily_slot) = 0
        OR
        (num_nonnulls(investor_kind,thesis_evidence_sha256,company_evidence_sha256,
          personalization_sha256,daily_slot) = 5
          AND investor_kind IN ('vc','angel')
          AND thesis_evidence_sha256 ~ '^[0-9a-f]{64}$'
          AND company_evidence_sha256 ~ '^[0-9a-f]{64}$'
          AND personalization_sha256 ~ '^[0-9a-f]{64}$'
          AND daily_slot BETWEEN 1 AND 5)
      );
  END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS lm_funder_outreach_ledger_daily_slot_uidx
  ON public.lm_funder_outreach_ledger (tenant_id,tokyo_date,daily_slot)
  WHERE daily_slot IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.lm_funder_investor_outreach_reservation (
  tenant_id text NOT NULL,
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  tokyo_date date NOT NULL,
  recipient_sha256 text NOT NULL CHECK (recipient_sha256 ~ '^[0-9a-f]{64}$'),
  investor_kind text NOT NULL CHECK (investor_kind IN ('vc','angel')),
  thesis_evidence_sha256 text NOT NULL CHECK (thesis_evidence_sha256 ~ '^[0-9a-f]{64}$'),
  company_evidence_sha256 text NOT NULL CHECK (company_evidence_sha256 ~ '^[0-9a-f]{64}$'),
  personalization_sha256 text NOT NULL CHECK (personalization_sha256 ~ '^[0-9a-f]{64}$'),
  daily_slot smallint NOT NULL CHECK (daily_slot BETWEEN 1 AND 5),
  reserved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, outreach_id),
  UNIQUE (tenant_id, recipient_sha256),
  UNIQUE (tenant_id, tokyo_date, daily_slot),
  UNIQUE (tenant_id, outreach_id, daily_slot),
  CONSTRAINT lm_funder_investor_reservation_binding_v2_key UNIQUE (
    tenant_id,outreach_id,tokyo_date,daily_slot,recipient_sha256,investor_kind,
    thesis_evidence_sha256,company_evidence_sha256,personalization_sha256
  )
);

ALTER TABLE public.lm_funder_investor_outreach_reservation ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_investor_outreach_reservation FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.lm_reserve_funder_investor_outreach(
  p_tenant_id text,
  p_tokyo_date date,
  p_outreach_id text,
  p_recipient_sha256 text,
  p_investor_kind text,
  p_thesis_evidence_sha256 text,
  p_company_evidence_sha256 text,
  p_personalization_sha256 text
) RETURNS TABLE (outreach_id text, daily_slot smallint, reserved_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_existing public.lm_funder_investor_outreach_reservation%ROWTYPE;
  v_used integer;
  v_slot smallint;
BEGIN
  IF p_tenant_id IS NULL OR p_tenant_id !~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$'
    OR p_tokyo_date IS NULL OR p_outreach_id IS NULL OR p_outreach_id !~ '^funder-outreach:[0-9a-f]{64}$'
    OR p_recipient_sha256 IS NULL OR p_recipient_sha256 !~ '^[0-9a-f]{64}$'
    OR p_investor_kind IS NULL OR p_investor_kind NOT IN ('vc','angel')
    OR p_thesis_evidence_sha256 IS NULL OR p_thesis_evidence_sha256 !~ '^[0-9a-f]{64}$'
    OR p_company_evidence_sha256 IS NULL OR p_company_evidence_sha256 !~ '^[0-9a-f]{64}$'
    OR p_personalization_sha256 IS NULL OR p_personalization_sha256 !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'funder investor reservation invalid' USING ERRCODE='22023';
  END IF;

  PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant_id || ':' || p_tokyo_date::text, 0));

  SELECT * INTO v_existing
  FROM public.lm_funder_investor_outreach_reservation AS r
  WHERE r.tenant_id=p_tenant_id AND r.outreach_id=p_outreach_id;
  IF FOUND THEN
    IF v_existing.tokyo_date IS DISTINCT FROM p_tokyo_date
      OR v_existing.recipient_sha256 IS DISTINCT FROM p_recipient_sha256
      OR v_existing.investor_kind IS DISTINCT FROM p_investor_kind
      OR v_existing.thesis_evidence_sha256 IS DISTINCT FROM p_thesis_evidence_sha256
      OR v_existing.company_evidence_sha256 IS DISTINCT FROM p_company_evidence_sha256
      OR v_existing.personalization_sha256 IS DISTINCT FROM p_personalization_sha256 THEN
      RAISE EXCEPTION 'funder investor reservation conflict' USING ERRCODE='23505';
    END IF;
    RETURN QUERY SELECT v_existing.outreach_id, v_existing.daily_slot, v_existing.reserved_at;
    RETURN;
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.lm_funder_outreach_ledger AS l
    WHERE l.tenant_id=p_tenant_id AND l.recipient_sha256=p_recipient_sha256
  ) OR EXISTS (
    SELECT 1 FROM public.lm_funder_investor_outreach_reservation AS r
    WHERE r.tenant_id=p_tenant_id AND r.recipient_sha256=p_recipient_sha256
  ) THEN
    RAISE EXCEPTION 'funder investor recipient already used' USING ERRCODE='23505';
  END IF;

  SELECT count(*) INTO v_used
  FROM (
    SELECT l.outreach_id FROM public.lm_funder_outreach_ledger AS l
      WHERE l.tenant_id=p_tenant_id AND l.tokyo_date=p_tokyo_date
    UNION
    SELECT r.outreach_id FROM public.lm_funder_investor_outreach_reservation AS r
      WHERE r.tenant_id=p_tenant_id AND r.tokyo_date=p_tokyo_date
  ) AS used_outreach;
  IF v_used >= 5 THEN
    RAISE EXCEPTION 'funder investor daily cap reached' USING ERRCODE='23514';
  END IF;
  v_slot := (v_used + 1)::smallint;

  INSERT INTO public.lm_funder_investor_outreach_reservation (
    tenant_id,outreach_id,tokyo_date,recipient_sha256,investor_kind,
    thesis_evidence_sha256,company_evidence_sha256,personalization_sha256,daily_slot
  ) VALUES (
    p_tenant_id,p_outreach_id,p_tokyo_date,p_recipient_sha256,p_investor_kind,
    p_thesis_evidence_sha256,p_company_evidence_sha256,p_personalization_sha256,v_slot
  ) RETURNING * INTO v_existing;
  RETURN QUERY SELECT v_existing.outreach_id, v_existing.daily_slot, v_existing.reserved_at;
END
$$;

REVOKE ALL ON FUNCTION public.lm_reserve_funder_investor_outreach(text,date,text,text,text,text,text,text) FROM PUBLIC;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.lm_funder_investor_outreach_reservation'::regclass
      AND conname='lm_funder_investor_reservation_binding_v2_key'
  ) THEN
    ALTER TABLE public.lm_funder_investor_outreach_reservation
      ADD CONSTRAINT lm_funder_investor_reservation_binding_v2_key UNIQUE (
        tenant_id,outreach_id,tokyo_date,daily_slot,recipient_sha256,investor_kind,
        thesis_evidence_sha256,company_evidence_sha256,personalization_sha256
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.lm_funder_outreach_ledger'::regclass
      AND conname='lm_funder_outreach_reservation_fk'
  ) THEN
    ALTER TABLE public.lm_funder_outreach_ledger
      ADD CONSTRAINT lm_funder_outreach_reservation_fk
      FOREIGN KEY (tenant_id,outreach_id,daily_slot)
      REFERENCES public.lm_funder_investor_outreach_reservation (tenant_id,outreach_id,daily_slot);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.lm_funder_outreach_ledger'::regclass
      AND conname='lm_funder_outreach_reservation_proof_v2_fk'
  ) THEN
    ALTER TABLE public.lm_funder_outreach_ledger
      ADD CONSTRAINT lm_funder_outreach_reservation_proof_v2_fk
      FOREIGN KEY (
        tenant_id,outreach_id,tokyo_date,daily_slot,recipient_sha256,investor_kind,
        thesis_evidence_sha256,company_evidence_sha256,personalization_sha256
      ) REFERENCES public.lm_funder_investor_outreach_reservation (
        tenant_id,outreach_id,tokyo_date,daily_slot,recipient_sha256,investor_kind,
        thesis_evidence_sha256,company_evidence_sha256,personalization_sha256
      );
  END IF;

  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_investor_outreach_reservation FROM anon';
    EXECUTE 'REVOKE ALL ON FUNCTION public.lm_reserve_funder_investor_outreach(text,date,text,text,text,text,text,text) FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_investor_outreach_reservation FROM authenticated';
    EXECUTE 'REVOKE ALL ON FUNCTION public.lm_reserve_funder_investor_outreach(text,date,text,text,text,text,text,text) FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
    EXECUTE 'REVOKE INSERT ON TABLE public.lm_funder_investor_outreach_reservation FROM service_role';
    EXECUTE 'GRANT SELECT ON TABLE public.lm_funder_investor_outreach_reservation TO service_role';
    EXECUTE 'GRANT SELECT ON TABLE public.lm_funder_outreach_ledger TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_reserve_funder_investor_outreach(text,date,text,text,text,text,text,text) TO service_role';
  END IF;
END
$$;
