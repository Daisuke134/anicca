-- O1B-12: keep attendee registration and talk application as separate durable entities.

CREATE TABLE IF NOT EXISTS public.lm_event_participation_entities (
  tenant_id text NOT NULL,
  entity_id text NOT NULL CHECK (entity_id ~ '^event-entity:[0-9a-f]{64}$'),
  event_ref text NOT NULL CHECK (char_length(event_ref) BETWEEN 3 AND 500),
  entity_kind text NOT NULL CHECK (entity_kind IN ('audience_registration', 'talk_application')),
  canonical_url text NOT NULL CHECK (canonical_url ~ '^https://'),
  status text NOT NULL CHECK (status IN (
    'discovered', 'queued', 'unavailable', 'registered', 'cancelled',
    'drafted', 'submitted', 'accepted', 'rejected', 'withdrawn', 'presented', 'closed'
  )),
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, entity_id)
);

CREATE INDEX IF NOT EXISTS lm_event_participation_entities_event_idx
  ON public.lm_event_participation_entities (tenant_id, event_ref, entity_kind);

CREATE TABLE IF NOT EXISTS public.lm_event_participation_transitions (
  transition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id text NOT NULL,
  entity_id text NOT NULL,
  entity_kind text NOT NULL CHECK (entity_kind IN ('audience_registration', 'talk_application')),
  from_status text NOT NULL,
  to_status text NOT NULL,
  version integer NOT NULL CHECK (version >= 2),
  occurred_at timestamptz NOT NULL,
  receipt_ref text CHECK (receipt_ref IS NULL OR char_length(receipt_ref) BETWEEN 3 AND 500),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id, entity_id, version),
  FOREIGN KEY (tenant_id, entity_id)
    REFERENCES public.lm_event_participation_entities (tenant_id, entity_id)
    ON DELETE RESTRICT
);

ALTER TABLE public.lm_event_participation_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_event_participation_transitions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_event_participation_entities FROM PUBLIC;
REVOKE ALL ON TABLE public.lm_event_participation_transitions FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_participation_entities FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_participation_transitions FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_participation_entities FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_participation_transitions FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_event_participation_entities TO service_role';
    EXECUTE 'GRANT SELECT, INSERT ON TABLE public.lm_event_participation_transitions TO service_role';
  END IF;
END
$$;
