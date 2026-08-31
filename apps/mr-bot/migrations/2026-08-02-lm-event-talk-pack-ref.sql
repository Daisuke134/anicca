ALTER TABLE public.lm_event_participations
  ADD COLUMN IF NOT EXISTS talk_pack_ref text;

ALTER TABLE public.lm_event_participations
  DROP CONSTRAINT IF EXISTS lm_event_participations_talk_pack_ref_format;
ALTER TABLE public.lm_event_participations
  ADD CONSTRAINT lm_event_participations_talk_pack_ref_format CHECK (
    talk_pack_ref IS NULL
    OR talk_pack_ref ~ '^artifact://connector-talk-pack/sha256/[0-9a-f]{64}$'
  );

ALTER TABLE public.lm_event_participations
  DROP CONSTRAINT IF EXISTS lm_event_participations_talk_pack_kind;
ALTER TABLE public.lm_event_participations
  ADD CONSTRAINT lm_event_participations_talk_pack_kind CHECK (
    talk_pack_ref IS NULL OR kind = 'talk_application'
  );
