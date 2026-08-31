ALTER TABLE public.lm_panel_sessions
  ADD COLUMN IF NOT EXISTS family_id uuid DEFAULT gen_random_uuid(),
  ADD COLUMN IF NOT EXISTS idle_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS absolute_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS rotated_at timestamptz,
  ADD COLUMN IF NOT EXISTS revoked_at timestamptz,
  ADD COLUMN IF NOT EXISTS pending_child_hash text,
  ADD COLUMN IF NOT EXISTS pending_child_seed text,
  ADD COLUMN IF NOT EXISTS rotation_grace_until timestamptz;

UPDATE public.lm_panel_sessions SET revoked_at = COALESCE(revoked_at, now()) WHERE idle_expires_at IS NULL;
ALTER TABLE public.lm_panel_sessions ENABLE ROW LEVEL SECURITY;

DROP FUNCTION IF EXISTS public.resolve_lm_panel_session(text,text);
CREATE OR REPLACE FUNCTION public.resolve_lm_panel_session(p_session_hash text, p_child_hash text, p_child_seed text)
RETURNS TABLE(uid text, chat_id text, rotated boolean, accepted_child_hash text, accepted_child_seed text, family_id uuid, cookie_max_age integer)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE s public.lm_panel_sessions%ROWTYPE; bound_chat text;
BEGIN
  SELECT * INTO s FROM public.lm_panel_sessions WHERE session_hash = p_session_hash FOR UPDATE;
  IF NOT FOUND OR length(p_child_hash) <> 64 OR length(p_child_seed) <> 64 THEN RETURN; END IF;
  SELECT telegram_chat_id::text INTO bound_chat FROM public.lm_users WHERE lm_users.uid = s.uid;
  IF bound_chat IS DISTINCT FROM s.chat_id THEN
    UPDATE public.lm_panel_sessions SET revoked_at = now(), pending_child_hash = NULL, pending_child_seed = NULL, rotation_grace_until = NULL WHERE lm_panel_sessions.family_id = s.family_id;
    RETURN;
  END IF;

  -- Concurrent requests presenting the same pre-rotation cookie all receive the
  -- first committed seed. The application deterministically derives that one raw
  -- child; the database retains only its hash plus the non-bearer seed digest.
  IF s.revoked_at IS NOT NULL AND s.rotation_grace_until > now() AND s.pending_child_hash IS NOT NULL AND s.pending_child_seed IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.lm_panel_sessions child WHERE child.session_hash = s.pending_child_hash AND child.family_id = s.family_id AND child.revoked_at IS NULL AND child.idle_expires_at > now()) THEN
      UPDATE public.lm_panel_sessions SET expires_at = now() + interval '30 days', idle_expires_at = now() + interval '30 days'
        WHERE session_hash = s.pending_child_hash AND revoked_at IS NULL;
      RETURN QUERY SELECT s.uid, s.chat_id, true, s.pending_child_hash, s.pending_child_seed, s.family_id, 2592000;
    END IF;
    RETURN;
  END IF;
  IF s.revoked_at IS NOT NULL THEN RETURN; END IF;

  -- Browser storage removal stops activity; the idle boundary then revokes the
  -- whole family. There is deliberately no unconditional absolute lifetime.
  IF s.idle_expires_at <= now() THEN
    UPDATE public.lm_panel_sessions SET revoked_at = now(), pending_child_hash = NULL, pending_child_seed = NULL, rotation_grace_until = NULL
      WHERE lm_panel_sessions.family_id = s.family_id;
    RETURN;
  END IF;

  IF s.rotated_at IS NULL AND s.created_at <= now() - interval '12 hours' THEN
    UPDATE public.lm_panel_sessions SET rotated_at = now(), revoked_at = now(), pending_child_hash = p_child_hash, pending_child_seed = p_child_seed, rotation_grace_until = now() + interval '2 minutes' WHERE session_hash = p_session_hash;
    INSERT INTO public.lm_panel_sessions(session_hash, uid, chat_id, family_id, expires_at, idle_expires_at, absolute_expires_at)
      VALUES (p_child_hash, s.uid, s.chat_id, s.family_id, now() + interval '30 days', now() + interval '30 days', NULL);
    RETURN QUERY SELECT s.uid, s.chat_id, true, p_child_hash, p_child_seed, s.family_id, 2592000; RETURN;
  END IF;

  UPDATE public.lm_panel_sessions SET expires_at = now() + interval '30 days', idle_expires_at = now() + interval '30 days'
    WHERE session_hash = p_session_hash AND revoked_at IS NULL;
  RETURN QUERY SELECT s.uid, s.chat_id, false, NULL::text, NULL::text, s.family_id, 2592000;
END $$;

CREATE OR REPLACE FUNCTION public.revoke_lm_panel_session(p_session_hash text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE target_family uuid;
BEGIN
  SELECT family_id INTO target_family FROM public.lm_panel_sessions WHERE session_hash = p_session_hash FOR UPDATE;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE public.lm_panel_sessions SET revoked_at = now(), pending_child_hash = NULL, pending_child_seed = NULL, rotation_grace_until = NULL WHERE family_id = target_family;
  RETURN true;
END $$;

CREATE OR REPLACE FUNCTION public.revoke_lm_panel_sessions_for_tenant(p_uid text, p_chat_id text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$ BEGIN UPDATE public.lm_panel_sessions SET revoked_at = now(), pending_child_hash = NULL, pending_child_seed = NULL, rotation_grace_until = NULL WHERE uid = p_uid AND chat_id = p_chat_id; RETURN FOUND; END $$;

REVOKE ALL ON FUNCTION public.resolve_lm_panel_session(text,text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.revoke_lm_panel_session(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.revoke_lm_panel_sessions_for_tenant(text,text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_lm_panel_session(text,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.revoke_lm_panel_session(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.revoke_lm_panel_sessions_for_tenant(text,text) TO service_role;

CREATE OR REPLACE FUNCTION public.mutate_lm_panel_preferences(p_uid text, p_chat_id text, p_patch jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE result jsonb;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.lm_users WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id) THEN RAISE EXCEPTION 'scope_mismatch'; END IF;
  INSERT INTO public.lm_panel_preferences(uid) VALUES (p_uid) ON CONFLICT (uid) DO NOTHING;
  UPDATE public.lm_panel_preferences SET
    call_enabled = COALESCE((p_patch->>'call_enabled')::boolean, call_enabled),
    notifications_enabled = COALESCE((p_patch->>'notifications_enabled')::boolean, notifications_enabled),
    daily_automation_enabled = COALESCE((p_patch->>'daily_automation_enabled')::boolean, daily_automation_enabled),
    call_time_zone = COALESCE(p_patch->>'call_time_zone', call_time_zone), updated_at = now()
  WHERE uid = p_uid RETURNING to_jsonb(lm_panel_preferences.*) INTO result;
  RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.mutate_lm_panel_user(p_uid text, p_chat_id text, p_patch jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE result jsonb;
BEGIN
  UPDATE public.lm_users SET call_language = COALESCE(p_patch->>'call_language', call_language), wake_policy = COALESCE(p_patch->>'wake_policy', wake_policy)
  WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id RETURNING to_jsonb(lm_users.*) INTO result;
  IF result IS NULL THEN RAISE EXCEPTION 'scope_mismatch'; END IF; RETURN result;
END $$;
REVOKE ALL ON FUNCTION public.mutate_lm_panel_preferences(text,text,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.mutate_lm_panel_user(text,text,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mutate_lm_panel_preferences(text,text,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.mutate_lm_panel_user(text,text,jsonb) TO service_role;
