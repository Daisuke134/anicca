-- O1B-14: one durable accepted-talk timeline from acceptance through follow-up.

CREATE TABLE IF NOT EXISTS public.lm_event_talk_timelines (
  tenant_id text NOT NULL,
  timeline_id text NOT NULL CHECK (timeline_id ~ '^talk-timeline:[0-9a-f]{64}$'),
  talk_entity_id text NOT NULL CHECK (talk_entity_id ~ '^event-entity:[0-9a-f]{64}$'),
  event_ref text NOT NULL CHECK (char_length(event_ref) BETWEEN 3 AND 500),
  canonical_url text NOT NULL CHECK (canonical_url ~ '^https://'),
  accepted_receipt_ref text NOT NULL CHECK (char_length(accepted_receipt_ref) BETWEEN 3 AND 500),
  items jsonb NOT NULL CHECK (jsonb_typeof(items) = 'array' AND jsonb_array_length(items) = 5),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, timeline_id),
  UNIQUE (tenant_id, talk_entity_id),
  FOREIGN KEY (tenant_id, talk_entity_id)
    REFERENCES public.lm_event_participation_entities (tenant_id, entity_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lm_event_talk_timelines_event_idx
  ON public.lm_event_talk_timelines (tenant_id, event_ref);

ALTER TABLE public.lm_event_talk_timelines ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_event_talk_timelines FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_talk_timelines FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_event_talk_timelines FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_event_talk_timelines TO service_role';
  END IF;
END
$$;
