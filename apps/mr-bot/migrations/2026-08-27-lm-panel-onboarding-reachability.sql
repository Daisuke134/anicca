-- Task 7A R1A: make verified Telegram onboarding reachable without a legacy browser identity.
-- This migration only replaces existing RPCs; lm_users and lm_panel_preferences remain the SSOT.

CREATE OR REPLACE FUNCTION public.claim_lm_panel_telegram_init_v2(p_init_hash text, p_actor_id text, p_profile_name text)
RETURNS TABLE(status text, uid text, chat_id text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE claimed_count integer; matching_count integer; target_uid text; bound_uid text; profile_name text;
BEGIN
  IF p_init_hash IS NULL OR p_init_hash !~ '^[a-f0-9]{64}$'
     OR p_actor_id IS NULL OR p_actor_id !~ '^[1-9][0-9]{0,19}$' THEN
    RETURN QUERY SELECT 'unknown_actor'::text, NULL::text, NULL::text; RETURN;
  END IF;

  INSERT INTO public.lm_panel_telegram_replays(init_hash, actor_id)
    VALUES (p_init_hash, p_actor_id) ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS claimed_count = ROW_COUNT;
  IF claimed_count <> 1 THEN
    RETURN QUERY SELECT 'replayed'::text, NULL::text, NULL::text; RETURN;
  END IF;

  IF char_length(trim(coalesce(p_profile_name, ''))) > 120 THEN RAISE EXCEPTION 'invalid_profile_name'; END IF;
  profile_name := trim(coalesce(p_profile_name, ''));

  -- Existing rows win (including rows created by the older Telegram flow). A first-time actor uses
  -- a deterministic UID; the primary-key conflict serializes concurrent first claims for that actor.
  SELECT count(*) INTO matching_count FROM public.lm_users AS u
   WHERE u.telegram_chat_id::text = p_actor_id;
  IF matching_count > 1 THEN RAISE EXCEPTION 'telegram_tenant_conflict'; END IF;
  SELECT u.uid INTO bound_uid FROM public.lm_users AS u
   WHERE u.telegram_chat_id::text = p_actor_id ORDER BY u.uid LIMIT 1 FOR UPDATE;
  IF bound_uid IS NULL THEN
    target_uid := 'lm_tg_' || md5(p_actor_id);
    INSERT INTO public.lm_users(uid, telegram_chat_id, name, tg_onboard_stage)
      VALUES (target_uid, p_actor_id, NULLIF(profile_name, ''), 'calendar') ON CONFLICT ON CONSTRAINT lm_users_pkey DO NOTHING;
    SELECT count(*) INTO matching_count FROM public.lm_users AS u
      WHERE u.telegram_chat_id::text = p_actor_id;
    IF matching_count > 1 THEN RAISE EXCEPTION 'telegram_tenant_conflict'; END IF;
    SELECT u.uid INTO bound_uid FROM public.lm_users AS u
      WHERE u.telegram_chat_id::text = p_actor_id ORDER BY u.uid LIMIT 1 FOR UPDATE;
    IF bound_uid IS NULL THEN RAISE EXCEPTION 'telegram_tenant_conflict'; END IF;
  END IF;
  UPDATE public.lm_users AS u SET
    name = CASE WHEN name IS NULL OR trim(name) = '' THEN NULLIF(trim(profile_name), '') ELSE name END,
    tg_onboard_stage = COALESCE(tg_onboard_stage, 'calendar'), updated_at = now()
    WHERE u.uid = bound_uid;
  RETURN QUERY SELECT 'claimed'::text, bound_uid, p_actor_id;
END;
$$;

-- Preserve the old service-role entrypoint for callers that have no profile display data.
CREATE OR REPLACE FUNCTION public.claim_lm_panel_telegram_init(p_init_hash text, p_actor_id text)
RETURNS TABLE(status text, uid text, chat_id text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY SELECT * FROM public.claim_lm_panel_telegram_init_v2(p_init_hash, p_actor_id, NULL);
END;
$$;

CREATE OR REPLACE FUNCTION public.sync_lm_panel_calendar_status(p_uid text, p_chat_id text, p_status text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE binding_uid text;
BEGIN
  SELECT uid INTO binding_uid FROM public.lm_users
   WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id FOR UPDATE;
  IF binding_uid IS NULL THEN RAISE EXCEPTION 'scope_mismatch'; END IF;
  IF p_status = 'ACTIVE' THEN
    UPDATE public.lm_users SET calendar_provider = 'composio_gcal', updated_at = now() WHERE uid = p_uid;
  ELSIF p_status IN ('MISSING', 'DISABLED', 'INACTIVE') THEN
    UPDATE public.lm_users SET calendar_provider = NULL, updated_at = now()
      WHERE uid = p_uid AND calendar_provider = 'composio_gcal';
  ELSE
    RAISE EXCEPTION 'calendar_status_unknown';
  END IF;
  RETURN true;
END;
$$;

-- The POST onboarding path must not commit a provider marker before a transition can reject. Both
-- operations therefore share this one transaction and the same tenant row lock.
CREATE OR REPLACE FUNCTION public.lm_panel_onboarding_transition_with_calendar(
  p_uid text, p_chat_id text, p_status text, p_action text, p_payload jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  PERFORM public.sync_lm_panel_calendar_status(p_uid, p_chat_id, p_status);
  RETURN public.lm_panel_onboarding_transition(p_uid, p_chat_id, p_action, p_payload);
END;
$$;

REVOKE ALL ON FUNCTION public.claim_lm_panel_telegram_init(text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_panel_telegram_init_v2(text,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.sync_lm_panel_calendar_status(text,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_panel_onboarding_transition_with_calendar(text,text,text,text,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_telegram_init(text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_telegram_init_v2(text,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.sync_lm_panel_calendar_status(text,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.lm_panel_onboarding_transition_with_calendar(text,text,text,text,jsonb) TO service_role;
