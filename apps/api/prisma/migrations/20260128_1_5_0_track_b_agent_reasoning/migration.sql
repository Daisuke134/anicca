-- Track B: Add agent_reasoning column to tiktok_posts
-- Stores the LLM agent's reasoning for each post decision
ALTER TABLE tiktok_posts ADD COLUMN IF NOT EXISTS agent_reasoning TEXT;

-- One-post-per-day constraint (prevents TOCTOU race condition)
CREATE UNIQUE INDEX IF NOT EXISTS idx_tiktok_posts_one_per_day
  ON tiktok_posts (DATE(posted_at AT TIME ZONE 'UTC'));
