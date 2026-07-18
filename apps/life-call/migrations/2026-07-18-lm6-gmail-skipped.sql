ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS gmail_skipped boolean NOT NULL DEFAULT false;
