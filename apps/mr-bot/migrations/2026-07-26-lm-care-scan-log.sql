-- 11a/11b runtime: the PHYSICAL organ scans by itself once per user per UTC day. This table is both
-- the durable daily claim (UNIQUE(uid, scan_day) — no in-memory counter, survives restarts, the
-- recordDailyComposioPoll precedent made atomic the claimWake way: a duplicate insert 409s) and the
-- auditable record of what the detector saw (abstention rows included — the honest common case).
-- Additive only: nothing existing is altered or dropped.
CREATE TABLE IF NOT EXISTS public.lm_care_scan_log (
  id bigserial PRIMARY KEY,
  uid text NOT NULL,
  scan_day date NOT NULL,
  scanned_at timestamptz NOT NULL DEFAULT now(),
  history_event_count integer NOT NULL DEFAULT 0 CHECK (history_event_count >= 0),
  detections jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- 11b chain result, filled in AFTER the detection row is durable: {category, anchors_used
  -- (presence booleans only — the raw home address never leaves lm_users), candidates,
  -- selected_provider_id, shortfall_reason}. chain_error records an isolated chain failure without
  -- losing the detection itself.
  chain jsonb,
  chain_error text,
  UNIQUE (uid, scan_day)
);

CREATE INDEX IF NOT EXISTS lm_care_scan_log_uid_scanned_at
  ON public.lm_care_scan_log (uid, scanned_at DESC);

-- Scan facts are append-only: the day's claim, what the calendar showed, and what was detected can
-- never be rewritten after the fact. Only the 11b chain columns may be filled in on the same row.
CREATE OR REPLACE FUNCTION public.lm_care_scan_log_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'lm_care_scan_log is append-only';
  END IF;
  IF NEW.uid IS DISTINCT FROM OLD.uid
     OR NEW.scan_day IS DISTINCT FROM OLD.scan_day
     OR NEW.scanned_at IS DISTINCT FROM OLD.scanned_at
     OR NEW.history_event_count IS DISTINCT FROM OLD.history_event_count
     OR NEW.detections IS DISTINCT FROM OLD.detections THEN
    RAISE EXCEPTION 'lm_care_scan_log is append-only (only chain/chain_error may be set)';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS lm_care_scan_log_guard ON public.lm_care_scan_log;
CREATE TRIGGER lm_care_scan_log_guard
  BEFORE UPDATE OR DELETE ON public.lm_care_scan_log
  FOR EACH ROW EXECUTE FUNCTION public.lm_care_scan_log_guard();

ALTER TABLE public.lm_care_scan_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_care_scan_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_care_scan_log TO service_role;
REVOKE DELETE ON TABLE public.lm_care_scan_log FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_care_scan_log_id_seq TO service_role;
