-- O1C-11: append-only typed Gmail inbound observations and derived current status.

CREATE TABLE IF NOT EXISTS public.lm_funder_inbound_status_ledger (
  tenant_id text NOT NULL,
  observation_id text NOT NULL CHECK (observation_id ~ '^funder-inbound-status:[0-9a-f]{64}$'),
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  candidate_id text NOT NULL,
  status text NOT NULL CHECK (status IN (
    'delivery_failed', 'reply_received', 'rejected', 'meeting_requested'
  )),
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  observed_at timestamptz NOT NULL,
  sender_sha256 text NOT NULL CHECK (sender_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 text NOT NULL CHECK (subject_sha256 ~ '^[0-9a-f]{64}$'),
  body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$'),
  evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
  rationale_sha256 text NOT NULL CHECK (rationale_sha256 ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, observation_id),
  UNIQUE (tenant_id, provider_message_id),
  FOREIGN KEY (tenant_id, outreach_id)
    REFERENCES public.lm_funder_outreach_ledger (tenant_id, outreach_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lm_funder_inbound_status_thread_idx
  ON public.lm_funder_inbound_status_ledger (tenant_id, provider_thread_id, observed_at DESC);

ALTER TABLE public.lm_funder_inbound_status_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_inbound_status_ledger FROM PUBLIC;

CREATE OR REPLACE VIEW public.lm_funder_current_status
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (tenant_id, outreach_id)
  tenant_id, outreach_id, candidate_id, status, provider_message_id,
  provider_thread_id, observed_at, observation_id
FROM public.lm_funder_inbound_status_ledger
ORDER BY tenant_id, outreach_id, observed_at DESC, observation_id DESC;

REVOKE ALL ON TABLE public.lm_funder_current_status FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_inbound_status_ledger FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_current_status FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_inbound_status_ledger FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_current_status FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_inbound_status_ledger TO service_role';
    EXECUTE 'GRANT SELECT ON TABLE public.lm_funder_current_status TO service_role';
  END IF;
END
$$;
