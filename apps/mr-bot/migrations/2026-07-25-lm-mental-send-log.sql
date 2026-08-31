-- MEN-c: the MENTAL organ needs to know what it already said today, or the daily cap and the minimum
-- gap are unenforceable across restarts. Additive only: nothing existing is altered or dropped.
CREATE TABLE IF NOT EXISTS lm_mental_send_log (
  id bigserial PRIMARY KEY,
  uid text NOT NULL,
  trigger text NOT NULL CHECK (trigger IN ('pre_event', 'between_events', 'pre_sleep')),
  telegram_message_id text NOT NULL,
  sent_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_mental_send_log_uid_sent_at ON lm_mental_send_log (uid, sent_at DESC);

ALTER TABLE lm_mental_send_log ENABLE ROW LEVEL SECURITY;
