-- v1.9.1 newsletter + feedback pipeline

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
  id                BIGSERIAL PRIMARY KEY,
  email             TEXT NOT NULL,
  locale            TEXT NOT NULL DEFAULT 'en',
  device_id         TEXT UNIQUE NOT NULL,
  opt_in_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  opted_out_at      TIMESTAMPTZ NULL,
  last_sent_at      TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_email ON newsletter_subscribers (email);
CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_opted_out ON newsletter_subscribers (opted_out_at) WHERE opted_out_at IS NULL;

CREATE TABLE IF NOT EXISTS feedback_log (
  id            BIGSERIAL PRIMARY KEY,
  text          TEXT NOT NULL,
  locale        TEXT NOT NULL DEFAULT 'en',
  app_user_id   TEXT,
  app_version   TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_feedback_log_created_at ON feedback_log (created_at);

CREATE TABLE IF NOT EXISTS failed_resend_calls (
  id            BIGSERIAL PRIMARY KEY,
  call_type     TEXT NOT NULL,
  payload_json  JSONB NOT NULL,
  error         TEXT NOT NULL,
  attempted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
