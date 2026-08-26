-- Task 6: one live Calendar consent state per verified panel tenant.
-- Existing lm_panel_oauth_states remains the sole OAuth-state table; raw state values are never stored.

DELETE FROM public.lm_panel_oauth_states
 WHERE used_at IS NOT NULL OR expires_at <= now();

WITH ranked AS (
  SELECT state_hash,
         row_number() OVER (
           PARTITION BY uid, chat_id, provider
           ORDER BY created_at DESC, state_hash DESC
         ) AS position
    FROM public.lm_panel_oauth_states
   WHERE used_at IS NULL
)
DELETE FROM public.lm_panel_oauth_states AS state
 WHERE state.state_hash IN (SELECT state_hash FROM ranked WHERE position > 1);

CREATE UNIQUE INDEX IF NOT EXISTS lm_panel_oauth_states_live_scope_idx
  ON public.lm_panel_oauth_states (uid, chat_id, provider)
  WHERE used_at IS NULL;

CREATE OR REPLACE FUNCTION public.create_lm_panel_oauth_state(
  p_state_hash text,
  p_uid text,
  p_chat_id text,
  p_provider text,
  p_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF p_state_hash IS NULL OR p_state_hash !~ '^[a-f0-9]{64}$'
     OR p_uid IS NULL OR p_uid = ''
     OR p_chat_id IS NULL OR p_chat_id = ''
     OR p_provider IS DISTINCT FROM 'calendar'
     OR p_expires_at IS NULL OR p_expires_at <= now() THEN
    RETURN false;
  END IF;

  DELETE FROM public.lm_panel_oauth_states
   WHERE uid = p_uid
     AND chat_id = p_chat_id
     AND provider = p_provider
     AND (used_at IS NOT NULL OR expires_at <= now());

  BEGIN
    INSERT INTO public.lm_panel_oauth_states(state_hash, uid, chat_id, provider, expires_at)
    VALUES (p_state_hash, p_uid, p_chat_id, p_provider, p_expires_at);
    RETURN true;
  EXCEPTION WHEN unique_violation THEN
    RETURN false;
  END;
END;
$$;

REVOKE ALL ON FUNCTION public.create_lm_panel_oauth_state(text, text, text, text, timestamptz)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_lm_panel_oauth_state(text, text, text, text, timestamptz)
  TO service_role;
