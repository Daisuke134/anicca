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
