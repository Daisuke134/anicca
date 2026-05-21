-- Allow 2 TikTok posts per day (morning + evening slots)
-- Removes the one-per-day constraint added in 1.5.0

DROP INDEX IF EXISTS idx_tiktok_posts_one_per_day;
