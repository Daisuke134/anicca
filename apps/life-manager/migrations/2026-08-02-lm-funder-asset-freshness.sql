BEGIN;
CREATE TABLE IF NOT EXISTS public.lm_funder_asset_freshness_gates (
 tenant_id text NOT NULL, attempt_id uuid NOT NULL, gate_id text NOT NULL CHECK (gate_id ~ '^funder-freshness-gate:[0-9a-f]{64}$'), funder_id text NOT NULL,
 evaluated_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, decision text NOT NULL CHECK (decision IN ('allow','refresh_required')), submit_allowed boolean NOT NULL,
 kit_digest text NOT NULL CHECK (kit_digest ~ '^[0-9a-f]{64}$'), kit_captured_at timestamptz NOT NULL, submission_binding jsonb NOT NULL, payload_claim_receipts jsonb NOT NULL, dashboard_receipt jsonb NOT NULL, mrr_receipt jsonb NOT NULL,
 claim_receipts jsonb NOT NULL, asset_receipts jsonb NOT NULL, refresh_reasons jsonb NOT NULL,
 gate_digest text NOT NULL CHECK (gate_digest ~ '^[0-9a-f]{64}$'), attestation_signature text NOT NULL CHECK (attestation_signature ~ '^[0-9a-f]{64}$'), recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id,attempt_id)
);
ALTER TABLE public.lm_funder_asset_freshness_gates ADD COLUMN IF NOT EXISTS expires_at timestamptz;
ALTER TABLE public.lm_funder_asset_freshness_gates ADD COLUMN IF NOT EXISTS kit_captured_at timestamptz;
ALTER TABLE public.lm_funder_asset_freshness_gates ADD COLUMN IF NOT EXISTS submission_binding jsonb;
ALTER TABLE public.lm_funder_asset_freshness_gates ADD COLUMN IF NOT EXISTS payload_claim_receipts jsonb;
ALTER TABLE public.lm_funder_asset_freshness_gates ADD COLUMN IF NOT EXISTS attestation_signature text CHECK (attestation_signature IS NULL OR attestation_signature ~ '^[0-9a-f]{64}$');
ALTER TABLE public.lm_funder_asset_freshness_gates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_funder_asset_freshness_gates FROM PUBLIC;
CREATE OR REPLACE FUNCTION public.lm_funder_asset_freshness_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'lm_funder_asset_freshness_gates is append-only'; END
$$;
DROP TRIGGER IF EXISTS lm_funder_asset_freshness_append_only ON public.lm_funder_asset_freshness_gates;
CREATE TRIGGER lm_funder_asset_freshness_append_only BEFORE UPDATE OR DELETE ON public.lm_funder_asset_freshness_gates FOR EACH ROW EXECUTE FUNCTION public.lm_funder_asset_freshness_append_only();
CREATE OR REPLACE FUNCTION public.lm_funder_asset_freshness_no_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'lm_funder_asset_freshness_gates is append-only'; END
$$;
DROP TRIGGER IF EXISTS lm_funder_asset_freshness_no_truncate ON public.lm_funder_asset_freshness_gates;
CREATE TRIGGER lm_funder_asset_freshness_no_truncate BEFORE TRUNCATE ON public.lm_funder_asset_freshness_gates FOR EACH STATEMENT EXECUTE FUNCTION public.lm_funder_asset_freshness_no_truncate();
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN EXECUTE 'REVOKE ALL ON public.lm_funder_asset_freshness_gates FROM anon'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN EXECUTE 'REVOKE ALL ON public.lm_funder_asset_freshness_gates FROM authenticated'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
  EXECUTE 'REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.lm_funder_asset_freshness_gates FROM service_role';
  EXECUTE 'GRANT SELECT, INSERT ON public.lm_funder_asset_freshness_gates TO service_role';
 END IF;
END
$$;
COMMIT;
