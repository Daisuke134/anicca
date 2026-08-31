-- Bind the existing cloud browser queue to Panel/Symphony workrooms without duplicating it.
-- Historical Telegram jobs remain readable and keep their original idempotency key.

ALTER TABLE public.lm_browser_jobs
  ADD COLUMN IF NOT EXISTS source_kind text,
  ADD COLUMN IF NOT EXISTS source_ref text,
  ADD COLUMN IF NOT EXISTS job_id text,
  ADD COLUMN IF NOT EXISTS dispatch_id text,
  ADD COLUMN IF NOT EXISTS effect_key text;

UPDATE public.lm_browser_jobs
SET source_kind = 'telegram'
WHERE source_kind IS NULL;

UPDATE public.lm_browser_jobs
SET source_ref = 'telegram-message://' || telegram_chat_id || '/' || telegram_message_id
WHERE source_ref IS NULL;

ALTER TABLE public.lm_browser_jobs
  ALTER COLUMN source_kind SET NOT NULL,
  ALTER COLUMN source_ref SET NOT NULL,
  ALTER COLUMN telegram_chat_id DROP NOT NULL,
  ALTER COLUMN telegram_message_id DROP NOT NULL,
  ALTER COLUMN telegram_update_id DROP NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_source_kind_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_source_kind_check
      CHECK (source_kind IN ('telegram', 'panel', 'symphony')) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_source_shape_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_source_shape_check CHECK (
        (source_kind = 'telegram'
          AND telegram_chat_id IS NOT NULL
          AND telegram_message_id IS NOT NULL
          AND telegram_update_id IS NOT NULL)
        OR (source_kind IN ('panel', 'symphony')
          AND telegram_chat_id IS NULL
          AND telegram_message_id IS NULL
          AND telegram_update_id IS NULL)
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_workroom_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_workroom_check CHECK (
        (job_id IS NULL OR job_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$')
        AND (dispatch_id IS NULL OR dispatch_id ~ '^[0-9a-f]{64}$')
        AND (effect_key IS NULL OR effect_key ~ '^[0-9a-f]{64}$')
        AND (source_kind <> 'symphony'
          OR (job_id IS NOT NULL AND dispatch_id IS NOT NULL AND effect_key IS NOT NULL))
      ) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_source_ref_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_source_ref_check
      CHECK (char_length(source_ref) BETWEEN 4 AND 1000) NOT VALID;
  END IF;
END
$$;

ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_source_kind_check;
ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_source_shape_check;
ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_workroom_check;
ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_source_ref_check;

CREATE UNIQUE INDEX IF NOT EXISTS lm_browser_jobs_tenant_effect_uidx
  ON public.lm_browser_jobs (uid, effect_key)
  WHERE effect_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS lm_browser_jobs_workroom_idx
  ON public.lm_browser_jobs (uid, job_id, created_at DESC)
  WHERE job_id IS NOT NULL;
