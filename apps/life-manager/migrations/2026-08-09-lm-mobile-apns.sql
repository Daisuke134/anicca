-- Durable APNs delivery facts for the mobile semantic outbox.
-- Device credentials and notification content deliberately stay outside this table.

CREATE TABLE IF NOT EXISTS public.lm_mobile_apns_results (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  message_id text NOT NULL,
  device_id text,
  apns_id text,
  status integer,
  reason text,
  environment text CHECK (environment IS NULL OR environment IN ('production', 'development')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_mobile_apns_results_uid_message_idx
  ON public.lm_mobile_apns_results (uid, message_id, created_at);

ALTER TABLE public.lm_mobile_apns_results ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.lm_mobile_apns_results FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_mobile_apns_results TO service_role;
