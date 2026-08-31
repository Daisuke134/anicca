-- Preserve sub-cent USDC settlements exactly without rewriting any append-only earning row.
ALTER TABLE public.lm_agent_earnings
  ADD COLUMN IF NOT EXISTS amount_atomic numeric,
  ADD COLUMN IF NOT EXISTS amount_decimals smallint;

ALTER TABLE public.lm_agent_earnings
  ALTER COLUMN amount_minor DROP NOT NULL,
  DROP CONSTRAINT IF EXISTS lm_agent_earnings_amount_minor_check;

ALTER TABLE public.lm_agent_earnings
  ADD CONSTRAINT lm_agent_earnings_amount_minor_check CHECK (
    amount_minor IS NULL OR (
      amount_minor = trunc(amount_minor)
      AND amount_minor >= 0
      AND amount_minor <= 9007199254740991
    )
  ) NOT VALID,
  ADD CONSTRAINT lm_agent_earnings_amount_atomic_check CHECK (
    amount_atomic IS NULL OR (
      amount_atomic = trunc(amount_atomic)
      AND amount_atomic >= 0
      AND amount_atomic <= 90071992547409910000
    )
  ) NOT VALID,
  ADD CONSTRAINT lm_agent_earnings_amount_representation_check CHECK (
    (amount_minor IS NOT NULL AND amount_atomic IS NULL AND amount_decimals IS NULL)
    OR
    (amount_minor IS NULL AND amount_atomic IS NOT NULL AND amount_decimals BETWEEN 0 AND 6)
  ) NOT VALID;

ALTER TABLE public.lm_agent_earnings
  VALIDATE CONSTRAINT lm_agent_earnings_amount_minor_check,
  VALIDATE CONSTRAINT lm_agent_earnings_amount_atomic_check,
  VALIDATE CONSTRAINT lm_agent_earnings_amount_representation_check;
