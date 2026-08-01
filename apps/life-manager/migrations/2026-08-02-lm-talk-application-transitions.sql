CREATE UNIQUE INDEX IF NOT EXISTS lm_event_participations_id_tenant_uidx
  ON public.lm_event_participations (participation_id, tenant_id);

CREATE TABLE IF NOT EXISTS public.lm_talk_application_transitions (
  transition_id text PRIMARY KEY CHECK (transition_id ~ '^talk-transition:[0-9a-f]{64}$'),
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  participation_id text NOT NULL CHECK (participation_id ~ '^event-participation:[0-9a-f]{64}$'),
  from_state text NOT NULL,
  to_state text NOT NULL,
  observed_at timestamptz NOT NULL,
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 1 AND 500),
  source_refs jsonb NOT NULL CHECK (jsonb_typeof(source_refs) = 'array' AND jsonb_array_length(source_refs) BETWEEN 1 AND 20),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (participation_id, tenant_id)
    REFERENCES public.lm_event_participations (participation_id, tenant_id),
  CHECK (
    (from_state = 'discovered' AND to_state = 'submission_queued')
    OR (from_state = 'submission_queued' AND to_state IN ('submitted', 'withdrawn'))
    OR (from_state = 'submitted' AND to_state IN ('accepted', 'rejected', 'withdrawn'))
    OR (from_state = 'accepted' AND to_state IN ('presented', 'withdrawn'))
  )
);

CREATE OR REPLACE FUNCTION public.lm_talk_transition_before_insert()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  parent_kind text;
  parent_state text;
BEGIN
  SELECT kind, state INTO parent_kind, parent_state
  FROM public.lm_event_participations
  WHERE participation_id = NEW.participation_id AND tenant_id = NEW.tenant_id
  FOR UPDATE;
  IF NOT FOUND OR parent_kind <> 'talk_application' OR parent_state <> NEW.from_state THEN
    RAISE EXCEPTION 'talk application transition current state mismatch';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_talk_transition_current_gate ON public.lm_talk_application_transitions;
CREATE TRIGGER lm_talk_transition_current_gate
BEFORE INSERT ON public.lm_talk_application_transitions
FOR EACH ROW EXECUTE FUNCTION public.lm_talk_transition_before_insert();

CREATE OR REPLACE FUNCTION public.lm_talk_transition_project_current()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  affected integer;
BEGIN
  UPDATE public.lm_event_participations
  SET state = NEW.to_state, updated_at = clock_timestamp()
  WHERE participation_id = NEW.participation_id AND tenant_id = NEW.tenant_id
    AND kind = 'talk_application' AND state = NEW.from_state;
  GET DIAGNOSTICS affected = ROW_COUNT;
  IF affected <> 1 THEN
    RAISE EXCEPTION 'talk application transition projection failed';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_talk_transition_project_current ON public.lm_talk_application_transitions;
CREATE TRIGGER lm_talk_transition_project_current
AFTER INSERT ON public.lm_talk_application_transitions
FOR EACH ROW EXECUTE FUNCTION public.lm_talk_transition_project_current();

CREATE OR REPLACE FUNCTION public.lm_talk_transition_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'talk application transitions are immutable';
END;
$$;

DROP TRIGGER IF EXISTS lm_talk_transition_immutable ON public.lm_talk_application_transitions;
CREATE TRIGGER lm_talk_transition_immutable
BEFORE UPDATE OR DELETE ON public.lm_talk_application_transitions
FOR EACH ROW EXECUTE FUNCTION public.lm_talk_transition_immutable();

CREATE INDEX IF NOT EXISTS lm_talk_transition_tenant_participation_idx
  ON public.lm_talk_application_transitions (tenant_id, participation_id, observed_at, created_at);

ALTER TABLE public.lm_talk_application_transitions ENABLE ROW LEVEL SECURITY;
