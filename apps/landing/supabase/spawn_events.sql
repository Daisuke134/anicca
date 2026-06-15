-- spawn_events — Stripe event.id idempotency ledger for the spawn webhook.
-- A row is inserted (markEventSeen) only AFTER the side effect (droplet create/destroy) succeeds,
-- so a crashed spawn is retried by Stripe rather than silently lost.
-- See netlify/functions/_lib/owners-store.js (isEventSeen / markEventSeen).
create table if not exists spawn_events (
  event_id text primary key,             -- Stripe event.id
  seen_at timestamptz not null default now()
);
-- RLS: service-role key bypasses RLS, so no policy needed for the function. Keep RLS enabled
-- so the anon key cannot read/write directly.
alter table spawn_events enable row level security;
