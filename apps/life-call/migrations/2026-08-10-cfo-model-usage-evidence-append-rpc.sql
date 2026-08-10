-- CFO-2a2.2b: typed idempotent append over the verified usage evidence table.
CREATE OR REPLACE FUNCTION public.lm_append_cfo_model_usage_evidence(
  p_uid text, p_financial_unit_id text, p_attribution_status text,
  p_provider text, p_provider_request_id text, p_usage_sequence bigint,
  p_occurred_at timestamptz, p_trace_id text, p_request_model text, p_response_model text,
  p_input_tokens bigint, p_output_tokens bigint, p_total_tokens bigint,
  p_cached_input_tokens bigint, p_reasoning_output_tokens bigint, p_tool_input_tokens bigint,
  p_evidence_status text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  stored public.lm_cfo_model_usage_evidence%ROWTYPE;
BEGIN
  INSERT INTO public.lm_cfo_model_usage_evidence (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence, occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens, cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status)
  VALUES (p_uid, p_financial_unit_id, p_attribution_status, p_provider, p_provider_request_id, p_usage_sequence, p_occurred_at, p_trace_id, p_request_model, p_response_model, p_input_tokens, p_output_tokens, p_total_tokens, p_cached_input_tokens, p_reasoning_output_tokens, p_tool_input_tokens, p_evidence_status)
  ON CONFLICT ON CONSTRAINT lm_cfo_model_usage_evidence_identity_unique DO NOTHING
  RETURNING * INTO stored;
  IF NOT FOUND THEN
    SELECT * INTO stored FROM public.lm_cfo_model_usage_evidence
    WHERE provider = p_provider AND provider_request_id = p_provider_request_id AND usage_sequence = p_usage_sequence;
    IF NOT FOUND OR stored.uid IS DISTINCT FROM p_uid OR stored.financial_unit_id IS DISTINCT FROM p_financial_unit_id OR stored.attribution_status IS DISTINCT FROM p_attribution_status OR stored.provider IS DISTINCT FROM p_provider OR stored.provider_request_id IS DISTINCT FROM p_provider_request_id OR stored.usage_sequence IS DISTINCT FROM p_usage_sequence OR stored.occurred_at IS DISTINCT FROM p_occurred_at OR stored.trace_id IS DISTINCT FROM p_trace_id OR stored.request_model IS DISTINCT FROM p_request_model OR stored.response_model IS DISTINCT FROM p_response_model OR stored.input_tokens IS DISTINCT FROM p_input_tokens OR stored.output_tokens IS DISTINCT FROM p_output_tokens OR stored.total_tokens IS DISTINCT FROM p_total_tokens OR stored.cached_input_tokens IS DISTINCT FROM p_cached_input_tokens OR stored.reasoning_output_tokens IS DISTINCT FROM p_reasoning_output_tokens OR stored.tool_input_tokens IS DISTINCT FROM p_tool_input_tokens OR stored.evidence_status IS DISTINCT FROM p_evidence_status THEN
      RAISE EXCEPTION 'provider_usage_identity_conflict' USING ERRCODE = '23505';
    END IF;
  END IF;
  RETURN jsonb_build_object('public_ref', stored.public_ref, 'provider', stored.provider, 'provider_request_id', stored.provider_request_id, 'usage_sequence', stored.usage_sequence, 'trace_id', stored.trace_id, 'created_at', stored.created_at);
END;
$$;
REVOKE ALL ON FUNCTION public.lm_append_cfo_model_usage_evidence(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.lm_append_cfo_model_usage_evidence(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text) TO service_role;
