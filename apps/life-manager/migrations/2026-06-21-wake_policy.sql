-- #69 wake/travel importance filter — per-user wake policy.
-- 'travel-only' (default): only call for events the user must travel to (location ≠ home).
-- 'all-events': call for every timed commitment (opt-in to the original behavior).
-- Applied to the live Supabase (project cycgdwndgfgdbnndithc) via the Management API on 2026-06-21.
ALTER TABLE lm_users
  ADD COLUMN IF NOT EXISTS wake_policy text NOT NULL DEFAULT 'travel-only';
