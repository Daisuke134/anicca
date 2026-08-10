-- CFO-2a2.2a: structured provider usage evidence with a private append-only boundary.
CREATE TABLE IF NOT EXISTS public.lm_cfo_model_usage_evidence (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE CHECK (public_ref <> '00000000-0000-0000-0000-000000000000'::uuid),
  uid text NOT NULL REFERENCES public.lm_users(uid) CHECK (btrim(uid) <> ''),
  financial_unit_id text CONSTRAINT lm_cfo_model_usage_evidence_financial_unit_snake_case CHECK (financial_unit_id IS NULL OR financial_unit_id ~ '^[a-z][a-z0-9_]*$'),
  attribution_status text NOT NULL CHECK ((attribution_status = 'attributed' AND financial_unit_id IS NOT NULL) OR (attribution_status = 'unattributed' AND financial_unit_id IS NULL)),
  provider text NOT NULL CHECK (provider ~ '^[a-z0-9]+(?:\.[a-z0-9-]+)+$'),
  provider_request_id text NOT NULL CHECK (btrim(provider_request_id) <> '' AND provider_request_id = btrim(provider_request_id)),
  usage_sequence bigint NOT NULL CHECK (usage_sequence >= 0),
  occurred_at timestamptz NOT NULL,
  trace_id text NOT NULL CHECK (trace_id ~ '^[0-9a-f]{32}$' AND trace_id <> repeat('0', 32)),
  request_model text NOT NULL CHECK (btrim(request_model) <> '' AND request_model = btrim(request_model)),
  response_model text NOT NULL CHECK (btrim(response_model) <> '' AND response_model = btrim(response_model)),
  input_tokens bigint NOT NULL CHECK (input_tokens >= 0),
  output_tokens bigint NOT NULL CHECK (output_tokens >= 0),
  total_tokens bigint NOT NULL CHECK (total_tokens >= 0),
  cached_input_tokens bigint CHECK (cached_input_tokens IS NULL OR cached_input_tokens >= 0),
  reasoning_output_tokens bigint CHECK (reasoning_output_tokens IS NULL OR reasoning_output_tokens >= 0),
  tool_input_tokens bigint CHECK (tool_input_tokens IS NULL OR tool_input_tokens >= 0),
  evidence_status text NOT NULL CHECK (evidence_status IN ('provider_reported', 'locally_estimated')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CONSTRAINT lm_cfo_model_usage_evidence_identity_unique UNIQUE (provider, provider_request_id, usage_sequence)
);

ALTER TABLE public.lm_cfo_model_usage_evidence ENABLE ROW LEVEL SECURITY;
CREATE POLICY lm_cfo_model_usage_evidence_service_select ON public.lm_cfo_model_usage_evidence FOR SELECT TO service_role USING (true);
CREATE POLICY lm_cfo_model_usage_evidence_service_insert ON public.lm_cfo_model_usage_evidence FOR INSERT TO service_role WITH CHECK (true);
REVOKE ALL ON TABLE public.lm_cfo_model_usage_evidence FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_model_usage_evidence TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_model_usage_evidence FROM service_role;
REVOKE ALL ON SEQUENCE public.lm_cfo_model_usage_evidence_id_seq FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_model_usage_evidence_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_cfo_model_usage_evidence_mutation()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_cfo_model_usage_evidence is append-only' USING ERRCODE = '55000';
END;
$$;
DROP TRIGGER IF EXISTS lm_cfo_model_usage_evidence_append_only ON public.lm_cfo_model_usage_evidence;
CREATE TRIGGER lm_cfo_model_usage_evidence_append_only BEFORE UPDATE OR DELETE ON public.lm_cfo_model_usage_evidence
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_cfo_model_usage_evidence_mutation();
REVOKE ALL ON FUNCTION public.reject_lm_cfo_model_usage_evidence_mutation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reject_lm_cfo_model_usage_evidence_mutation() TO service_role;
