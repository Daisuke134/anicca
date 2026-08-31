-- BROWSER-AUTH-1 forward upgrade for production trace functions created before
-- the bounded authentication lifecycle stages existed.

CREATE OR REPLACE FUNCTION public.append_lm_browser_job_trace(
  p_job_id uuid,
  p_stage text,
  p_meta jsonb DEFAULT '{}'::jsonb
) RETURNS SETOF public.lm_browser_jobs
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_stage NOT IN (
    'claimed', 'discovery', 'selected', 'action_started',
    'action_observed', 'provider_readback',
    'auth_context_loaded', 'auth_context_saved', 'auth_context_invalidated',
    'telegram_sent',
    'evidence_sent', 'steel_released'
  ) THEN
    RAISE EXCEPTION 'invalid browser trace stage';
  END IF;
  IF jsonb_typeof(COALESCE(p_meta, '{}'::jsonb)) <> 'object'
    OR octet_length(COALESCE(p_meta, '{}'::jsonb)::text) > 8192 THEN
    RAISE EXCEPTION 'invalid browser trace metadata';
  END IF;

  RETURN QUERY
  UPDATE public.lm_browser_jobs
  SET trace = trace || jsonb_build_array(jsonb_build_object(
        'stage', p_stage,
        'at', clock_timestamp(),
        'meta', COALESCE(p_meta, '{}'::jsonb)
      )),
      updated_at = clock_timestamp()
  WHERE id = p_job_id
    AND jsonb_array_length(trace) < 100
  RETURNING *;
END
$$;
