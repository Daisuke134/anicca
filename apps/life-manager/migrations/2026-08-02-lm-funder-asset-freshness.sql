BEGIN;
CREATE TABLE IF NOT EXISTS public.lm_funder_asset_freshness_gates (
 tenant_id text NOT NULL, attempt_id uuid NOT NULL, gate_id text NOT NULL CHECK (gate_id ~ '^funder-freshness-gate:[0-9a-f]{64}$'), funder_id text NOT NULL,
 evaluated_at timestamptz NOT NULL, decision text NOT NULL CHECK (decision IN ('allow','refresh_required')), submit_allowed boolean NOT NULL,
 kit_digest text NOT NULL CHECK (kit_digest ~ '^[0-9a-f]{64}$'), dashboard_receipt jsonb NOT NULL, mrr_receipt jsonb NOT NULL,
 claim_receipts jsonb NOT NULL, asset_receipts jsonb NOT NULL, refresh_reasons jsonb NOT NULL,
 gate_digest text NOT NULL CHECK (gate_digest ~ '^[0-9a-f]{64}$'), recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id,attempt_id)
);
ALTER TABLE public.lm_funder_asset_freshness_gates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_funder_asset_freshness_gates FROM PUBLIC;
COMMIT;
