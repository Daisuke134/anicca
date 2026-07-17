-- personhood_nullifiers — World ID sybil gate for the /income UBI claim (#36).
-- One human = at most one queued recipient. The UNIQUE(nullifier_hash, action) constraint is the
-- ATOMIC guard: income-signup inserts the nullifier in the SAME server call that records the
-- recipient; a duplicate INSERT returns 409 -> already_claimed (closes the TOCTOU race). This file
-- MUST be applied in the Supabase SQL editor for the dedup to be enforced (VCSDD round-2 NEW-001) —
-- without the UNIQUE index the atomic block fails open.

create table if not exists personhood_nullifiers (
  id             bigint generated always as identity primary key,
  nullifier_hash text not null,
  action         text not null,
  signal         text,
  created_at     timestamptz not null default now(),
  unique (nullifier_hash, action)
);

-- defense-in-depth (the table-level UNIQUE above is the real guard; this is explicit + named):
create unique index if not exists personhood_nullifiers_hash_action_key
  on personhood_nullifiers (nullifier_hash, action);
