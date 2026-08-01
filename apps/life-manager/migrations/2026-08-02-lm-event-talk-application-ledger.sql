-- O1B-15: append-only external-status ledger for talk applications.

CREATE TABLE IF NOT EXISTS public.lm_event_talk_application_ledger (
  tenant_id text NOT NULL,
  ledger_id text NOT NULL CHECK (ledger_id ~ '^talk-ledger:[0-9a-f]{64}$'),
  talk_entity_id text NOT NULL CHECK (talk_entity_id ~ '^event-entity:[0-9a-f]{64}$'),
  event_ref text NOT NULL CHECK (char_length(event_ref) BETWEEN 3 AND 500),
  from_status text NOT NULL,
  status text NOT NULL CHECK (status IN ('submitted', 'accepted', 'rejected', 'presented')),
  receipt_ref text NOT NULL CHECK (char_length(receipt_ref) BETWEEN 3 AND 500),
  entity_version integer NOT NULL CHECK (entity_version >= 2),
  occurred_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, ledger_id),
  UNIQUE (tenant_id, talk_entity_id, status),
  UNIQUE (tenant_id, receipt_ref),
  FOREIGN KEY (tenant_id, talk_entity_id)
    REFERENCES public.lm_event_participation_entities (tenant_id, entity_id)
    ON DELETE RESTRICT,
  CHECK (
    (status = 'submitted' AND from_status = 'drafted') OR
    (status IN ('accepted', 'rejected') AND from_status = 'submitted') OR
    (status = 'presented' AND from_status = 'accepted')
  )
);

CREATE INDEX IF NOT EXISTS lm_event_talk_application_ledger_event_idx
  ON public.lm_event_talk_application_ledger (tenant_id, event_ref, occurred_at);

ALTER TABLE public.lm_event_talk_application_ledger ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_event_talk_application_ledger FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_talk_application_ledger FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_talk_application_ledger FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_event_talk_application_ledger TO service_role';
  END IF;
END
$$;
