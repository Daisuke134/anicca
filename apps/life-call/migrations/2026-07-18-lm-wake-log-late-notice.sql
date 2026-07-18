ALTER TABLE lm_wake_log ADD COLUMN IF NOT EXISTS answered_at timestamptz;
ALTER TABLE lm_wake_log ADD COLUMN IF NOT EXISTS notified_late_at timestamptz;
