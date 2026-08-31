-- CORE 8f: additive, tenant-scoped provenance for semantic calendar questions and
-- one-time Calendar OAuth grants. Existing event-id dedup remains for compatibility.

ALTER TABLE public.lm_ask_log
  ADD COLUMN IF NOT EXISTS semantic_key text,
  ADD COLUMN IF NOT EXISTS question_type text,
  ADD COLUMN IF NOT EXISTS question_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS answer_value text,
  ADD COLUMN IF NOT EXISTS answer_source text,
  ADD COLUMN IF NOT EXISTS answer_provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS telegram_chat_id text;

CREATE UNIQUE INDEX IF NOT EXISTS lm_ask_log_uid_semantic_key_key
  ON public.lm_ask_log (uid, semantic_key)
  WHERE semantic_key IS NOT NULL;

ALTER TABLE public.lm_ask_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_ask_log FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lm_ask_log TO service_role;

ALTER TABLE public.lm_user_locations
  ADD COLUMN IF NOT EXISTS source text;

CREATE TABLE IF NOT EXISTS public.lm_calendar_connect_nonces (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  purpose text NOT NULL CHECK (purpose = 'oauth'),
  nonce_hash text NOT NULL CHECK (length(nonce_hash) = 64),
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, purpose, nonce_hash)
);

CREATE INDEX IF NOT EXISTS lm_calendar_connect_nonces_expires_idx
  ON public.lm_calendar_connect_nonces (expires_at);

ALTER TABLE public.lm_calendar_connect_nonces ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_calendar_connect_nonces FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, DELETE ON TABLE public.lm_calendar_connect_nonces TO service_role;
