-- Task 2: persist one server-owned three-day trial in the existing onboarding state.
ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS trial_expires_at timestamptz;

CREATE OR REPLACE FUNCTION public.lm_panel_onboarding_step(
  p_stored_stage text,
  p_name text,
  p_calendar_provider text,
  p_home_address text,
  p_phone text,
  p_notifications_enabled boolean,
  p_paid boolean
) RETURNS text
LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE stage text := lower(coalesce(nullif(trim(p_stored_stage), ''), 'calendar'));
BEGIN
  IF nullif(trim(coalesce(p_name, '')), '') IS NULL THEN RETURN 'name'; END IF;
  IF p_calendar_provider IS DISTINCT FROM 'composio_gcal' THEN RETURN 'calendar'; END IF;
  IF nullif(trim(coalesce(p_home_address, '')), '') IS NULL THEN RETURN 'home'; END IF;
  IF p_notifications_enabled IS NOT TRUE THEN RETURN 'notifications'; END IF;
  IF p_paid IS TRUE THEN RETURN 'dashboard'; END IF;
  IF stage IN ('done', 'dashboard', 'pay', 'payment', 'gmail') THEN RETURN 'dashboard'; END IF;
  IF nullif(trim(coalesce(p_phone, '')), '') IS NULL THEN RETURN 'phone'; END IF;
  RETURN 'call';
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_panel_onboarding_state(p_uid text, p_chat_id text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE u public.lm_users%ROWTYPE; p public.lm_panel_preferences%ROWTYPE; stage text; step text;
BEGIN
  SELECT * INTO u FROM public.lm_users WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT * INTO p FROM public.lm_panel_preferences WHERE uid = p_uid;
  stage := lower(coalesce(nullif(trim(u.tg_onboard_stage), ''), 'calendar'));
  step := public.lm_panel_onboarding_step(stage, u.name, u.calendar_provider, u.home_address, u.phone, coalesce(p.notifications_enabled, false), u.paid);
  RETURN jsonb_build_object(
    'step', step, 'stage', stage, 'name', nullif(trim(u.name), ''),
    'calendarConnected', u.calendar_provider = 'composio_gcal',
    'homeAddress', nullif(trim(u.home_address), ''), 'phone', nullif(trim(u.phone), ''),
    'notificationsEnabled', coalesce(p.notifications_enabled, false),
    'callEnabled', coalesce(p.call_enabled, false), 'paid', coalesce(u.paid, false),
    'trialExpiresAt', u.trial_expires_at,
    'trialActive', coalesce(u.trial_expires_at > now(), false)
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_panel_onboarding_transition(
  p_uid text, p_chat_id text, p_action text, p_payload jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE u public.lm_users%ROWTYPE; p public.lm_panel_preferences%ROWTYPE; step text; value text;
BEGIN
  SELECT * INTO u FROM public.lm_users WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'scope_mismatch'; END IF;
  SELECT * INTO p FROM public.lm_panel_preferences WHERE uid = p_uid FOR UPDATE;
  step := public.lm_panel_onboarding_step(u.tg_onboard_stage, u.name, u.calendar_provider, u.home_address, u.phone, coalesce(p.notifications_enabled, false), u.paid);
  IF p_action = 'name.save' THEN
    IF step <> 'name' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    value := trim(coalesce(p_payload->>'name', ''));
    IF value = '' OR char_length(value) > 120 THEN RAISE EXCEPTION 'invalid_name'; END IF;
    UPDATE public.lm_users SET name = value, tg_onboard_stage = 'calendar', updated_at = now() WHERE uid = p_uid;
  ELSIF p_action = 'home.save' THEN
    IF step <> 'home' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    value := trim(coalesce(p_payload->>'home_address', p_payload->>'homeAddress', ''));
    IF value = '' OR char_length(value) > 240 THEN RAISE EXCEPTION 'invalid_home_address'; END IF;
    UPDATE public.lm_users SET home_address = value, tg_onboard_stage = 'notifications', updated_at = now() WHERE uid = p_uid;
  ELSIF p_action = 'notifications.enable' THEN
    IF step <> 'notifications' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    INSERT INTO public.lm_panel_preferences(uid, notifications_enabled, call_enabled)
      VALUES (p_uid, true, false)
      ON CONFLICT (uid) DO UPDATE SET notifications_enabled = true, call_enabled = false, updated_at = now();
    UPDATE public.lm_users
    SET tg_onboard_stage = 'phone',
        trial_expires_at = coalesce(trial_expires_at, now() + interval '3 days'),
        updated_at = now()
    WHERE uid = p_uid;
  ELSIF p_action = 'phone.save' THEN
    IF step <> 'phone' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    value := trim(coalesce(p_payload->>'phone', ''));
    IF value !~ '^\+[1-9][0-9]{7,14}$' THEN RAISE EXCEPTION 'invalid_phone'; END IF;
    UPDATE public.lm_users SET phone = value, tg_onboard_stage = 'call', updated_at = now() WHERE uid = p_uid;
    INSERT INTO public.lm_panel_preferences(uid, call_enabled) VALUES (p_uid, false)
      ON CONFLICT (uid) DO UPDATE SET call_enabled = false, updated_at = now();
  ELSIF p_action = 'phone.skip' THEN
    IF step <> 'phone' OR nullif(trim(coalesce(u.phone, '')), '') IS NOT NULL THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    UPDATE public.lm_users SET tg_onboard_stage = 'done', updated_at = now() WHERE uid = p_uid;
    INSERT INTO public.lm_panel_preferences(uid, call_enabled) VALUES (p_uid, false)
      ON CONFLICT (uid) DO UPDATE SET call_enabled = false, updated_at = now();
  ELSIF p_action = 'call.enable' THEN
    IF step <> 'call' OR nullif(trim(coalesce(u.phone, '')), '') IS NULL THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    INSERT INTO public.lm_panel_preferences(uid, call_enabled) VALUES (p_uid, true)
      ON CONFLICT (uid) DO UPDATE SET call_enabled = true, updated_at = now();
    UPDATE public.lm_users SET tg_onboard_stage = 'done', updated_at = now() WHERE uid = p_uid;
  ELSIF p_action = 'call.skip' THEN
    IF step <> 'call' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    INSERT INTO public.lm_panel_preferences(uid, call_enabled) VALUES (p_uid, false)
      ON CONFLICT (uid) DO UPDATE SET call_enabled = false, updated_at = now();
    UPDATE public.lm_users SET tg_onboard_stage = 'done', updated_at = now() WHERE uid = p_uid;
  ELSIF p_action = 'payment.skip' THEN
    IF step <> 'payment' THEN RAISE EXCEPTION 'onboarding_conflict'; END IF;
    UPDATE public.lm_users SET tg_onboard_stage = 'done', updated_at = now() WHERE uid = p_uid;
  ELSE
    RAISE EXCEPTION 'invalid_onboarding_action';
  END IF;
  RETURN public.lm_panel_onboarding_state(p_uid, p_chat_id);
END;
$$;

REVOKE ALL ON FUNCTION public.lm_panel_onboarding_step(text,text,text,text,text,boolean,boolean) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_panel_onboarding_state(text,text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_panel_onboarding_transition(text,text,text,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_panel_onboarding_state(text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.lm_panel_onboarding_transition(text,text,text,jsonb) TO service_role;
