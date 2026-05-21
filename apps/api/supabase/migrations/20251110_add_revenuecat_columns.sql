ALTER TABLE public.user_subscriptions
  ADD COLUMN IF NOT EXISTS entitlement_source text DEFAULT 'stripe',
  ADD COLUMN IF NOT EXISTS revenuecat_entitlement_id text,
  ADD COLUMN IF NOT EXISTS revenuecat_original_transaction_id text,
  ADD COLUMN IF NOT EXISTS entitlement_payload jsonb,
  ADD COLUMN IF NOT EXISTS management_url text;

ALTER TABLE public.subscription_events
  ADD COLUMN IF NOT EXISTS provider text DEFAULT 'stripe';


