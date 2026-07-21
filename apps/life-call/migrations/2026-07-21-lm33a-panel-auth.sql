-- LM-33a panel authentication. Additive only; applied during Fable E2E.
-- Raw bearer values never enter the database: only their SHA-256 hex digests do.

CREATE TABLE IF NOT EXISTS public.lm_panel_tokens (
  token_hash text PRIMARY KEY CHECK (length(token_hash) = 64),
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  chat_id text NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_panel_tokens_expires_idx
  ON public.lm_panel_tokens (expires_at);

CREATE TABLE IF NOT EXISTS public.lm_panel_sessions (
  session_hash text PRIMARY KEY CHECK (length(session_hash) = 64),
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  chat_id text NOT NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_panel_sessions_expires_idx
  ON public.lm_panel_sessions (expires_at);

ALTER TABLE public.lm_panel_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_panel_sessions ENABLE ROW LEVEL SECURITY;

-- A single UPDATE both checks and burns the token. Concurrent requests cannot both
-- receive a row from RETURNING, unlike a SELECT followed by a separate UPDATE.
CREATE OR REPLACE FUNCTION public.claim_lm_panel_token(p_token_hash text)
RETURNS TABLE(uid text, chat_id text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_panel_tokens AS token
     SET used_at = now()
   WHERE token.token_hash = p_token_hash
     AND token.used_at IS NULL
     AND token.expires_at > now()
  RETURNING token.uid, token.chat_id;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lm_panel_token(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.claim_lm_panel_token(text) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_token(text) TO service_role;
