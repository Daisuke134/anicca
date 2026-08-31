CREATE TABLE IF NOT EXISTS public.lm_automation_stacks (
  uid text NOT NULL CHECK (char_length(uid) BETWEEN 1 AND 200),
  stack_id text NOT NULL DEFAULT 'default' CHECK (stack_id = 'default'),
  name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
  desired_state text NOT NULL DEFAULT 'off' CHECK (desired_state IN ('off', 'on')),
  observed_state text NOT NULL DEFAULT 'stopped' CHECK (observed_state IN ('stopped', 'pending_start', 'running', 'pending_stop', 'error')),
  revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
  last_error_code text CHECK (last_error_code IS NULL OR char_length(last_error_code) BETWEEN 1 AND 120),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, stack_id)
);

CREATE TABLE IF NOT EXISTS public.lm_automation_stack_tools (
  uid text NOT NULL,
  stack_id text NOT NULL DEFAULT 'default',
  catalog_id text NOT NULL CHECK (char_length(catalog_id) BETWEEN 1 AND 280),
  source text NOT NULL CHECK (source IN ('mcp-registry', 'hugging-face')),
  name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  description text NOT NULL DEFAULT '' CHECK (char_length(description) <= 360),
  connection_kind text NOT NULL CHECK (connection_kind IN ('remote_mcp', 'hugging_face_mcp')),
  endpoint text NOT NULL CHECK (endpoint ~ '^https://'),
  source_url text NOT NULL CHECK (source_url ~ '^https://'),
  version text CHECK (version IS NULL OR char_length(version) <= 80),
  required_secrets jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(required_secrets) = 'array' AND octet_length(required_secrets::text) <= 2048),
  position integer NOT NULL CHECK (position BETWEEN 0 AND 11),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, stack_id, catalog_id),
  UNIQUE (uid, stack_id, position),
  FOREIGN KEY (uid, stack_id) REFERENCES public.lm_automation_stacks(uid, stack_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS lm_automation_stacks_desired_idx
  ON public.lm_automation_stacks (desired_state, observed_state, updated_at);

ALTER TABLE public.lm_automation_stacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_automation_stack_tools ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_automation_stacks, public.lm_automation_stack_tools FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.lm_automation_stacks, public.lm_automation_stack_tools TO service_role;

CREATE OR REPLACE FUNCTION public.replace_lm_automation_stack(
  p_uid text,
  p_chat_id text,
  p_name text,
  p_expected_revision bigint,
  p_tools jsonb
) RETURNS SETOF public.lm_automation_stacks
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_stack public.lm_automation_stacks%ROWTYPE;
  v_tool jsonb;
  v_position integer := 0;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.lm_users WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id) THEN
    RAISE EXCEPTION 'scope mismatch';
  END IF;
  IF p_name IS NULL OR char_length(p_name) NOT BETWEEN 1 AND 80 OR p_expected_revision < 0
    OR jsonb_typeof(p_tools) <> 'array' OR jsonb_array_length(p_tools) NOT BETWEEN 1 AND 12 THEN
    RAISE EXCEPTION 'automation input invalid';
  END IF;

  INSERT INTO public.lm_automation_stacks (uid, stack_id, name)
  VALUES (p_uid, 'default', p_name)
  ON CONFLICT (uid, stack_id) DO NOTHING;

  SELECT * INTO v_stack FROM public.lm_automation_stacks
  WHERE uid = p_uid AND stack_id = 'default'
  FOR UPDATE;
  IF v_stack.revision <> p_expected_revision THEN RAISE EXCEPTION 'automation revision conflict'; END IF;
  IF v_stack.desired_state <> 'off' OR v_stack.observed_state NOT IN ('stopped', 'error') THEN
    RAISE EXCEPTION 'automation must be off before editing';
  END IF;

  DELETE FROM public.lm_automation_stack_tools WHERE uid = p_uid AND stack_id = 'default';
  FOR v_tool IN SELECT value FROM jsonb_array_elements(p_tools)
  LOOP
    IF jsonb_typeof(v_tool) <> 'object'
      OR (v_tool->>'source') NOT IN ('mcp-registry', 'hugging-face')
      OR (v_tool->>'connection_kind') NOT IN ('remote_mcp', 'hugging_face_mcp')
      OR (v_tool->>'endpoint') !~ '^https://'
      OR (v_tool->>'source_url') !~ '^https://'
      OR char_length(COALESCE(v_tool->>'catalog_id', '')) NOT BETWEEN 1 AND 280
      OR char_length(COALESCE(v_tool->>'name', '')) NOT BETWEEN 1 AND 120 THEN
      RAISE EXCEPTION 'automation tool invalid';
    END IF;
    INSERT INTO public.lm_automation_stack_tools (
      uid, stack_id, catalog_id, source, name, description, connection_kind,
      endpoint, source_url, version, required_secrets, position
    ) VALUES (
      p_uid, 'default', v_tool->>'catalog_id', v_tool->>'source', v_tool->>'name',
      left(COALESCE(v_tool->>'description', ''), 360), v_tool->>'connection_kind',
      v_tool->>'endpoint', v_tool->>'source_url', NULLIF(v_tool->>'version', ''),
      COALESCE(v_tool->'required_secrets', '[]'::jsonb), v_position
    );
    v_position := v_position + 1;
  END LOOP;

  RETURN QUERY UPDATE public.lm_automation_stacks
  SET name = p_name, revision = revision + 1, observed_state = 'stopped',
      last_error_code = NULL, updated_at = clock_timestamp()
  WHERE uid = p_uid AND stack_id = 'default'
  RETURNING *;
END;
$$;

CREATE OR REPLACE FUNCTION public.toggle_lm_automation_stack(
  p_uid text,
  p_chat_id text,
  p_enabled boolean,
  p_expected_revision bigint,
  p_verified boolean
) RETURNS SETOF public.lm_automation_stacks
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_stack public.lm_automation_stacks%ROWTYPE;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.lm_users WHERE uid = p_uid AND telegram_chat_id::text = p_chat_id) THEN
    RAISE EXCEPTION 'scope mismatch';
  END IF;
  SELECT * INTO v_stack FROM public.lm_automation_stacks
  WHERE uid = p_uid AND stack_id = 'default'
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'automation stack missing'; END IF;
  IF v_stack.revision <> p_expected_revision THEN RAISE EXCEPTION 'automation revision conflict'; END IF;
  IF p_enabled AND NOT EXISTS (SELECT 1 FROM public.lm_automation_stack_tools WHERE uid = p_uid AND stack_id = 'default') THEN
    RAISE EXCEPTION 'automation tools missing';
  END IF;

  RETURN QUERY UPDATE public.lm_automation_stacks
  SET desired_state = CASE WHEN p_enabled THEN 'on' ELSE 'off' END,
      observed_state = CASE
        WHEN p_enabled AND p_verified THEN 'running'
        WHEN p_enabled THEN 'pending_start'
        ELSE 'stopped'
      END,
      revision = revision + 1,
      last_error_code = NULL,
      updated_at = clock_timestamp()
  WHERE uid = p_uid AND stack_id = 'default'
  RETURNING *;
END;
$$;

REVOKE ALL ON FUNCTION public.replace_lm_automation_stack(text,text,text,bigint,jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.toggle_lm_automation_stack(text,text,boolean,bigint,boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.replace_lm_automation_stack(text,text,text,bigint,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.toggle_lm_automation_stack(text,text,boolean,bigint,boolean) TO service_role;
