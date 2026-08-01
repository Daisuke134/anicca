-- O1C-10: append-only scheduling decisions and at-most-two follow-up receipts.

CREATE TABLE IF NOT EXISTS public.lm_funder_followup_decisions (
  tenant_id text NOT NULL,
  decision_id text NOT NULL CHECK (decision_id ~ '^funder-followup-decision:[0-9a-f]{64}$'),
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  candidate_id text NOT NULL,
  status text NOT NULL CHECK (status IN ('scheduled', 'suppressed_inbound', 'complete')),
  followup_number smallint CHECK (followup_number IN (1, 2)),
  due_at timestamptz,
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  inbound_message_id text CHECK (inbound_message_id ~ '^[0-9a-f]{16,32}$'),
  observed_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, decision_id),
  FOREIGN KEY (tenant_id, outreach_id)
    REFERENCES public.lm_funder_outreach_ledger (tenant_id, outreach_id) ON DELETE RESTRICT,
  CHECK (
    (status = 'scheduled' AND followup_number IS NOT NULL AND due_at IS NOT NULL AND inbound_message_id IS NULL) OR
    (status = 'suppressed_inbound' AND followup_number IS NULL AND due_at IS NULL AND inbound_message_id IS NOT NULL) OR
    (status = 'complete' AND followup_number IS NULL AND due_at IS NULL AND inbound_message_id IS NULL)
  )
);

CREATE TABLE IF NOT EXISTS public.lm_funder_followup_ledger (
  tenant_id text NOT NULL,
  followup_id text NOT NULL CHECK (followup_id ~ '^funder-followup:[0-9a-f]{64}$'),
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  batch_id text NOT NULL CHECK (batch_id ~ '^funder-outreach-batch:[0-9a-f]{64}$'),
  candidate_id text NOT NULL,
  followup_number smallint NOT NULL CHECK (followup_number IN (1, 2)),
  due_at timestamptz NOT NULL,
  sent_at timestamptz NOT NULL CHECK (sent_at >= due_at),
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  rationale_sha256 text NOT NULL CHECK (rationale_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 text NOT NULL CHECK (subject_sha256 ~ '^[0-9a-f]{64}$'),
  body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, followup_id),
  UNIQUE (tenant_id, outreach_id, followup_number),
  UNIQUE (tenant_id, provider_message_id),
  FOREIGN KEY (tenant_id, outreach_id)
    REFERENCES public.lm_funder_outreach_ledger (tenant_id, outreach_id) ON DELETE RESTRICT
);

ALTER TABLE public.lm_funder_followup_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_funder_followup_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_followup_decisions FROM PUBLIC;
REVOKE ALL ON TABLE public.lm_funder_followup_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_followup_decisions FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_followup_ledger FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_followup_decisions FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_followup_ledger FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_followup_decisions TO service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_followup_ledger TO service_role';
  END IF;
END
$$;
