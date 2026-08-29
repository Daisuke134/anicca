-- Task 5A: durable human boundary and same-job resume.
-- The task row contains only opaque references. Private answers stay in the vault.

-- A human handoff pauses an existing runtime row; answering it requeues that same row.
ALTER TABLE public.lm_runtime_jobs
  DROP CONSTRAINT IF EXISTS lm_runtime_jobs_status_check;
ALTER TABLE public.lm_runtime_jobs
  ADD CONSTRAINT lm_runtime_jobs_status_check CHECK (
    status IN ('queued', 'running', 'waiting_human', 'reconciling', 'completed', 'dead_letter')
  );

CREATE TABLE IF NOT EXISTS public.lm_human_tasks (
  uid text NOT NULL CHECK (uid ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  task_id text NOT NULL CHECK (task_id ~ '^[0-9a-f]{64}$'),
  job_id text NOT NULL CHECK (char_length(job_id) BETWEEN 1 AND 200),
  reason_code text NOT NULL CHECK (reason_code ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$'),
  question text NOT NULL CHECK (char_length(question) BETWEEN 1 AND 2000),
  required_format jsonb NOT NULL CHECK (
    jsonb_typeof(required_format) IN ('object', 'array', 'string')
    AND octet_length(required_format::text) <= 4096
  ),
  resume_ref text NOT NULL CHECK (
    resume_ref ~ '^[a-z][a-z0-9+.-]{1,31}://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&''()*+,;=%-]{0,999}$'
  ),
  context_refs jsonb NOT NULL CHECK (
    jsonb_typeof(context_refs) = 'object'
    AND octet_length(context_refs::text) <= 16384
  ),
  human_boundary_ref text NOT NULL CHECK (
    human_boundary_ref ~ '^human-boundary://sha256/[0-9a-f]{64}$'
  ),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1 AND version <= 1000000),
  answer_ref text CHECK (
    answer_ref IS NULL
    OR answer_ref ~ '^vault-answer://[a-z0-9][a-z0-9._-]{0,199}/[A-Za-z0-9][A-Za-z0-9._~%-]{0,255}$'
  ),
  answered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, task_id),
  FOREIGN KEY (job_id, uid)
    REFERENCES public.lm_runtime_jobs (job_id, tenant_id),
  CHECK (
    (status = 'open' AND answer_ref IS NULL AND answered_at IS NULL)
    OR (status = 'answered' AND answer_ref IS NOT NULL AND answered_at IS NOT NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS lm_human_tasks_open_dedupe_idx
  ON public.lm_human_tasks (uid, job_id, reason_code)
  WHERE status = 'open';
CREATE INDEX IF NOT EXISTS lm_human_tasks_uid_status_idx
  ON public.lm_human_tasks (uid, status, updated_at DESC);

ALTER TABLE public.lm_human_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_human_tasks FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_human_tasks FROM PUBLIC, anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.create_lm_human_task(
  p_uid text,
  p_task_id text,
  p_job_id text,
  p_reason_code text,
  p_question text,
  p_required_format jsonb,
  p_resume_ref text,
  p_context_refs jsonb,
  p_human_boundary_ref text
) RETURNS SETOF public.lm_human_tasks
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_task public.lm_human_tasks%ROWTYPE;
  v_job public.lm_runtime_jobs%ROWTYPE;
  v_item record;
  v_ref jsonb;
  v_task_found boolean;
BEGIN
  IF p_uid IS NULL OR p_uid !~ '^[a-z0-9][a-z0-9._-]{0,199}$'
    OR p_task_id IS NULL OR p_task_id !~ '^[0-9a-f]{64}$'
    OR p_job_id IS NULL OR p_job_id !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$'
    OR p_reason_code IS NULL OR p_reason_code !~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$'
    OR p_question IS NULL OR char_length(p_question) NOT BETWEEN 1 AND 2000
    OR jsonb_typeof(p_required_format) NOT IN ('object', 'array', 'string')
    OR octet_length(p_required_format::text) > 4096
    OR p_resume_ref IS NULL OR p_resume_ref !~ '^[a-z][a-z0-9+.-]{1,31}://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&''()*+,;=%-]{0,999}$'
    OR p_human_boundary_ref IS NULL OR p_human_boundary_ref !~ '^human-boundary://sha256/[0-9a-f]{64}$'
    OR jsonb_typeof(p_context_refs) <> 'object'
    OR octet_length(p_context_refs::text) > 16384 THEN
    RAISE EXCEPTION 'human task input invalid';
  END IF;

  FOR v_item IN SELECT key, value FROM jsonb_each(p_context_refs) LOOP
    IF v_item.key !~ '_(ref|refs)$' THEN
      RAISE EXCEPTION 'human task context refs must be reference-only';
    END IF;
    IF jsonb_typeof(v_item.value) = 'array' THEN
      FOR v_ref IN SELECT value FROM jsonb_array_elements(v_item.value) LOOP
        IF jsonb_typeof(v_ref) <> 'string'
          OR v_ref #>> '{}' !~ '^[a-z][a-z0-9+.-]{1,31}://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&''()*+,;=%-]{1,999}$' THEN
          RAISE EXCEPTION 'human task context refs must be reference-only';
        END IF;
      END LOOP;
    ELSIF jsonb_typeof(v_item.value) <> 'string'
      OR v_item.value #>> '{}' !~ '^[a-z][a-z0-9+.-]{1,31}://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&''()*+,;=%-]{1,999}$' THEN
      RAISE EXCEPTION 'human task context refs must be reference-only';
    END IF;
  END LOOP;

  SELECT * INTO v_task
  FROM public.lm_human_tasks
  WHERE uid = p_uid AND task_id = p_task_id
  FOR UPDATE;
  IF FOUND THEN
    IF v_task.job_id IS DISTINCT FROM p_job_id
      OR v_task.reason_code IS DISTINCT FROM p_reason_code
      OR v_task.question IS DISTINCT FROM p_question
      OR v_task.required_format IS DISTINCT FROM p_required_format
      OR v_task.resume_ref IS DISTINCT FROM p_resume_ref
      OR v_task.context_refs IS DISTINCT FROM p_context_refs
      OR v_task.human_boundary_ref IS DISTINCT FROM p_human_boundary_ref THEN
      RAISE EXCEPTION 'human task id conflict';
    END IF;
    RETURN NEXT v_task;
    RETURN;
  END IF;

  SELECT * INTO v_task
  FROM public.lm_human_tasks
  WHERE uid = p_uid AND job_id = p_job_id AND reason_code = p_reason_code AND status = 'open'
  FOR UPDATE;
  v_task_found := FOUND;

  SELECT * INTO v_job
  FROM public.lm_runtime_jobs
  WHERE tenant_id = p_uid AND job_id = p_job_id
  FOR UPDATE;
  IF NOT FOUND OR v_job.status NOT IN ('queued', 'running', 'waiting_human') THEN
    RAISE EXCEPTION 'human task runtime job unavailable';
  END IF;

  IF NOT v_task_found THEN
    INSERT INTO public.lm_human_tasks (
      uid, task_id, job_id, reason_code, question, required_format, resume_ref,
      context_refs, human_boundary_ref
    ) VALUES (
      p_uid, p_task_id, p_job_id, p_reason_code, p_question, p_required_format,
      p_resume_ref, p_context_refs, p_human_boundary_ref
    )
    ON CONFLICT DO NOTHING
    RETURNING * INTO v_task;
    IF NOT FOUND THEN
      SELECT * INTO v_task
      FROM public.lm_human_tasks
      WHERE uid = p_uid AND job_id = p_job_id AND reason_code = p_reason_code AND status = 'open'
      FOR UPDATE;
    END IF;
  END IF;

  IF v_task.task_id IS NULL THEN RAISE EXCEPTION 'human task create conflict'; END IF;

  UPDATE public.lm_runtime_jobs
  SET status = 'waiting_human',
      lease_owner = NULL,
      lease_expires_at = NULL,
      updated_at = clock_timestamp()
  WHERE tenant_id = p_uid
    AND job_id = p_job_id
    AND status IN ('queued', 'running', 'waiting_human');
  IF NOT FOUND THEN RAISE EXCEPTION 'human task runtime job unavailable'; END IF;

  RETURN NEXT v_task;
END;
$$;

CREATE OR REPLACE FUNCTION public.answer_lm_human_task(
  p_uid text,
  p_task_id text,
  p_version integer,
  p_answer_ref text
) RETURNS SETOF public.lm_human_tasks
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_task public.lm_human_tasks%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR p_uid !~ '^[a-z0-9][a-z0-9._-]{0,199}$'
    OR p_task_id IS NULL OR p_task_id !~ '^[0-9a-f]{64}$'
    OR p_version IS NULL OR p_version NOT BETWEEN 1 AND 1000000
    OR p_answer_ref IS NULL
    OR p_answer_ref !~ '^vault-answer://[a-z0-9][a-z0-9._-]{0,199}/[A-Za-z0-9][A-Za-z0-9._~%-]{0,255}$'
    OR split_part(p_answer_ref, '/', 3) <> p_uid THEN
    RAISE EXCEPTION 'human task answer invalid';
  END IF;

  SELECT * INTO v_task
  FROM public.lm_human_tasks
  WHERE uid = p_uid AND task_id = p_task_id
  FOR UPDATE;
  IF NOT FOUND THEN RETURN; END IF;

  IF v_task.status = 'answered' THEN
    IF v_task.answer_ref IS DISTINCT FROM p_answer_ref THEN
      RAISE EXCEPTION 'human task answer conflict';
    END IF;
    RETURN NEXT v_task;
    RETURN;
  END IF;
  IF v_task.version <> p_version THEN RAISE EXCEPTION 'human task version conflict'; END IF;

  UPDATE public.lm_runtime_jobs
  SET status = 'queued',
      available_at = clock_timestamp(),
      lease_owner = NULL,
      lease_expires_at = NULL,
      last_error_code = NULL,
      updated_at = clock_timestamp()
  WHERE tenant_id = p_uid
    AND job_id = v_task.job_id
    AND status = 'waiting_human';
  IF NOT FOUND THEN RAISE EXCEPTION 'human task runtime job is not waiting'; END IF;

  UPDATE public.lm_human_tasks
  SET status = 'answered',
      version = version + 1,
      answer_ref = p_answer_ref,
      answered_at = clock_timestamp(),
      updated_at = clock_timestamp()
  WHERE uid = p_uid AND task_id = p_task_id AND status = 'open' AND version = p_version
  RETURNING * INTO v_task;
  IF NOT FOUND THEN RAISE EXCEPTION 'human task answer conflict'; END IF;
  RETURN NEXT v_task;
END;
$$;

REVOKE ALL ON FUNCTION public.create_lm_human_task(text,text,text,text,text,jsonb,text,jsonb,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.answer_lm_human_task(text,text,integer,text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_lm_human_task(text,text,text,text,text,jsonb,text,jsonb,text)
  TO service_role;
GRANT EXECUTE ON FUNCTION public.answer_lm_human_task(text,text,integer,text)
  TO service_role;
