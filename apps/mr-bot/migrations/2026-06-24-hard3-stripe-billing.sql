-- HARD-3: Stripe lifecycle = billing source of truth. The webhook (lib/billing.js) is the SINGLE writer
-- of lm_users.paid; the HARD-2 sweeper (paid=is.true) is its only reader. Idempotent + out-of-order-safe.
-- Re-runnable (IF NOT EXISTS everywhere).

-- 1) lm_users: billing columns (paid already exists as the entitlement gate). All nullable / default-safe.
ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS stripe_customer_id     text;
ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS stripe_subscription_id text;
ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS plan_status            text;       -- mirrors Stripe subscription.status
ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS current_period_end     timestamptz; -- the subscription's period end (data)
ALTER TABLE public.lm_users ADD COLUMN IF NOT EXISTS stripe_event_at        timestamptz; -- created of the last applied event = the out-of-order staleness key (FIND-002)

-- One Stripe customer maps to at most one user (subscription.* events look up the uid by this).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'lm_users_stripe_customer_id_key') THEN
    ALTER TABLE public.lm_users ADD CONSTRAINT lm_users_stripe_customer_id_key UNIQUE (stripe_customer_id);
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS lm_users_stripe_customer_idx ON public.lm_users (stripe_customer_id);

-- 2) lm_stripe_events: idempotency ledger. A claim is an INSERT; the PK makes a duplicate delivery 409.
CREATE TABLE IF NOT EXISTS public.lm_stripe_events (
  event_id    text        PRIMARY KEY,             -- Stripe evt_... id (deduped at most once)
  type        text,
  received_at timestamptz NOT NULL DEFAULT now()
);

-- RLS: the webhook uses the service-role key (bypasses RLS); enabling it blocks the anon key.
ALTER TABLE public.lm_stripe_events ENABLE ROW LEVEL SECURITY;
