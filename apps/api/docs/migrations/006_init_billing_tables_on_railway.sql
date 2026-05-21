-- Create core billing tables on Railway Postgres
create table if not exists public.user_subscriptions (
  user_id text primary key,
  plan text not null default 'free',
  status text not null default 'free',
  stripe_customer_id text,
  stripe_subscription_id text,
  entitlement_source text not null default 'revenuecat',
  revenuecat_entitlement_id text,
  revenuecat_original_transaction_id text,
  entitlement_payload jsonb,
  current_period_end timestamptz,
  trial_end timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.realtime_usage_daily (
  user_id text not null,
  usage_date date not null,
  count integer not null default 0,
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (user_id, usage_date)
);

create table if not exists public.subscription_events (
  event_id text primary key,
  user_id text,
  type text not null,
  provider text not null default 'revenuecat',
  payload jsonb,
  created_at timestamptz not null default timezone('utc', now())
);


