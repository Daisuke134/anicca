-- Task 11: repair the first-actor Telegram claim for installations that already ran
-- 2026-08-27-lm-panel-onboarding-reachability.sql. Keep the full RPC contract and
-- use the existing lm_users primary-key constraint as the unambiguous arbiter.

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

REVOKE ALL ON FUNCTION public.claim_lm_panel_telegram_init_v2(text,text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_telegram_init_v2(text,text,text) TO service_role;
