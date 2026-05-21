-- Migration: Create mobile VoIP-related tables
-- Date: 2025-01-08
-- Description: Creates tables for VoIP token storage and alarm scheduling

-- Create mobile_voip_tokens table
CREATE TABLE IF NOT EXISTS mobile_voip_tokens (
  user_id TEXT NOT NULL,
  device_token TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, device_token)
);

-- Create mobile_alarm_schedules table
CREATE TABLE IF NOT EXISTS mobile_alarm_schedules (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  habit_type TEXT NOT NULL,
  fire_time TIMESTAMPTZ NOT NULL,
  timezone TEXT NOT NULL,
  repeat_rule TEXT NOT NULL DEFAULT 'daily',
  next_fire_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_mobile_alarm_schedules_user 
ON mobile_alarm_schedules(user_id);

CREATE INDEX IF NOT EXISTS idx_mobile_alarm_schedules_next_fire 
ON mobile_alarm_schedules(next_fire_at);

COMMENT ON TABLE mobile_voip_tokens IS 'Stores VoIP push tokens for iOS devices';
COMMENT ON TABLE mobile_alarm_schedules IS 'Stores scheduled VoIP alarm times for habit routines (wake, training, bedtime)';



