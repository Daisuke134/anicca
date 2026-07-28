-- FIN-c: allow independently verified Solana receipts alongside the existing EVM receipts.
--
-- This migration changes constraints only. Existing append-only rows are never rewritten, and the
-- original EIP-55/EVM shapes remain accepted.
ALTER TABLE public.lm_agent_earnings
  DROP CONSTRAINT IF EXISTS lm_agent_earnings_wallet_address_check,
  DROP CONSTRAINT IF EXISTS lm_agent_earnings_tx_hash_check;

ALTER TABLE public.lm_agent_earnings
  ADD CONSTRAINT lm_agent_earnings_wallet_address_check CHECK (
    wallet_address ~ '^0x[0-9a-fA-F]{40}$'
    OR wallet_address ~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$'
  ) NOT VALID,
  ADD CONSTRAINT lm_agent_earnings_tx_hash_check CHECK (
    tx_hash IS NULL
    OR tx_hash ~ '^0x[0-9a-fA-F]{64}$'
    OR tx_hash ~ '^[1-9A-HJ-NP-Za-km-z]{87,88}$'
  ) NOT VALID;

ALTER TABLE public.lm_agent_earnings
  VALIDATE CONSTRAINT lm_agent_earnings_wallet_address_check,
  VALIDATE CONSTRAINT lm_agent_earnings_tx_hash_check;
