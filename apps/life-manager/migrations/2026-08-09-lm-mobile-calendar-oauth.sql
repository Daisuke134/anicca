-- Life Manager mobile Calendar OAuth repair (additive follow-up).
--
-- Connect Link owns the provider consent. The mobile callback carries only the
-- server-created state plus Composio's exact connected account ID; raw provider
-- identities never enter this database.

ALTER TABLE public.lm_mobile_oauth_states
  ADD COLUMN IF NOT EXISTS composio_user_id text,
  ADD COLUMN IF NOT EXISTS connected_account_id text,
  ADD COLUMN IF NOT EXISTS auth_config_id text;

ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS calendar_composio_user_id text;

CREATE TABLE IF NOT EXISTS public.lm_mobile_calendar_connections (
  provider text NOT NULL DEFAULT 'google_calendar',
  provider_subject_hash text NOT NULL CHECK (length(provider_subject_hash) = 64),
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  composio_user_id text NOT NULL,
  connected_account_id text NOT NULL,
  auth_config_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (provider, provider_subject_hash),
  UNIQUE (provider, uid)
);

CREATE INDEX IF NOT EXISTS lm_mobile_calendar_connections_uid_idx
  ON public.lm_mobile_calendar_connections (uid);

ALTER TABLE public.lm_mobile_calendar_connections ENABLE ROW LEVEL SECURITY;

-- The old claim function remains available to the Telegram/panel rolling path.
-- This v2 claim is intentionally callback-fact-only: no client identity is
-- accepted as an ownership predicate, and the UPDATE makes replay impossible.
CREATE OR REPLACE FUNCTION public.claim_lm_mobile_oauth_state_v2(p_state_hash text)
RETURNS TABLE(
  state_hash text,
  uid text,
  subject_hash text,
  provider text,
  redirect_uri text,
  expires_at timestamptz,
  used_at timestamptz,
  composio_user_id text,
  connected_account_id text,
  auth_config_id text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE public.lm_mobile_oauth_states AS s
     SET used_at = now()
   WHERE s.state_hash = p_state_hash
     AND s.used_at IS NULL
     AND s.expires_at > now()
  RETURNING s.state_hash, s.uid, s.subject_hash, s.provider, s.redirect_uri,
            s.expires_at, s.used_at, s.composio_user_id, s.connected_account_id,
            s.auth_config_id;
END;
$$;

-- Existing provider subject -> stable Life Manager UID is the identity map.
-- ON CONFLICT preserves the original opaque UID while refreshing routing facts
-- for a re-connect. The unique provider/uid constraint rejects two provider
-- identities being silently merged into one Life Manager account.
CREATE OR REPLACE FUNCTION public.link_lm_mobile_calendar_identity(
  p_provider text,
  p_provider_subject_hash text,
  p_uid text,
  p_composio_user_id text,
  p_connected_account_id text,
  p_auth_config_id text,
  p_product_locale text DEFAULT 'en'
)
RETURNS TABLE(uid text, product_locale text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE mapped_uid text;
DECLARE mapped_locale text;
BEGIN
  IF p_provider IS NULL OR p_provider <> 'google_calendar'
     OR p_provider_subject_hash IS NULL OR length(p_provider_subject_hash) <> 64
     OR p_uid IS NULL OR p_uid !~ '^lm_[A-Za-z0-9_-]+$'
     OR p_composio_user_id IS NULL OR p_connected_account_id IS NULL OR p_auth_config_id IS NULL
  THEN
    RAISE EXCEPTION 'mobile calendar identity facts invalid' USING ERRCODE = '22023';
  END IF;

  SELECT c.uid INTO mapped_uid
    FROM public.lm_mobile_calendar_connections AS c
   WHERE c.provider = p_provider AND c.provider_subject_hash = p_provider_subject_hash
   FOR UPDATE;

  IF mapped_uid IS NULL THEN
    INSERT INTO public.lm_users(
      uid, product_locale, calls_enabled, calendar_status,
      calendar_provider, gmail_account_id, calendar_composio_user_id
    ) VALUES (
      p_uid, CASE WHEN p_product_locale IN ('en', 'ja') THEN p_product_locale ELSE 'en' END,
      false, 'connected', 'composio_gcal', p_connected_account_id, p_composio_user_id
    ) ON CONFLICT (uid) DO UPDATE SET
      calendar_status = 'connected', calendar_provider = 'composio_gcal',
      gmail_account_id = EXCLUDED.gmail_account_id,
      calendar_composio_user_id = EXCLUDED.calendar_composio_user_id,
      updated_at = now();

    INSERT INTO public.lm_mobile_calendar_connections(
      provider, provider_subject_hash, uid, composio_user_id,
      connected_account_id, auth_config_id
    ) VALUES (
      p_provider, p_provider_subject_hash, p_uid, p_composio_user_id,
      p_connected_account_id, p_auth_config_id
    );
    mapped_uid := p_uid;
  ELSE
    UPDATE public.lm_mobile_calendar_connections
       SET composio_user_id = p_composio_user_id,
           connected_account_id = p_connected_account_id,
           auth_config_id = p_auth_config_id,
           updated_at = now()
     WHERE provider = p_provider AND provider_subject_hash = p_provider_subject_hash;
    UPDATE public.lm_users
       SET calendar_status = 'connected', calendar_provider = 'composio_gcal',
           gmail_account_id = p_connected_account_id,
           calendar_composio_user_id = p_composio_user_id,
           updated_at = now()
     WHERE uid = mapped_uid;
  END IF;

  SELECT u.product_locale INTO mapped_locale FROM public.lm_users AS u WHERE u.uid = mapped_uid;
  RETURN QUERY SELECT mapped_uid, COALESCE(mapped_locale, 'en');
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lm_mobile_oauth_state_v2(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.link_lm_mobile_calendar_identity(text, text, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_oauth_state_v2(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.link_lm_mobile_calendar_identity(text, text, text, text, text, text, text) TO service_role;
