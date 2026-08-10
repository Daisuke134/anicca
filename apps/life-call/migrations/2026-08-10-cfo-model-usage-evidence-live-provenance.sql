ALTER TABLE public.lm_cfo_model_usage_evidence
  ADD COLUMN local_correlation_id text
    CONSTRAINT lm_cfo_model_usage_evidence_local_correlation_format
    CHECK (local_correlation_id IS NULL OR local_correlation_id ~ '^live-session:[0-9a-f]{32}$'),
  ALTER COLUMN provider_request_id DROP NOT NULL,
  ALTER COLUMN response_model DROP NOT NULL,
  ADD CONSTRAINT lm_cfo_model_usage_evidence_identity_path_check CHECK (
    (provider_request_id IS NOT NULL AND response_model IS NOT NULL AND local_correlation_id IS NULL)
    OR
    (provider_request_id IS NULL AND response_model IS NULL AND local_correlation_id IS NOT NULL)
  );

CREATE UNIQUE INDEX lm_cfo_model_usage_evidence_local_identity_unique
  ON public.lm_cfo_model_usage_evidence (provider, local_correlation_id, usage_sequence)
  WHERE local_correlation_id IS NOT NULL;
