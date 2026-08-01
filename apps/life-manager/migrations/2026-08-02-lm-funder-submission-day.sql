BEGIN;
CREATE TABLE IF NOT EXISTS public.lm_funder_submission_day_gates (
 tenant_id text NOT NULL, attempt_id uuid NOT NULL, gate_id text NOT NULL CHECK (gate_id ~ '^funder-day-gate:[0-9a-f]{64}$'), registry_id text NOT NULL,
 funder_id text NOT NULL, evaluated_at timestamptz NOT NULL, tokyo_day date NOT NULL, decision text NOT NULL CHECK (decision IN ('allow','registry_refresh_required','deadline_closed','solo_not_verified','eligibility_not_verified')),
 submit_allowed boolean NOT NULL, deadline_status text NOT NULL, deadline_at timestamptz, deadline_display_date date, location text NOT NULL,
 solo_allowed text NOT NULL, eligibility text NOT NULL, terms_hash text NOT NULL CHECK (terms_hash ~ '^[0-9a-f]{64}$'), kit_ref text NOT NULL,
 kit_digest text NOT NULL CHECK (kit_digest ~ '^[0-9a-f]{64}$'), evidence_refs jsonb NOT NULL, source_receipts jsonb NOT NULL,
 gate_digest text NOT NULL CHECK (gate_digest ~ '^[0-9a-f]{64}$'), attestation_signature text NOT NULL CHECK (attestation_signature ~ '^[0-9a-f]{64}$'), recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (tenant_id,attempt_id)
);
ALTER TABLE public.lm_funder_submission_day_gates ADD COLUMN IF NOT EXISTS attestation_signature text CHECK (attestation_signature IS NULL OR attestation_signature ~ '^[0-9a-f]{64}$');
ALTER TABLE public.lm_funder_submission_day_gates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_funder_submission_day_gates FROM PUBLIC;
COMMIT;
