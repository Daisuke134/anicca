BEGIN;

CREATE TABLE IF NOT EXISTS public.lm_funder_registry_snapshots (
  tenant_id text NOT NULL,
  registry_id text NOT NULL CHECK (registry_id ~ '^funder-registry:[0-9a-f]{64}$'),
  funder_id text NOT NULL CHECK (funder_id ~ '^[a-z0-9][a-z0-9._-]{1,99}$'),
  name text NOT NULL,
  official_url text NOT NULL CHECK (official_url ~ '^https://'),
  funder_type text NOT NULL CHECK (funder_type IN ('accelerator','grant','foundation','prize')),
  priority integer NOT NULL CHECK (priority > 0),
  verification_status text NOT NULL CHECK (verification_status IN ('needs_reverification','verified','denied','closed')),
  automation_gate text NOT NULL CHECK (automation_gate IN ('review_required','captcha_blocked','auth_blocked','ready','denied')),
  source_ref text NOT NULL,
  observed_at timestamptz NOT NULL,
  revision_digest text NOT NULL CHECK (revision_digest ~ '^[0-9a-f]{64}$'),
  legacy_claims jsonb NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, registry_id)
);

ALTER TABLE public.lm_funder_registry_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_funder_registry_snapshots FROM PUBLIC;

COMMIT;
