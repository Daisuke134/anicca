-- L1 (#78) — per-user CALL LANGUAGE (Dais 2026-06-22).
-- The user picks their call language on /lm (English / 日本語); it overrides the phone-country default.
-- NULLABLE on purpose: NULL → fall back to langForPhone(phone) (+81 → ja, else en). No default value,
-- so existing users keep the phone-based behavior until they choose.
-- Applied to the live Supabase (project cycgdwndgfgdbnndithc) via the Management API on 2026-06-22.
ALTER TABLE lm_users
  ADD COLUMN IF NOT EXISTS call_language text
  CHECK (call_language IN ('en', 'ja'));
