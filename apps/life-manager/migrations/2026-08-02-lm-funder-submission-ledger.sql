-- O1C-08: append-only evidence ledger for verified funder submissions.

CREATE TABLE IF NOT EXISTS public.lm_funder_submission_ledger (
  tenant_id text NOT NULL,
  ledger_id text NOT NULL CHECK (ledger_id ~ '^funder-ledger:[0-9a-f]{64}$'),
  funder_id text NOT NULL CHECK (funder_id = 'yc-fall-2026'),
  draft_id uuid NOT NULL,
  application_url text NOT NULL CHECK (application_url = 'https://apply.ycombinator.com/home'),
  status text NOT NULL CHECK (status = 'submitted'),
  provider_status text NOT NULL CHECK (provider_status = 'in_review'),
  submitted_at timestamptz NOT NULL,
  home_observed_at timestamptz NOT NULL,
  mail_message_id text NOT NULL CHECK (mail_message_id ~ '^[0-9a-f]{16}$'),
  mail_thread_id text NOT NULL CHECK (mail_thread_id ~ '^[0-9a-f]{16}$'),
  mail_sender text NOT NULL CHECK (mail_sender = 'apply@ycombinator.com'),
  mail_subject text NOT NULL CHECK (mail_subject = 'YC Fall 2026 Application Submitted'),
  mail_auth jsonb NOT NULL CHECK (mail_auth = '{"dkim":true,"spf":true,"dmarc":true}'::jsonb),
  evidence_digest text NOT NULL CHECK (evidence_digest ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, ledger_id),
  UNIQUE (tenant_id, funder_id, draft_id, status),
  UNIQUE (tenant_id, mail_message_id),
  CHECK (home_observed_at >= submitted_at AND home_observed_at <= submitted_at + interval '10 minutes')
);

ALTER TABLE public.lm_funder_submission_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_submission_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_submission_ledger FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_submission_ledger FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_submission_ledger TO service_role';
  END IF;
END
$$;
