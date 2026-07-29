-- AE-ZERO-START-1 §4.1 — bind a tenant to the public identity of BOTH of its agent wallets.
--
-- REPORT-1 (2026-07-27-lm-financial-reports.sql) already owns agent_wallet_address and its EVM CHECK.
-- This migration is purely additive: it adds the Solana public address, a reference for each rail's
-- signing material, and the provisioning timestamp. The existing EVM constraint is deliberately not
-- touched — restating it here would be a second place for the EVM shape to drift.
--
-- The only column-level secret this schema stores is a reference, never key material. §5.3 requires
-- that to be true BY SCHEMA rather than by convention, so each key-ref column carries a CHECK that
-- accepts the `secret://` grammar (the same one lib/secret-provider.js resolves) and then refuses
-- anything key-shaped: an EVM 0x prefix, any run of 64 hex characters (an EVM private key), and any run
-- of 80+ base58 characters (a Solana 64-byte secret key encodes to 87-88). A well-formed reference
-- cannot contain those runs, so the checks cost nothing legitimate and close the case where a caller
-- passes the key where the reference belongs.
--
-- Uniqueness is enforced here too, partial on NOT NULL like the existing EVM index. Cross-tenant wallet
-- contamination is the headline risk in this slice, and the database is the only place that can refuse
-- it regardless of which code path writes the row.

ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS agent_wallet_solana_address text,
  ADD COLUMN IF NOT EXISTS agent_wallet_key_ref text,
  ADD COLUMN IF NOT EXISTS agent_wallet_solana_key_ref text,
  ADD COLUMN IF NOT EXISTS agent_wallet_created_at timestamptz;

-- PostgreSQL has no ADD CONSTRAINT IF NOT EXISTS, so idempotence is explicit — the same pattern this
-- repo already uses for policies in 2026-07-27-lm-financial-reports.sql.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_users'::regclass
      AND conname = 'lm_users_agent_wallet_solana_address_check'
  ) THEN
    ALTER TABLE public.lm_users
      ADD CONSTRAINT lm_users_agent_wallet_solana_address_check CHECK (
        agent_wallet_solana_address IS NULL
        OR agent_wallet_solana_address ~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$'
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_users'::regclass
      AND conname = 'lm_users_agent_wallet_key_ref_check'
  ) THEN
    ALTER TABLE public.lm_users
      ADD CONSTRAINT lm_users_agent_wallet_key_ref_check CHECK (
        agent_wallet_key_ref IS NULL
        OR (
          agent_wallet_key_ref ~ '^secret://[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)+$'
          AND agent_wallet_key_ref !~ '^0[xX]'
          AND agent_wallet_key_ref !~ '[0-9a-fA-F]{64}'
          AND agent_wallet_key_ref !~ '[1-9A-HJ-NP-Za-km-z]{80,}'
          AND char_length(agent_wallet_key_ref) BETWEEN 12 AND 200
        )
      );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_users'::regclass
      AND conname = 'lm_users_agent_wallet_solana_key_ref_check'
  ) THEN
    ALTER TABLE public.lm_users
      ADD CONSTRAINT lm_users_agent_wallet_solana_key_ref_check CHECK (
        agent_wallet_solana_key_ref IS NULL
        OR (
          agent_wallet_solana_key_ref ~ '^secret://[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)+$'
          AND agent_wallet_solana_key_ref !~ '^0[xX]'
          AND agent_wallet_solana_key_ref !~ '[0-9a-fA-F]{64}'
          AND agent_wallet_solana_key_ref !~ '[1-9A-HJ-NP-Za-km-z]{80,}'
          AND char_length(agent_wallet_solana_key_ref) BETWEEN 12 AND 200
        )
      );
  END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS lm_users_agent_wallet_solana_address_key
  ON public.lm_users (agent_wallet_solana_address)
  WHERE agent_wallet_solana_address IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS lm_users_agent_wallet_key_ref_key
  ON public.lm_users (agent_wallet_key_ref)
  WHERE agent_wallet_key_ref IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS lm_users_agent_wallet_solana_key_ref_key
  ON public.lm_users (agent_wallet_solana_key_ref)
  WHERE agent_wallet_solana_key_ref IS NOT NULL;
