-- O1C-09: append-only evidence ledger for daily funder cold outreach.

CREATE TABLE IF NOT EXISTS public.lm_funder_outreach_ledger (
  tenant_id text NOT NULL,
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  batch_id text NOT NULL CHECK (batch_id ~ '^funder-outreach-batch:[0-9a-f]{64}$'),
  tokyo_date date NOT NULL,
  candidate_id text NOT NULL,
  funder_name text NOT NULL,
  recipient_sha256 text NOT NULL CHECK (recipient_sha256 ~ '^[0-9a-f]{64}$'),
  source_url text NOT NULL CHECK (source_url ~ '^https://'),
  source_observed_at timestamptz NOT NULL,
  source_digest text NOT NULL CHECK (source_digest ~ '^[0-9a-f]{64}$'),
  fit_summary_sha256 text NOT NULL CHECK (fit_summary_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 text NOT NULL CHECK (subject_sha256 ~ '^[0-9a-f]{64}$'),
  body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
  sent_at timestamptz NOT NULL,
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  investor_kind text,
  thesis_evidence_sha256 text,
  company_evidence_sha256 text,
  personalization_sha256 text,
  daily_slot smallint,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, outreach_id),
  UNIQUE (tenant_id, recipient_sha256),
  UNIQUE (tenant_id, provider_message_id)
);

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
      AND conname='lm_funder_outreach_investor_proof_check'
  ) THEN
    ALTER TABLE public.lm_funder_outreach_ledger
      ADD CONSTRAINT lm_funder_outreach_investor_proof_check CHECK (
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
  ON public.lm_funder_outreach_ledger (tenant_id, tokyo_date, daily_slot)
  WHERE daily_slot IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_funder_outreach_ledger_date_idx
  ON public.lm_funder_outreach_ledger (tenant_id, tokyo_date, sent_at);

ALTER TABLE public.lm_funder_outreach_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_outreach_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_outreach_ledger FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_outreach_ledger FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_outreach_ledger TO service_role';
  END IF;
END
$$;
