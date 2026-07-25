-- FIN-c: the agent's own earnings ledger on the crypto rail (spec 9.8).
--
-- Additive only: nothing existing is altered or dropped. This sits alongside lm_score_outcomes rather
-- than inside it, because that table is scoped to a user and this one is scoped to a wallet — the
-- agent earns before it knows whose month it is reporting.
--
-- Append-only is enforced by the engine, not by convention. A monthly report is a claim about money,
-- and a claim is only evidence if the rows behind it could not have been edited after the fact.
CREATE TABLE IF NOT EXISTS public.lm_agent_earnings (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  -- The agent wallet the money moved through, checksummed exactly as the chain writes it.
  wallet_address text NOT NULL CHECK (wallet_address ~ '^0x[0-9a-fA-F]{40}$'),
  -- Caller-supplied idempotency key. The earn loop retries; revenue must not be booked twice.
  entry_key text NOT NULL CHECK (char_length(entry_key) BETWEEN 1 AND 256),
  -- Same vocabulary as lm_score_outcomes, so the panel score and the monthly report cannot drift apart.
  kind text NOT NULL CHECK (kind IN (
    'financial_external_income',
    'financial_realized_loss',
    'financial_fee',
    'financial_user_transfer',
    'financial_self_funding',
    'financial_deposit',
    'financial_internal_move',
    'financial_unverified'
  )),
  -- Whole, non-negative minor units. Direction is carried by the kind: a stored negative amount is the
  -- easiest way to book a loss as income by accident, and a fractional cent cannot be reconciled
  -- against a block explorer.
  amount_minor numeric NOT NULL CHECK (
    amount_minor = trunc(amount_minor) AND amount_minor >= 0 AND amount_minor <= 9007199254740991
  ),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  occurred_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  tx_hash text CHECK (tx_hash IS NULL OR tx_hash ~ '^0x[0-9a-fA-F]{64}$'),
  source text,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(meta) = 'object'),
  UNIQUE (wallet_address, entry_key)
);

CREATE INDEX IF NOT EXISTS lm_agent_earnings_month_idx
  ON public.lm_agent_earnings (wallet_address, occurred_at, kind);

ALTER TABLE public.lm_agent_earnings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_agent_earnings' AND policyname = 'lm_agent_earnings_service_select') THEN
    CREATE POLICY lm_agent_earnings_service_select ON public.lm_agent_earnings FOR SELECT TO service_role USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'lm_agent_earnings' AND policyname = 'lm_agent_earnings_service_insert') THEN
    CREATE POLICY lm_agent_earnings_service_insert ON public.lm_agent_earnings FOR INSERT TO service_role WITH CHECK (true);
  END IF;
END $$;

REVOKE ALL ON TABLE public.lm_agent_earnings FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_agent_earnings TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_agent_earnings FROM service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_agent_earnings_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_agent_earnings is append-only' USING ERRCODE = '55000';
END;
$$;

DROP TRIGGER IF EXISTS lm_agent_earnings_append_only ON public.lm_agent_earnings;
CREATE TRIGGER lm_agent_earnings_append_only
BEFORE UPDATE OR DELETE ON public.lm_agent_earnings
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_agent_earnings_mutation();

REVOKE ALL ON FUNCTION public.reject_lm_agent_earnings_mutation() FROM PUBLIC, anon, authenticated;
