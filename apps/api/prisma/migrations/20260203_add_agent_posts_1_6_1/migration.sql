-- 1.6.1 Anicca in the World: AgentPost + AgentAuditLog

-- AgentPost table
CREATE TABLE IF NOT EXISTS agent_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL,
  external_post_id VARCHAR(255),
  platform_user_id VARCHAR(255),
  severity VARCHAR(20),
  region VARCHAR(10),
  hook TEXT,
  content TEXT,
  tone VARCHAR(50),
  problem_type VARCHAR(100),
  reasoning TEXT,
  buddhism_reference TEXT,
  upvotes INTEGER NOT NULL DEFAULT 0,
  reactions JSONB NOT NULL DEFAULT '{}',
  views INTEGER,  -- nullable: null = unknown/not available (for Moltbook Z-Score fallback)
  likes INTEGER NOT NULL DEFAULT 0,
  shares INTEGER NOT NULL DEFAULT 0,
  comments INTEGER NOT NULL DEFAULT 0,
  moltbook_z DOUBLE PRECISION,
  slack_z DOUBLE PRECISION,
  tiktok_z DOUBLE PRECISION,
  x_z DOUBLE PRECISION,
  instagram_z DOUBLE PRECISION,
  unified_score DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  promoted_to_hook_candidates BOOLEAN NOT NULL DEFAULT FALSE,
  anonymized_at TIMESTAMPTZ,
  UNIQUE (platform, external_post_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_posts_platform ON agent_posts(platform);
CREATE INDEX IF NOT EXISTS idx_agent_posts_created_at ON agent_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_posts_platform_user_id ON agent_posts(platform_user_id);

-- AgentAuditLog table
CREATE TABLE IF NOT EXISTS agent_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type VARCHAR(50) NOT NULL,
  agent_post_id UUID,
  platform VARCHAR(50),
  request_payload JSONB,
  response_payload JSONB,
  executed_by VARCHAR(100),
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_event_type ON agent_audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_created_at ON agent_audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_agent_post_id ON agent_audit_logs(agent_post_id);

-- HookCandidate extensions for 1.6.1 (Moltbook/Slack metrics)
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS moltbook_upvote_rate DECIMAL(5,4);
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS moltbook_sample_size INTEGER;
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS moltbook_high_performer BOOLEAN;
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS slack_reaction_rate DECIMAL(5,4);
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS slack_sample_size INTEGER;
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS slack_high_performer BOOLEAN;
