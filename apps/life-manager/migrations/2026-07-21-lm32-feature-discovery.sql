-- LM-32 weekly context-gate discovery state. Additive and idempotent so FIN can
-- reuse payout_destination when its registration flow ships.
ALTER TABLE public.lm_users
  ADD COLUMN IF NOT EXISTS last_discovery_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_discovery_gate text,
  ADD COLUMN IF NOT EXISTS payout_destination jsonb;
