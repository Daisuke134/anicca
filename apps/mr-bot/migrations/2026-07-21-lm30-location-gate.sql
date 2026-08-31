CREATE TABLE IF NOT EXISTS lm_user_locations (
  uid text PRIMARY KEY,
  latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
  longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
  telegram_message_id text NOT NULL,
  observed_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_user_locations_expires_idx
  ON lm_user_locations (expires_at);

CREATE TABLE IF NOT EXISTS lm_late_notice_log (
  uid text NOT NULL,
  event_key text NOT NULL,
  claimed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, event_key)
);

ALTER TABLE lm_user_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE lm_late_notice_log ENABLE ROW LEVEL SECURITY;
