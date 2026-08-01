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
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, outreach_id),
  UNIQUE (tenant_id, recipient_sha256),
  UNIQUE (tenant_id, provider_message_id)
);

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
