-- Tokens table for OAuth credentials (encrypted via KMS envelope)
CREATE TABLE IF NOT EXISTS tokens (
  user_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_sub TEXT,
  email TEXT,
  access_token_enc JSONB NOT NULL,
  refresh_token_enc JSONB,
  scope TEXT,
  expiry TIMESTAMPTZ,
  rotation_family_id TEXT,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_tokens_provider_sub ON tokens(provider_sub);
CREATE INDEX IF NOT EXISTS idx_tokens_email ON tokens(email);

-- Updated-at trigger (optional). If you don't have plpgsql, skip this.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at_tokens'
  ) THEN
    CREATE OR REPLACE FUNCTION set_updated_at_tokens() RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = now();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
  END IF;
END$$;

DROP TRIGGER IF EXISTS trg_tokens_updated_at ON tokens;
CREATE TRIGGER trg_tokens_updated_at
BEFORE UPDATE ON tokens
FOR EACH ROW EXECUTE FUNCTION set_updated_at_tokens();
