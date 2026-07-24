-- PANEL-1 canonical panel authentication. Additive and hash-only.

CREATE TABLE IF NOT EXISTS public.lm_panel_telegram_replays (
  init_hash text PRIMARY KEY CHECK (length(init_hash) = 64),
  actor_id text NOT NULL,
  claimed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_panel_telegram_replays_claimed_idx
  ON public.lm_panel_telegram_replays (claimed_at);

CREATE TABLE IF NOT EXISTS public.lm_panel_device_challenges (
  challenge_hash text PRIMARY KEY CHECK (length(challenge_hash) = 64),
  code_hash text NOT NULL UNIQUE CHECK (length(code_hash) = 64),
  expires_at timestamptz NOT NULL,
  confirmed_uid text REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  confirmed_chat_id text,
  confirmed_at timestamptz,
  exchanged_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_panel_device_challenges_expires_idx
  ON public.lm_panel_device_challenges (expires_at);

ALTER TABLE public.lm_panel_telegram_replays ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_panel_device_challenges ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_panel_telegram_replays FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.lm_panel_device_challenges FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lm_panel_telegram_replays TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lm_panel_device_challenges TO service_role;

CREATE OR REPLACE FUNCTION public.claim_lm_panel_telegram_init(p_init_hash text, p_actor_id text)
RETURNS TABLE(status text, uid text, chat_id text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE target_uid text; matches integer;
BEGIN
  IF p_init_hash !~ '^[a-f0-9]{64}$' OR p_actor_id IS NULL OR p_actor_id = '' THEN
    RETURN QUERY SELECT 'unknown_actor'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  SELECT count(*), min(lm_users.uid) INTO matches, target_uid
    FROM public.lm_users WHERE telegram_chat_id::text = p_actor_id;
  IF matches <> 1 THEN
    RETURN QUERY SELECT 'unknown_actor'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  INSERT INTO public.lm_panel_telegram_replays(init_hash, actor_id)
    VALUES (p_init_hash, p_actor_id) ON CONFLICT DO NOTHING;
  IF NOT FOUND THEN
    RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  RETURN QUERY SELECT 'claimed'::text, target_uid, p_actor_id;
END $$;

CREATE OR REPLACE FUNCTION public.claim_lm_panel_device_code(p_code_hash text, p_uid text, p_chat_id text)
RETURNS TABLE(status text, uid text, chat_id text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE challenge public.lm_panel_device_challenges%ROWTYPE; matches integer;
BEGIN
  IF p_code_hash !~ '^[a-f0-9]{64}$' THEN
    RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  SELECT count(*) INTO matches FROM public.lm_users
    WHERE lm_users.uid = p_uid AND telegram_chat_id::text = p_chat_id;
  IF matches <> 1 THEN
    RETURN QUERY SELECT 'scope_mismatch'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  SELECT * INTO challenge FROM public.lm_panel_device_challenges
    WHERE code_hash = p_code_hash FOR UPDATE;
  IF NOT FOUND THEN
    RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::text;
  ELSIF challenge.expires_at <= now() THEN
    RETURN QUERY SELECT 'expired'::text, NULL::text, NULL::text;
  ELSIF challenge.confirmed_at IS NOT NULL THEN
    RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text;
  ELSE
    UPDATE public.lm_panel_device_challenges SET
      confirmed_uid = p_uid, confirmed_chat_id = p_chat_id, confirmed_at = now()
      WHERE challenge_hash = challenge.challenge_hash AND confirmed_at IS NULL;
    IF FOUND THEN RETURN QUERY SELECT 'claimed'::text, p_uid, p_chat_id;
    ELSE RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text;
    END IF;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.exchange_lm_panel_device_challenge(p_challenge_hash text)
RETURNS TABLE(status text, uid text, chat_id text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE challenge public.lm_panel_device_challenges%ROWTYPE;
BEGIN
  IF p_challenge_hash !~ '^[a-f0-9]{64}$' THEN
    RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::text;
    RETURN;
  END IF;
  SELECT * INTO challenge FROM public.lm_panel_device_challenges
    WHERE challenge_hash = p_challenge_hash FOR UPDATE;
  IF NOT FOUND THEN
    RETURN QUERY SELECT 'not_found'::text, NULL::text, NULL::text;
  ELSIF challenge.expires_at <= now() THEN
    RETURN QUERY SELECT 'expired'::text, NULL::text, NULL::text;
  ELSIF challenge.exchanged_at IS NOT NULL THEN
    RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text;
  ELSIF challenge.confirmed_at IS NULL OR challenge.confirmed_uid IS NULL OR challenge.confirmed_chat_id IS NULL THEN
    RETURN QUERY SELECT 'pending'::text, NULL::text, NULL::text;
  ELSE
    UPDATE public.lm_panel_device_challenges SET exchanged_at = now()
      WHERE challenge_hash = challenge.challenge_hash AND exchanged_at IS NULL;
    IF FOUND THEN RETURN QUERY SELECT 'claimed'::text, challenge.confirmed_uid, challenge.confirmed_chat_id;
    ELSE RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text;
    END IF;
  END IF;
END $$;

REVOKE ALL ON FUNCTION public.claim_lm_panel_telegram_init(text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_panel_device_code(text,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.exchange_lm_panel_device_challenge(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_telegram_init(text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_device_code(text,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.exchange_lm_panel_device_challenge(text) TO service_role;
