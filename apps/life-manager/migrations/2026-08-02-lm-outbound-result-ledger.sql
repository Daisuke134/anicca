-- O1C-17: Job Hunter-compatible common outbound result tracker.

CREATE TABLE IF NOT EXISTS public.lm_outbound_result_ledger (
  tenant_id text NOT NULL,
  result_id text NOT NULL CHECK (result_id ~ '^outbound-result:[0-9a-f]{64}$'),
  organ text NOT NULL CHECK (organ IN ('job_hunter', 'fundraising')),
  workflow text NOT NULL,
  source_kind text NOT NULL,
  source_id text NOT NULL,
  source_fence integer NOT NULL CHECK (source_fence >= 1),
  entity_id text NOT NULL,
  result_type text NOT NULL CHECK (result_type IN ('confirmation', 'reply')),
  status text NOT NULL CHECK (status IN (
    'confirmed', 'reply_received', 'rejected', 'meeting_requested'
  )),
  provider_message_id text NOT NULL CHECK (provider_message_id ~ '^[0-9a-f]{16,32}$'),
  provider_thread_id text NOT NULL CHECK (provider_thread_id ~ '^[0-9a-f]{16,32}$'),
  occurred_at timestamptz NOT NULL,
  sender_sha256 text CHECK (sender_sha256 IS NULL OR sender_sha256 ~ '^[0-9a-f]{64}$'),
  subject_sha256 text CHECK (subject_sha256 IS NULL OR subject_sha256 ~ '^[0-9a-f]{64}$'),
  body_sha256 text CHECK (body_sha256 IS NULL OR body_sha256 ~ '^[0-9a-f]{64}$'),
  message_sha256 text NOT NULL CHECK (message_sha256 ~ '^[0-9a-f]{64}$'),
  evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
  rationale_sha256 text NOT NULL CHECK (rationale_sha256 ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, result_id),
  UNIQUE (tenant_id, provider_message_id),
  CHECK ((result_type = 'confirmation' AND status = 'confirmed') OR
         (result_type = 'reply' AND status IN (
           'reply_received', 'rejected', 'meeting_requested'
         ))),
  CONSTRAINT lm_outbound_fundraising_content_check CHECK (organ <> 'fundraising' OR
    (sender_sha256 IS NOT NULL AND subject_sha256 IS NOT NULL AND body_sha256 IS NOT NULL)),
  CONSTRAINT lm_outbound_job_hunter_content_check CHECK (organ <> 'job_hunter' OR
    (sender_sha256 IS NULL AND subject_sha256 IS NULL AND body_sha256 IS NULL))
);

-- Upgrade the same-day pre-bridge O1C-17 table without dropping its live row.
ALTER TABLE public.lm_outbound_result_ledger
  ALTER COLUMN sender_sha256 DROP NOT NULL,
  ALTER COLUMN subject_sha256 DROP NOT NULL,
  ALTER COLUMN body_sha256 DROP NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
    WHERE conname = 'lm_outbound_fundraising_content_check'
      AND conrelid = 'public.lm_outbound_result_ledger'::regclass) THEN
    ALTER TABLE public.lm_outbound_result_ledger
      ADD CONSTRAINT lm_outbound_fundraising_content_check CHECK
      (organ <> 'fundraising' OR
        (sender_sha256 IS NOT NULL AND subject_sha256 IS NOT NULL AND body_sha256 IS NOT NULL));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
    WHERE conname = 'lm_outbound_job_hunter_content_check'
      AND conrelid = 'public.lm_outbound_result_ledger'::regclass) THEN
    ALTER TABLE public.lm_outbound_result_ledger
      ADD CONSTRAINT lm_outbound_job_hunter_content_check CHECK
      (organ <> 'job_hunter' OR
        (sender_sha256 IS NULL AND subject_sha256 IS NULL AND body_sha256 IS NULL));
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS lm_outbound_result_thread_idx
  ON public.lm_outbound_result_ledger
  (tenant_id, provider_thread_id, occurred_at, provider_message_id);

CREATE OR REPLACE FUNCTION public.lm_outbound_result_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lm_outbound_result_ledger is append-only';
END
$$;

DROP TRIGGER IF EXISTS lm_outbound_result_no_mutation
  ON public.lm_outbound_result_ledger;
CREATE TRIGGER lm_outbound_result_no_mutation
BEFORE UPDATE OR DELETE ON public.lm_outbound_result_ledger
FOR EACH ROW EXECUTE FUNCTION public.lm_outbound_result_immutable();

DROP TRIGGER IF EXISTS lm_outbound_result_no_truncate
  ON public.lm_outbound_result_ledger;
CREATE TRIGGER lm_outbound_result_no_truncate
BEFORE TRUNCATE ON public.lm_outbound_result_ledger
FOR EACH STATEMENT EXECUTE FUNCTION public.lm_outbound_result_immutable();

ALTER TABLE public.lm_outbound_result_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_outbound_result_ledger FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON TABLE public.lm_outbound_result_ledger FROM PUBLIC;

CREATE OR REPLACE VIEW public.lm_outbound_current_result
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (tenant_id, organ, workflow, entity_id)
  tenant_id, organ, workflow, entity_id, result_type, status,
  provider_message_id, provider_thread_id, occurred_at, result_id
FROM public.lm_outbound_result_ledger
ORDER BY tenant_id, organ, workflow, entity_id, occurred_at DESC, result_id DESC;

REVOKE ALL ON TABLE public.lm_outbound_current_result FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_outbound_result_ledger FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_outbound_current_result FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_outbound_result_ledger FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_outbound_current_result FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.lm_outbound_result_ledger FROM service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_outbound_result_ledger TO service_role';
    EXECUTE 'GRANT SELECT ON TABLE public.lm_outbound_current_result TO service_role';
  END IF;
END
$$;
