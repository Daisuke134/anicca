-- PANEL-0 additive, user-keyed control-center persistence.
CREATE TABLE IF NOT EXISTS public.lm_panel_preferences (
  uid text PRIMARY KEY REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  call_enabled boolean NOT NULL DEFAULT true,
  notifications_enabled boolean NOT NULL DEFAULT true,
  daily_automation_enabled boolean NOT NULL DEFAULT true,
  delegation_enabled boolean NOT NULL DEFAULT false,
  call_time_zone text NOT NULL DEFAULT 'Asia/Tokyo',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.lm_panel_command_receipts (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  chat_id text NOT NULL,
  idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 8 AND 128),
  request_hash text NOT NULL CHECK (length(request_hash) = 64),
  command_type text NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed')),
  result jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (uid, chat_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS public.lm_panel_oauth_states (
  state_hash text PRIMARY KEY CHECK (length(state_hash) = 64),
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  chat_id text NOT NULL,
  provider text NOT NULL CHECK (provider = 'calendar'),
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lm_panel_oauth_states_user_idx
  ON public.lm_panel_oauth_states (uid, chat_id, expires_at);

ALTER TABLE public.lm_panel_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_panel_command_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_panel_oauth_states ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.claim_lm_panel_oauth_state(
  p_state_hash text, p_uid text, p_chat_id text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE claimed_count integer;
BEGIN
  UPDATE public.lm_panel_oauth_states
     SET used_at = now()
   WHERE state_hash = p_state_hash
     AND uid = p_uid
     AND chat_id = p_chat_id
     AND provider = 'calendar'
     AND used_at IS NULL
     AND expires_at > now();
  GET DIAGNOSTICS claimed_count = ROW_COUNT;
  RETURN claimed_count = 1;
END;
$$;
REVOKE ALL ON FUNCTION public.claim_lm_panel_oauth_state(text, text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_lm_panel_oauth_state(text, text, text) TO service_role;
