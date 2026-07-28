-- BROWSER-AUTH-1 forward upgrade for production lm_browser_jobs tables created before
-- principal_kind existed. Historical login-dependent classifier jobs used agent-owned auth;
-- non-login jobs had no principal. The deterministic backfill preserves that meaning.

ALTER TABLE public.lm_browser_jobs
  ADD COLUMN IF NOT EXISTS principal_kind text;

UPDATE public.lm_browser_jobs
SET principal_kind = CASE
  WHEN requires_login THEN 'agent_owned'
  ELSE 'none'
END
WHERE principal_kind IS NULL;

ALTER TABLE public.lm_browser_jobs
  ALTER COLUMN principal_kind SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_principal_kind_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_principal_kind_check
      CHECK (principal_kind IN ('none', 'agent_owned', 'user_provided')) NOT VALID;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_browser_jobs'::regclass
      AND conname = 'lm_browser_jobs_login_principal_kind_check'
  ) THEN
    ALTER TABLE public.lm_browser_jobs
      ADD CONSTRAINT lm_browser_jobs_login_principal_kind_check
      CHECK (
        (requires_login = false AND principal_kind = 'none')
        OR (requires_login = true AND principal_kind IN ('agent_owned', 'user_provided'))
      ) NOT VALID;
  END IF;
END
$$;

ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_principal_kind_check;
ALTER TABLE public.lm_browser_jobs
  VALIDATE CONSTRAINT lm_browser_jobs_login_principal_kind_check;
