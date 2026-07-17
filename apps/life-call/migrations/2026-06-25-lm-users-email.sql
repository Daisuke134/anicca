-- v1 web reply-by-email: the scheduler sends asks/late-notices to the user's own address (captured from
-- the Google sign-in during web onboarding) via Resend — we never read their Gmail. Replaces unipileEmail().
ALTER TABLE lm_users ADD COLUMN IF NOT EXISTS email text;
