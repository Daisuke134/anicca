-- Migration: Create mobile_profiles table for user personalization data
-- Date: 2025-01-XX

CREATE TABLE IF NOT EXISTS mobile_profiles (
    device_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    profile JSONB NOT NULL DEFAULT '{}',
    language TEXT NOT NULL DEFAULT 'en',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mobile_profiles_user_id ON mobile_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_mobile_profiles_updated_at ON mobile_profiles(updated_at);

COMMENT ON TABLE mobile_profiles IS 'Stores personalization data for iOS app users';
COMMENT ON COLUMN mobile_profiles.device_id IS 'Unique device identifier (UUID)';
COMMENT ON COLUMN mobile_profiles.user_id IS 'User ID from authentication system';
COMMENT ON COLUMN mobile_profiles.profile IS 'JSONB object containing user profile data (displayName, sleepLocation, trainingFocus, etc.)';
COMMENT ON COLUMN mobile_profiles.language IS 'Preferred language code (ja, en, etc.)';




