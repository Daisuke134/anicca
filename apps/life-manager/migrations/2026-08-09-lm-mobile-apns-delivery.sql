-- Durable APNs dispatch jobs. The semantic outbox row and its job are created
-- by append_lm_mobile_outbox_with_push_job in one transaction.
CREATE TABLE IF NOT EXISTS public.lm_mobile_push_jobs (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  message_id text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  lease_expires_at timestamptz,
  last_error text,
  result jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  PRIMARY KEY (uid, message_id),
  CONSTRAINT lm_mobile_push_jobs_message_fk FOREIGN KEY (uid, message_id)
    REFERENCES public.lm_mobile_outbox(uid, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS lm_mobile_push_jobs_pending_idx
  ON public.lm_mobile_push_jobs (status, next_attempt_at, created_at);

ALTER TABLE public.lm_mobile_push_jobs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_mobile_push_jobs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_mobile_push_jobs TO service_role;

CREATE OR REPLACE FUNCTION public.append_lm_mobile_outbox_with_push_job(
  p_uid text,
  p_id text,
  p_key text,
  p_type text,
  p_args jsonb,
  p_user_content jsonb,
  p_question jsonb,
  p_route jsonb,
  p_created_at timestamptz,
  p_mutation_key text
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  outbox_row public.lm_mobile_outbox;
  inserted boolean;
BEGIN
  INSERT INTO public.lm_mobile_outbox(
    uid, id, key, type, args, user_content, question, route, created_at, mutation_key
  ) VALUES (
    p_uid, p_id, p_key, p_type, COALESCE(p_args, '{}'::jsonb), p_user_content, p_question, p_route,
    COALESCE(p_created_at, now()), p_mutation_key
  )
  ON CONFLICT (uid, id) DO NOTHING
  RETURNING * INTO outbox_row;

  inserted := FOUND;
  IF NOT inserted THEN
    SELECT * INTO outbox_row
      FROM public.lm_mobile_outbox
     WHERE uid = p_uid AND id = p_id;
  END IF;

  INSERT INTO public.lm_mobile_push_jobs(uid, message_id)
  VALUES (p_uid, p_id)
  ON CONFLICT (uid, message_id) DO NOTHING;

  RETURN jsonb_build_object('inserted', inserted, 'row', to_jsonb(outbox_row));
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_lm_mobile_push_job(
  p_uid text,
  p_message_id text,
  p_now timestamptz,
  p_lease_seconds integer
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  job_row public.lm_mobile_push_jobs;
BEGIN
  UPDATE public.lm_mobile_push_jobs
     SET status = 'processing',
         attempts = attempts + 1,
         lease_expires_at = COALESCE(p_now, now()) + make_interval(secs => GREATEST(1, p_lease_seconds)),
         updated_at = COALESCE(p_now, now())
   WHERE uid = p_uid
     AND message_id = p_message_id
     AND (
       (status = 'pending' AND next_attempt_at <= COALESCE(p_now, now()))
       OR (status = 'processing' AND lease_expires_at IS NOT NULL AND lease_expires_at <= COALESCE(p_now, now()))
     )
  RETURNING * INTO job_row;
  IF NOT FOUND THEN RETURN NULL; END IF;
  RETURN to_jsonb(job_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_lm_mobile_push_job(
  p_uid text,
  p_message_id text,
  p_result jsonb
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  job_row public.lm_mobile_push_jobs;
BEGIN
  UPDATE public.lm_mobile_push_jobs
     SET status = 'completed', result = COALESCE(p_result, '{}'::jsonb),
         lease_expires_at = NULL, completed_at = now(), updated_at = now()
   WHERE uid = p_uid AND message_id = p_message_id AND status = 'processing'
  RETURNING * INTO job_row;
  IF NOT FOUND THEN RETURN NULL; END IF;
  RETURN to_jsonb(job_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.retry_lm_mobile_push_job(
  p_uid text,
  p_message_id text,
  p_error text,
  p_next_attempt_at timestamptz,
  p_max_attempts integer
)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  job_row public.lm_mobile_push_jobs;
BEGIN
  UPDATE public.lm_mobile_push_jobs
     SET status = CASE WHEN attempts >= GREATEST(1, p_max_attempts) THEN 'failed' ELSE 'pending' END,
         last_error = p_error, next_attempt_at = COALESCE(p_next_attempt_at, now()),
         lease_expires_at = NULL, updated_at = now()
   WHERE uid = p_uid AND message_id = p_message_id AND status = 'processing'
  RETURNING * INTO job_row;
  IF NOT FOUND THEN RETURN NULL; END IF;
  RETURN to_jsonb(job_row);
END;
$$;

REVOKE ALL ON FUNCTION public.append_lm_mobile_outbox_with_push_job(text, text, text, text, jsonb, jsonb, jsonb, jsonb, timestamptz, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.claim_lm_mobile_push_job(text, text, timestamptz, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_lm_mobile_push_job(text, text, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.retry_lm_mobile_push_job(text, text, text, timestamptz, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.append_lm_mobile_outbox_with_push_job(text, text, text, text, jsonb, jsonb, jsonb, jsonb, timestamptz, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_lm_mobile_push_job(text, text, timestamptz, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_lm_mobile_push_job(text, text, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.retry_lm_mobile_push_job(text, text, text, timestamptz, integer) TO service_role;
