BEGIN;

ALTER TABLE public.lm_funder_registry_snapshots
  ADD COLUMN IF NOT EXISTS source_url text CHECK (source_url IS NULL OR source_url ~ '^https://'),
  ADD COLUMN IF NOT EXISTS last_verified_at timestamptz,
  ADD COLUMN IF NOT EXISTS next_deadline date,
  ADD COLUMN IF NOT EXISTS terms_hash text CHECK (terms_hash IS NULL OR terms_hash ~ '^[0-9a-f]{64}$'),
  ADD COLUMN IF NOT EXISTS solo_allowed text CHECK (solo_allowed IS NULL OR solo_allowed IN ('yes','no','unknown')),
  ADD COLUMN IF NOT EXISTS location text,
  ADD COLUMN IF NOT EXISTS status text CHECK (status IS NULL OR status IN ('open','closed','announced','unknown')),
  ADD COLUMN IF NOT EXISTS source_content_sha256 text CHECK (source_content_sha256 IS NULL OR source_content_sha256 ~ '^[0-9a-f]{64}$'),
  ADD COLUMN IF NOT EXISTS evidence_sha256 text CHECK (evidence_sha256 IS NULL OR evidence_sha256 ~ '^[0-9a-f]{64}$'),
  ADD COLUMN IF NOT EXISTS rationale_sha256 text CHECK (rationale_sha256 IS NULL OR rationale_sha256 ~ '^[0-9a-f]{64}$'),
  ADD COLUMN IF NOT EXISTS discovery_kind text CHECK (discovery_kind IS NULL OR discovery_kind IN ('new_program','existing_change')),
  ADD COLUMN IF NOT EXISTS discovery_facts_digest text CHECK (discovery_facts_digest IS NULL OR discovery_facts_digest ~ '^[0-9a-f]{64}$');

CREATE TABLE IF NOT EXISTS public.lm_funder_discovery_runs (
  tenant_id text NOT NULL,
  discovery_run_id text NOT NULL CHECK (discovery_run_id ~ '^funder-discovery:[0-9a-f]{64}$'),
  tokyo_day date NOT NULL,
  observed_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status = 'complete'),
  source_count integer NOT NULL CHECK (source_count > 0),
  candidate_count integer NOT NULL CHECK (candidate_count >= 0),
  appended_count integer NOT NULL CHECK (appended_count >= 0 AND appended_count <= candidate_count),
  source_receipts jsonb NOT NULL,
  registry_ids jsonb NOT NULL,
  run_digest text NOT NULL CHECK (run_digest ~ '^[0-9a-f]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, discovery_run_id),
  UNIQUE (tenant_id, tokyo_day)
);

ALTER TABLE public.lm_funder_discovery_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.lm_funder_discovery_runs FROM PUBLIC;

COMMIT;
