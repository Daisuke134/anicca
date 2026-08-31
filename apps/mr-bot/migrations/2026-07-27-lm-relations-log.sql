CREATE TABLE IF NOT EXISTS public.lm_relations_log (
  id bigserial PRIMARY KEY,
  uid text NOT NULL,
  day date NOT NULL,
  kind text NOT NULL CHECK (kind IN ('scan', 'suggestion_attempt', 'delivery')),
  interaction_count integer,
  detections jsonb,
  person_key text,
  attempted_at timestamptz,
  delivered_at timestamptz,
  telegram_message_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT lm_relations_log_kind_shape CHECK (
    (kind = 'scan' AND interaction_count IS NOT NULL AND detections IS NOT NULL
      AND person_key IS NULL AND attempted_at IS NULL AND delivered_at IS NULL)
    OR
    (kind = 'suggestion_attempt' AND interaction_count IS NULL AND detections IS NULL
      AND person_key IS NOT NULL AND attempted_at IS NOT NULL AND delivered_at IS NULL)
    OR
    (kind = 'delivery' AND interaction_count IS NULL AND detections IS NULL
      AND person_key IS NOT NULL AND attempted_at IS NULL AND delivered_at IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS lm_relations_log_uid_day_kind
  ON public.lm_relations_log (uid, day, kind);
CREATE INDEX IF NOT EXISTS lm_relations_log_uid_attempted_at
  ON public.lm_relations_log (uid, attempted_at DESC)
  WHERE kind = 'suggestion_attempt';

CREATE OR REPLACE FUNCTION public.lm_relations_log_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lm_relations_log is append-only';
END $$;

DROP TRIGGER IF EXISTS lm_relations_log_guard ON public.lm_relations_log;
CREATE TRIGGER lm_relations_log_guard
  BEFORE UPDATE OR DELETE ON public.lm_relations_log
  FOR EACH ROW EXECUTE FUNCTION public.lm_relations_log_guard();

DROP TRIGGER IF EXISTS lm_relations_log_truncate_guard ON public.lm_relations_log;
CREATE TRIGGER lm_relations_log_truncate_guard
  BEFORE TRUNCATE ON public.lm_relations_log
  FOR EACH STATEMENT EXECUTE FUNCTION public.lm_relations_log_guard();

ALTER TABLE public.lm_relations_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_relations_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_relations_log TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_relations_log FROM service_role;
REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE public.lm_relations_log FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_relations_log_id_seq TO service_role;
