CREATE UNIQUE INDEX IF NOT EXISTS lm_event_participations_id_tenant_uidx
  ON public.lm_event_participations (participation_id, tenant_id);

CREATE TABLE IF NOT EXISTS public.lm_talk_timeline_snapshots (
  snapshot_id text PRIMARY KEY CHECK (snapshot_id ~ '^talk-timeline:[0-9a-f]{64}$'),
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  participation_id text NOT NULL CHECK (participation_id ~ '^event-participation:[0-9a-f]{64}$'),
  accepted_at timestamptz NOT NULL,
  slide_status text NOT NULL CHECK (slide_status IN ('known', 'pending', 'not_required')),
  slide_due_at timestamptz,
  appearance_start_at timestamptz NOT NULL,
  appearance_end_at timestamptz NOT NULL,
  venue_status text NOT NULL CHECK (venue_status IN ('known', 'pending')),
  venue_name text,
  venue_address text,
  ticket_status text NOT NULL CHECK (ticket_status IN ('ready', 'pending', 'not_required')),
  ticket_ref text CHECK (ticket_ref IS NULL OR ticket_ref ~ '^object://sha256/[0-9a-f]{64}$'),
  follow_up_at timestamptz NOT NULL,
  follow_up_purpose text NOT NULL CHECK (char_length(follow_up_purpose) BETWEEN 1 AND 300),
  follow_up_reason text NOT NULL CHECK (char_length(follow_up_reason) BETWEEN 1 AND 500),
  source_refs jsonb NOT NULL CHECK (jsonb_typeof(source_refs) = 'array' AND jsonb_array_length(source_refs) BETWEEN 1 AND 20),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (participation_id, tenant_id)
    REFERENCES public.lm_event_participations (participation_id, tenant_id),
  CHECK (accepted_at < appearance_start_at AND appearance_start_at < appearance_end_at),
  CHECK ((slide_status = 'known' AND slide_due_at IS NOT NULL AND slide_due_at >= accepted_at AND slide_due_at < appearance_start_at)
      OR (slide_status <> 'known' AND slide_due_at IS NULL)),
  CHECK ((venue_status = 'known' AND venue_name IS NOT NULL AND venue_address IS NOT NULL)
      OR (venue_status = 'pending' AND venue_name IS NULL AND venue_address IS NULL)),
  CHECK ((ticket_status = 'ready' AND ticket_ref IS NOT NULL)
      OR (ticket_status <> 'ready' AND ticket_ref IS NULL)),
  CHECK (follow_up_at > accepted_at AND follow_up_at <= appearance_end_at + interval '30 days')
);

CREATE OR REPLACE FUNCTION public.lm_talk_timeline_require_accepted_talk()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.lm_event_participations p
    WHERE p.participation_id = NEW.participation_id AND p.tenant_id = NEW.tenant_id
      AND p.kind = 'talk_application' AND p.state = 'accepted'
  ) THEN
    RAISE EXCEPTION 'talk timeline requires accepted talk_application';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_talk_timeline_accepted_gate ON public.lm_talk_timeline_snapshots;
CREATE TRIGGER lm_talk_timeline_accepted_gate
BEFORE INSERT ON public.lm_talk_timeline_snapshots
FOR EACH ROW EXECUTE FUNCTION public.lm_talk_timeline_require_accepted_talk();

CREATE OR REPLACE FUNCTION public.lm_talk_timeline_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'talk timeline snapshots are immutable';
END;
$$;

DROP TRIGGER IF EXISTS lm_talk_timeline_immutable ON public.lm_talk_timeline_snapshots;
CREATE TRIGGER lm_talk_timeline_immutable
BEFORE UPDATE OR DELETE ON public.lm_talk_timeline_snapshots
FOR EACH ROW EXECUTE FUNCTION public.lm_talk_timeline_immutable();

CREATE OR REPLACE VIEW public.lm_talk_timeline_current AS
SELECT DISTINCT ON (tenant_id, participation_id) *
FROM public.lm_talk_timeline_snapshots
ORDER BY tenant_id, participation_id, created_at DESC, snapshot_id DESC;

CREATE INDEX IF NOT EXISTS lm_talk_timeline_tenant_current_idx
  ON public.lm_talk_timeline_snapshots (tenant_id, participation_id, created_at DESC);

ALTER TABLE public.lm_talk_timeline_snapshots ENABLE ROW LEVEL SECURITY;
