-- Official Symphony owns agent execution rounds; the Life Manager runtime job remains authoritative.
-- waiting_agent releases the worker lease while one isolated Symphony round is in flight.

ALTER TABLE public.lm_runtime_jobs
  DROP CONSTRAINT IF EXISTS lm_runtime_jobs_status_check;
ALTER TABLE public.lm_runtime_jobs
  ADD CONSTRAINT lm_runtime_jobs_status_check CHECK (
    status IN (
      'queued', 'running', 'waiting_agent', 'waiting_human',
      'reconciling', 'completed', 'dead_letter'
    )
  );

CREATE TABLE IF NOT EXISTS public.lm_symphony_dispatches (
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  dispatch_id text NOT NULL CHECK (dispatch_id ~ '^[0-9a-f]{64}$'),
  job_id text NOT NULL CHECK (char_length(job_id) BETWEEN 1 AND 200),
  round integer NOT NULL CHECK (round BETWEEN 1 AND 1000000),
  status text NOT NULL CHECK (status IN ('claimed', 'mirrored', 'result_ready', 'failed')),
  issue_ref text CHECK (
    issue_ref IS NULL OR issue_ref ~ '^github-issue://Daisuke134/life-manager-workrooms/[1-9][0-9]*$'
  ),
  result_ref text CHECK (
    result_ref IS NULL OR result_ref ~ '^github-comment://Daisuke134/life-manager-workrooms/[1-9][0-9]*/[1-9][0-9]*$'
  ),
  result_hash text CHECK (result_hash IS NULL OR result_hash ~ '^[0-9a-f]{64}$'),
  result_payload jsonb CHECK (
    result_payload IS NULL OR (
      jsonb_typeof(result_payload) = 'object'
      AND octet_length(result_payload::text) <= 16384
    )
  ),
  failure_code text CHECK (
    failure_code IS NULL OR char_length(failure_code) BETWEEN 1 AND 200
  ),
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  mirrored_at timestamptz,
  result_ready_at timestamptz,
  failed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (tenant_id, dispatch_id),
  UNIQUE (tenant_id, job_id, round),
  FOREIGN KEY (job_id, tenant_id)
    REFERENCES public.lm_runtime_jobs (job_id, tenant_id),
  CHECK (
    (status = 'claimed' AND issue_ref IS NULL AND result_ref IS NULL AND result_hash IS NULL
      AND result_payload IS NULL AND failure_code IS NULL AND mirrored_at IS NULL
      AND result_ready_at IS NULL AND failed_at IS NULL)
    OR (status = 'mirrored' AND issue_ref IS NOT NULL AND result_ref IS NULL AND result_hash IS NULL
      AND result_payload IS NULL AND failure_code IS NULL AND mirrored_at IS NOT NULL
      AND result_ready_at IS NULL AND failed_at IS NULL)
    OR (status = 'result_ready' AND issue_ref IS NOT NULL AND result_ref IS NOT NULL
      AND result_hash IS NOT NULL AND result_payload IS NOT NULL AND failure_code IS NULL
      AND mirrored_at IS NOT NULL AND result_ready_at IS NOT NULL AND failed_at IS NULL)
    OR (status = 'failed' AND failure_code IS NOT NULL AND failed_at IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS lm_symphony_dispatches_open_job_idx
  ON public.lm_symphony_dispatches (tenant_id, job_id)
  WHERE status IN ('claimed', 'mirrored', 'result_ready');
CREATE INDEX IF NOT EXISTS lm_symphony_dispatches_tenant_status_idx
  ON public.lm_symphony_dispatches (tenant_id, status, updated_at DESC);

ALTER TABLE public.lm_symphony_dispatches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_symphony_dispatches FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_symphony_dispatches FROM PUBLIC, anon, authenticated, service_role;
