-- One redacted Alpaca paper-loop projection for the public dashboard.  The exact id check keeps
-- this boundary to one row; the raw Mac state remains local to the investment loop.
CREATE TABLE IF NOT EXISTS public.lm_alpaca_public_snapshot (
  id text PRIMARY KEY CHECK (id = 'alpaca-hackathon'),
  projection jsonb NOT NULL CHECK (jsonb_typeof(projection) = 'object'),
  observed_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

ALTER TABLE public.lm_alpaca_public_snapshot ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.lm_alpaca_public_snapshot FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.lm_alpaca_public_snapshot TO service_role;
REVOKE DELETE ON TABLE public.lm_alpaca_public_snapshot FROM service_role;
