-- Fleet-identity fields for the realtime dashboard (applied 2026-06-29 via Supabase Management API).
-- Additive + idempotent. `log` (jsonb) already exists. PK id = wallet address.
ALTER TABLE instances ADD COLUMN IF NOT EXISTS funding text;  -- 'human' | 'self'
ALTER TABLE instances ADD COLUMN IF NOT EXISTS env text;      -- 'local' | 'cloud'
ALTER TABLE instances ADD COLUMN IF NOT EXISTS brain text;    -- 'claude-p' | 'proxy'
