-- BROWSER-AUTH-1: service-only encrypted browser authentication contexts.
-- Every row is tenant-bound by uid, normalized HTTPS origin, and principal kind. Plaintext
-- cookies or storage values never enter this table.

CREATE TABLE IF NOT EXISTS public.lm_browser_auth_sessions (
  uid text NOT NULL,
  origin text NOT NULL,
  principal_kind text NOT NULL CHECK (principal_kind IN ('agent_owned', 'user_provided')),
  ciphertext text NOT NULL,
  iv text NOT NULL,
  auth_tag text NOT NULL,
  context_sha256 text NOT NULL,
  key_version integer NOT NULL DEFAULT 1,
  state text NOT NULL CHECK (state IN ('active', 'invalidated')),
  expires_at timestamptz,
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, origin, principal_kind)
);

ALTER TABLE public.lm_browser_auth_sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_browser_auth_sessions FROM PUBLIC;

-- Railway's production PostgreSQL is not required to define Supabase's client
-- roles. Keep the migration portable while preserving the same closed grants
-- whenever those roles exist.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_browser_auth_sessions FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_browser_auth_sessions FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_browser_auth_sessions TO service_role';
  END IF;
END
$$;
