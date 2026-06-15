-- owners — paying customers whose Stripe subscription spawned a cloud Anicca droplet.
-- Written by netlify/functions/stripe-spawn-webhook.js on checkout.session.completed,
-- patched to status='destroyed' on customer.subscription.deleted.
-- See netlify/functions/_lib/owners-store.js (upsertOwner / getOwnerBySub / markDestroyed).
create table if not exists owners (
  sub_id text primary key,               -- Stripe subscription id (stable across events)
  email text,                            -- customer email from the checkout session
  droplet_id text,                       -- DigitalOcean droplet id (text; null until provisioned)
  status text not null default 'active', -- active | destroyed
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
-- RLS: service-role key bypasses RLS, so no policy needed for the function. Keep RLS enabled
-- so the anon key cannot read/write directly.
alter table owners enable row level security;
