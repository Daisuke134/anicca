-- REPORT-1: bind a tenant to the public identity of its agent, then persist the
-- exact snapshot sent by each daily/weekly Telegram report.
--
-- Only a public address is stored here. Signing material remains in the
-- protected local wallet used by the payout runtime.
ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS agent_wallet_address text
  CHECK (
    agent_wallet_address IS NULL
    OR agent_wallet_address ~ '^0x[0-9a-fA-F]{40}$'
  );

CREATE UNIQUE INDEX IF NOT EXISTS lm_users_agent_wallet_address_key
  ON public.lm_users (agent_wallet_address)
  WHERE agent_wallet_address IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.lm_financial_report_receipts (
  uid text NOT NULL REFERENCES public.lm_users(uid) ON DELETE CASCADE,
  report_kind text NOT NULL CHECK (report_kind IN ('daily', 'weekly')),
  period_key text NOT NULL CHECK (char_length(period_key) BETWEEN 8 AND 16),
  timezone text NOT NULL CHECK (char_length(timezone) BETWEEN 1 AND 64),
  period_start timestamptz NOT NULL,
  period_end timestamptz NOT NULL CHECK (period_end > period_start),
  snapshot jsonb NOT NULL CHECK (jsonb_typeof(snapshot) = 'object'),
  snapshot_hash text NOT NULL CHECK (
    length(snapshot_hash) = 64 AND snapshot_hash ~ '^[0-9a-f]{64}$'
  ),
  status text NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
  telegram_message_id bigint CHECK (
    telegram_message_id IS NULL OR telegram_message_id > 0
  ),
  failure_code text CHECK (
    failure_code IS NULL OR char_length(failure_code) BETWEEN 1 AND 128
  ),
  attempt_count integer NOT NULL DEFAULT 1 CHECK (attempt_count BETWEEN 1 AND 100),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  sent_at timestamptz,
  PRIMARY KEY (uid, report_kind, period_key),
  CHECK (
    (status = 'sent' AND telegram_message_id IS NOT NULL AND sent_at IS NOT NULL)
    OR (status <> 'sent' AND telegram_message_id IS NULL AND sent_at IS NULL)
  ),
  CHECK (
    (status = 'failed' AND failure_code IS NOT NULL)
    OR (status <> 'failed' AND failure_code IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS lm_financial_report_receipts_latest_idx
  ON public.lm_financial_report_receipts (uid, report_kind, period_end DESC);

ALTER TABLE public.lm_financial_report_receipts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'lm_financial_report_receipts'
      AND policyname = 'lm_financial_report_service_select'
  ) THEN
    CREATE POLICY lm_financial_report_service_select
      ON public.lm_financial_report_receipts
      FOR SELECT TO service_role
      USING (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'lm_financial_report_receipts'
      AND policyname = 'lm_financial_report_service_insert'
  ) THEN
    CREATE POLICY lm_financial_report_service_insert
      ON public.lm_financial_report_receipts
      FOR INSERT TO service_role
      WITH CHECK (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'lm_financial_report_receipts'
      AND policyname = 'lm_financial_report_service_update'
  ) THEN
    CREATE POLICY lm_financial_report_service_update
      ON public.lm_financial_report_receipts
      FOR UPDATE TO service_role
      USING (true)
      WITH CHECK (true);
  END IF;
END
$$;

REVOKE ALL ON TABLE public.lm_financial_report_receipts
  FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_financial_report_receipts
  TO service_role;

-- lm_api_cost is intentionally high-volume. REPORT-1 must not pull every row
-- through PostgREST on each five-minute tick, so PostgreSQL performs the exact
-- tenant-scoped sums and returns only bounded aggregates.
CREATE OR REPLACE FUNCTION public.lm_financial_cost_totals(
  p_uid text,
  p_period_start timestamptz,
  p_period_end timestamptz
) RETURNS TABLE (
  period_est_usd numeric,
  all_time_est_usd numeric,
  period_rows bigint,
  all_time_rows bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT
    COALESCE(sum(est_usd) FILTER (
      WHERE ts >= p_period_start AND ts < p_period_end
    ), 0)::numeric AS period_est_usd,
    COALESCE(sum(est_usd) FILTER (
      WHERE ts < p_period_end
    ), 0)::numeric AS all_time_est_usd,
    count(*) FILTER (
      WHERE ts >= p_period_start AND ts < p_period_end
    )::bigint AS period_rows,
    count(*) FILTER (
      WHERE ts < p_period_end
    )::bigint AS all_time_rows
  FROM public.lm_api_cost
  WHERE lm_api_cost.uid = p_uid
    AND p_period_start < p_period_end;
$$;

REVOKE ALL ON FUNCTION public.lm_financial_cost_totals(text, timestamptz, timestamptz)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_financial_cost_totals(text, timestamptz, timestamptz)
  TO service_role;
