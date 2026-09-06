-- CLOUD-05: extend the existing tenant-scoped panel user mutation for post-onboarding profile edits.
-- Keep the historical row-shaped RPC result so existing callers do not change contract.
CREATE OR REPLACE FUNCTION public.mutate_lm_panel_user(
  p_uid text,
  p_chat_id text,
  p_patch jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  u public.lm_users%ROWTYPE;
  key text;
  home_value text;
  phone_value text;
  result jsonb;
BEGIN
  IF p_patch IS NULL OR jsonb_typeof(p_patch) <> 'object' OR p_patch = '{}'::jsonb THEN
    RAISE EXCEPTION 'invalid_profile_patch';
  END IF;

  FOR key IN SELECT jsonb_object_keys(p_patch)
  LOOP
    IF key NOT IN ('call_language', 'wake_policy', 'home_address', 'phone') THEN
      RAISE EXCEPTION 'invalid_profile_patch';
    END IF;
  END LOOP;

  SELECT * INTO u
  FROM public.lm_users
  WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'scope_mismatch'; END IF;

  IF p_patch ? 'call_language' THEN
    IF p_patch->>'call_language' NOT IN ('en', 'ja') THEN RAISE EXCEPTION 'invalid_call_language'; END IF;
    UPDATE public.lm_users
    SET call_language = p_patch->>'call_language', updated_at = now()
    WHERE uid = p_uid;
  END IF;

  IF p_patch ? 'wake_policy' THEN
    IF p_patch->>'wake_policy' NOT IN ('travel-only', 'all-events') THEN RAISE EXCEPTION 'invalid_wake_policy'; END IF;
    UPDATE public.lm_users
    SET wake_policy = p_patch->>'wake_policy', updated_at = now()
    WHERE uid = p_uid;
  END IF;

  IF p_patch ? 'home_address' THEN
    IF jsonb_typeof(p_patch->'home_address') <> 'string' THEN RAISE EXCEPTION 'invalid_home_address'; END IF;
    home_value := trim(p_patch->>'home_address');
    IF home_value = '' OR char_length(home_value) > 240 THEN RAISE EXCEPTION 'invalid_home_address'; END IF;
    UPDATE public.lm_users
    SET home_address = home_value, updated_at = now()
    WHERE uid = p_uid;
  END IF;

  IF p_patch ? 'phone' THEN
    IF p_patch->'phone' = 'null'::jsonb THEN
      phone_value := NULL;
    ELSE
      IF jsonb_typeof(p_patch->'phone') <> 'string' THEN RAISE EXCEPTION 'invalid_phone'; END IF;
      phone_value := trim(p_patch->>'phone');
      IF phone_value !~ '^\+[1-9][0-9]{7,14}$' THEN RAISE EXCEPTION 'invalid_phone'; END IF;
    END IF;
    UPDATE public.lm_users
    SET phone = phone_value, updated_at = now()
    WHERE uid = p_uid;
    IF phone_value IS NULL THEN
      INSERT INTO public.lm_panel_preferences(uid, call_enabled)
      VALUES (p_uid, false)
      ON CONFLICT (uid) DO UPDATE
      SET call_enabled = false, updated_at = now();
    END IF;
  END IF;

  SELECT to_jsonb(lm_users.*) INTO result
  FROM public.lm_users
  WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id;
  IF result IS NULL THEN RAISE EXCEPTION 'scope_mismatch'; END IF;
  RETURN result;
END;
$$;

REVOKE ALL ON FUNCTION public.mutate_lm_panel_user(text,text,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mutate_lm_panel_user(text,text,jsonb) TO service_role;
