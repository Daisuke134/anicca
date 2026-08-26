BEGIN;

ALTER TABLE public.lm_browser_jobs
  ADD COLUMN IF NOT EXISTS source_kind text,
  ADD COLUMN IF NOT EXISTS source_ref text;

UPDATE public.lm_browser_jobs
SET source_kind = 'telegram',
    source_ref = 'telegram://' || replace(telegram_chat_id, '/', '%2F') || '/' || replace(telegram_message_id, '/', '%2F')
WHERE source_kind IS NULL OR source_ref IS NULL;

ALTER TABLE public.lm_browser_jobs
  ALTER COLUMN source_kind SET NOT NULL,
  ALTER COLUMN source_ref SET NOT NULL,
  ALTER COLUMN telegram_chat_id DROP NOT NULL,
  ALTER COLUMN telegram_message_id DROP NOT NULL,
  ALTER COLUMN telegram_update_id DROP NOT NULL;

ALTER TABLE public.lm_browser_jobs
  DROP CONSTRAINT IF EXISTS lm_browser_jobs_source_kind_check,
  ADD CONSTRAINT lm_browser_jobs_source_kind_check CHECK (source_kind IN ('telegram', 'runtime')),
  DROP CONSTRAINT IF EXISTS lm_browser_jobs_source_shape_check,
  ADD CONSTRAINT lm_browser_jobs_source_shape_check CHECK (
    (source_kind = 'telegram' AND telegram_chat_id IS NOT NULL AND telegram_message_id IS NOT NULL AND telegram_update_id IS NOT NULL)
    OR
    (source_kind = 'runtime' AND telegram_chat_id IS NULL AND telegram_message_id IS NULL AND telegram_update_id IS NULL)
  );

CREATE UNIQUE INDEX IF NOT EXISTS lm_browser_jobs_source_unique_idx
  ON public.lm_browser_jobs (uid, source_kind, source_ref);

COMMIT;
