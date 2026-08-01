-- O1C-12: one immutable Calendar receipt per typed funder meeting request.

CREATE TABLE IF NOT EXISTS public.lm_funder_meeting_ledger (
  tenant_id text NOT NULL,
  meeting_id text NOT NULL CHECK (meeting_id ~ '^funder-meeting:[0-9a-f]{64}$'),
  outreach_id text NOT NULL CHECK (outreach_id ~ '^funder-outreach:[0-9a-f]{64}$'),
  candidate_id text NOT NULL,
  status_observation_id text NOT NULL CHECK (status_observation_id ~ '^funder-inbound-status:[0-9a-f]{64}$'),
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  scheduled_start_at timestamptz NOT NULL,
  scheduled_end_at timestamptz NOT NULL CHECK (scheduled_end_at > scheduled_start_at),
  provider_event_id text NOT NULL,
  provider_event_url text NOT NULL CHECK (provider_event_url ~ '^https://calendar.google.com/'),
  schedule_evidence_sha256 text NOT NULL CHECK (schedule_evidence_sha256 ~ '^[0-9a-f]{64}$'),
  schedule_rationale_sha256 text NOT NULL CHECK (schedule_rationale_sha256 ~ '^[0-9a-f]{64}$'),
  brief_sha256 text NOT NULL CHECK (brief_sha256 ~ '^[0-9a-f]{64}$'),
  brief_rationale_sha256 text NOT NULL CHECK (brief_rationale_sha256 ~ '^[0-9a-f]{64}$'),
  kit_digest text NOT NULL CHECK (kit_digest ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, meeting_id),
  UNIQUE (tenant_id, status_observation_id),
  UNIQUE (tenant_id, provider_event_id),
  FOREIGN KEY (tenant_id, outreach_id)
    REFERENCES public.lm_funder_outreach_ledger (tenant_id, outreach_id) ON DELETE RESTRICT,
  FOREIGN KEY (tenant_id, status_observation_id)
    REFERENCES public.lm_funder_inbound_status_ledger (tenant_id, observation_id) ON DELETE RESTRICT
);

ALTER TABLE public.lm_funder_meeting_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_funder_meeting_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_meeting_ledger FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_funder_meeting_ledger FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_funder_meeting_ledger TO service_role';
  END IF;
END
$$;
