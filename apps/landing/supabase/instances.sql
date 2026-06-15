create table if not exists instances (
  id text primary key,                -- wallet address (lowercase)
  ts bigint not null,                 -- last accepted unix ts (monotonic)
  host text not null, geo text not null,
  model_live text not null, model_tier text not null,
  net_worth_usd double precision not null, revenue_mo_usd double precision not null,
  burn_day_usd double precision not null, runway_days int not null,
  status text not null, updated_at timestamptz not null default now()
);
-- RLS: service-role key bypasses RLS, so no policy needed for the function. Keep RLS enabled
-- so the anon key cannot read/write directly.
alter table instances enable row level security;
