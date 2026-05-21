-- Migration: Create VoIP push tokens and alarm schedules tables
-- Run this migration on Railway PostgreSQL

CREATE TABLE IF NOT EXISTS mobile_voip_tokens (
  user_id TEXT NOT NULL,
  device_token TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, device_token)
);

CREATE INDEX IF NOT EXISTS idx_mobile_voip_tokens_user_id ON mobile_voip_tokens(user_id);

CREATE TABLE IF NOT EXISTS mobile_alarm_schedules (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  habit_type TEXT NOT NULL,
  fire_time TIMESTAMPTZ NOT NULL,
  timezone TEXT NOT NULL,
  repeat_rule TEXT NOT NULL DEFAULT 'daily',
  next_fire_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mobile_alarm_schedules_user_id ON mobile_alarm_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_mobile_alarm_schedules_next_fire_at ON mobile_alarm_schedules(next_fire_at);



