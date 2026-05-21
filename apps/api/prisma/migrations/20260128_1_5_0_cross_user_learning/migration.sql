-- 1.5.0 Cross-User Learning Migration
-- Run: psql $DATABASE_URL -f migration.sql
-- Or: npx prisma db execute --file prisma/migrations/20260128_1_5_0_cross_user_learning/migration.sql

-- Ensure pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1. user_type_estimates
-- ============================================================
CREATE TABLE IF NOT EXISTS user_type_estimates (
  user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  primary_type VARCHAR(10) NOT NULL
    CHECK (primary_type IN ('T1', 'T2', 'T3', 'T4')),
  type_scores JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_type_estimates_primary ON user_type_estimates(primary_type);

-- ============================================================
-- 2. type_stats (BIGINT counts per Section 6.2)
-- ============================================================
CREATE TABLE IF NOT EXISTS type_stats (
  type_id VARCHAR(10) NOT NULL
    CHECK (type_id IN ('T1', 'T2', 'T3', 'T4')),
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),
  tapped_count BIGINT NOT NULL DEFAULT 0 CHECK (tapped_count >= 0),
  ignored_count BIGINT NOT NULL DEFAULT 0 CHECK (ignored_count >= 0),
  thumbs_up_count BIGINT NOT NULL DEFAULT 0 CHECK (thumbs_up_count >= 0),
  thumbs_down_count BIGINT NOT NULL DEFAULT 0 CHECK (thumbs_down_count >= 0),
  sample_size BIGINT NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
  tap_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN sample_size > 0 THEN tapped_count::NUMERIC / sample_size ELSE 0 END
  ) STORED,
  thumbs_up_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN tapped_count > 0 THEN thumbs_up_count::NUMERIC / tapped_count ELSE 0 END
  ) STORED,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (type_id, tone),
  CONSTRAINT chk_sample_size_consistency CHECK (sample_size = tapped_count + ignored_count),
  CONSTRAINT chk_thumbs_up_le_tapped CHECK (thumbs_up_count <= tapped_count),
  CONSTRAINT chk_thumbs_down_le_tapped CHECK (thumbs_down_count <= tapped_count),
  CONSTRAINT chk_thumbs_total_le_tapped CHECK (thumbs_up_count + thumbs_down_count <= tapped_count)
);

-- ============================================================
-- 3. hook_candidates
-- ============================================================
CREATE TABLE IF NOT EXISTS hook_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  text TEXT NOT NULL,
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),
  UNIQUE (text, tone),
  target_problem_types TEXT[] NOT NULL DEFAULT '{}',
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  CONSTRAINT chk_hook_candidates_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  CONSTRAINT chk_hook_candidates_problem_types CHECK (
    target_problem_types <@ ARRAY['self_loathing','procrastination','rumination','staying_up_late','porn_addiction','anxiety','cant_wake_up','lying','bad_mouthing','alcohol_dependency','anger','obsessive','loneliness']::text[]
  ),
  app_tap_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_tap_rate >= 0 AND app_tap_rate <= 1),
  app_thumbs_up_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_thumbs_up_rate >= 0 AND app_thumbs_up_rate <= 1),
  app_sample_size INT NOT NULL DEFAULT 0 CHECK (app_sample_size >= 0),
  tiktok_like_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_like_rate >= 0 AND tiktok_like_rate <= 1),
  tiktok_share_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_share_rate >= 0 AND tiktok_share_rate <= 1),
  tiktok_sample_size INT NOT NULL DEFAULT 0 CHECK (tiktok_sample_size >= 0),
  tiktok_high_performer BOOLEAN NOT NULL DEFAULT FALSE,
  is_wisdom BOOLEAN NOT NULL DEFAULT FALSE,
  exploration_weight NUMERIC(3,2) NOT NULL DEFAULT 1.0 CHECK (exploration_weight >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hook_candidates_wisdom ON hook_candidates(is_wisdom) WHERE is_wisdom = TRUE;
CREATE INDEX IF NOT EXISTS idx_hook_candidates_high_performer ON hook_candidates(tiktok_high_performer) WHERE tiktok_high_performer = TRUE;
CREATE INDEX IF NOT EXISTS idx_hook_candidates_target_types ON hook_candidates USING GIN(target_user_types);
CREATE INDEX IF NOT EXISTS idx_hook_candidates_target_problems ON hook_candidates USING GIN(target_problem_types);
CREATE INDEX IF NOT EXISTS idx_hook_candidates_tone ON hook_candidates(tone);

-- ============================================================
-- 4. tiktok_posts
-- ============================================================
CREATE TABLE IF NOT EXISTS tiktok_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hook_candidate_id UUID REFERENCES hook_candidates(id),
  tiktok_video_id VARCHAR(100) UNIQUE,
  blotato_post_id VARCHAR(100),
  caption TEXT,
  posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metrics_fetched_at TIMESTAMPTZ,
  view_count BIGINT CHECK (view_count IS NULL OR view_count >= 0),
  like_count BIGINT CHECK (like_count IS NULL OR like_count >= 0),
  comment_count BIGINT CHECK (comment_count IS NULL OR comment_count >= 0),
  share_count BIGINT CHECK (share_count IS NULL OR share_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_metrics_consistency CHECK (
    (metrics_fetched_at IS NULL AND view_count IS NULL AND like_count IS NULL AND comment_count IS NULL AND share_count IS NULL)
    OR (metrics_fetched_at IS NOT NULL AND view_count IS NOT NULL AND like_count IS NOT NULL AND comment_count IS NOT NULL AND share_count IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_tiktok_posts_hook ON tiktok_posts(hook_candidate_id);
CREATE INDEX IF NOT EXISTS idx_tiktok_posts_posted_at ON tiktok_posts(posted_at DESC);

-- ============================================================
-- 5. wisdom_patterns
-- ============================================================
CREATE TABLE IF NOT EXISTS wisdom_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name VARCHAR(100) NOT NULL,
  description TEXT,
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  CONSTRAINT chk_wisdom_patterns_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  effective_tone VARCHAR(20)
    CHECK (effective_tone IS NULL OR effective_tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),
  effective_hook_pattern TEXT,
  effective_content_length VARCHAR(20)
    CHECK (effective_content_length IS NULL OR effective_content_length IN ('short', 'medium', 'long')),
  app_evidence JSONB NOT NULL DEFAULT '{}',
  tiktok_evidence JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),
  verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wisdom_patterns_types ON wisdom_patterns USING GIN(target_user_types);

-- ============================================================
-- 6. Performance indexes on existing tables (Section 6.1)
-- ============================================================

-- aggregateTypeStats: domain + user_type filter
CREATE INDEX IF NOT EXISTS idx_nudge_events_domain_user_type
  ON nudge_events(domain)
  WHERE (state->>'user_type') IS NOT NULL;

-- initHookLibrary: domain + hook filter
CREATE INDEX IF NOT EXISTS idx_nudge_events_domain_hook
  ON nudge_events(domain)
  WHERE (state->>'hook') IS NOT NULL;

-- FK index on nudge_outcomes.nudge_event_id (PostgreSQL doesn't auto-index FKs)
CREATE INDEX IF NOT EXISTS idx_nudge_outcomes_event_id ON nudge_outcomes(nudge_event_id);
