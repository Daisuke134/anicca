-- L04.6: tenant-scoped Investment Loop control state. Secrets stay in the secret provider;
-- this table contains references only and is service-role-only.
CREATE TABLE IF NOT EXISTS public.lm_investment_states (
  uid text PRIMARY KEY CHECK (uid ~ '^[A-Za-z0-9._-]{1,200}$'),
  lifecycle text NOT NULL CHECK (lifecycle IN ('setup_required', 'in_review', 'approved', 'active', 'rejected', 'action_required')),
  deployment text NOT NULL CHECK (deployment IN ('local', 'cloud')),
  mode text NOT NULL CHECK (mode IN ('paper', 'shadow', 'live')),
  paused boolean NOT NULL DEFAULT false,
  killed boolean NOT NULL DEFAULT false,
  core_digest text CHECK (core_digest IS NULL OR core_digest ~ '^[a-f0-9]{64}$'),
  receipt_refs jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(receipt_refs) = 'array'),
  alpaca_api_key_ref text CHECK (alpaca_api_key_ref IS NULL OR alpaca_api_key_ref ~ '^secret://alpaca/[A-Za-z0-9._/-]+$'),
  alpaca_api_secret_ref text CHECK (alpaca_api_secret_ref IS NULL OR alpaca_api_secret_ref ~ '^secret://alpaca/[A-Za-z0-9._/-]+$'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

ALTER TABLE public.lm_investment_states ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.lm_investment_states FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_investment_states FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.lm_investment_states FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_investment_states TO service_role';
  END IF;
END
$$;
