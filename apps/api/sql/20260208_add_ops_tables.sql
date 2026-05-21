-- migration: 20260208_add_ops_tables.sql
-- Adds 7 ops tables for closed-loop operations

-- 1. ops_proposals
CREATE TABLE IF NOT EXISTS ops_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_name VARCHAR(50) NOT NULL,
  source VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  title VARCHAR(500) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  reject_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_proposals_status ON ops_proposals (status);
CREATE INDEX IF NOT EXISTS idx_ops_proposals_skill_name ON ops_proposals (skill_name);
CREATE INDEX IF NOT EXISTS idx_ops_proposals_created_at ON ops_proposals (created_at DESC);

-- 2. ops_missions
CREATE TABLE IF NOT EXISTS ops_missions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES ops_proposals(id) ON DELETE CASCADE,
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_missions_status ON ops_missions (status);
CREATE INDEX IF NOT EXISTS idx_ops_missions_created_at ON ops_missions (created_at DESC);

-- 3. ops_mission_steps
CREATE TABLE IF NOT EXISTS ops_mission_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES ops_missions(id) ON DELETE CASCADE,
  step_kind VARCHAR(50) NOT NULL,
  step_order INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'queued',
  input JSONB,
  output JSONB,
  last_error TEXT,
  reserved_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_mission_order ON ops_mission_steps (mission_id, step_order);
CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_status ON ops_mission_steps (status);
CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_reserved_at ON ops_mission_steps (reserved_at);

-- 4. ops_events
CREATE TABLE IF NOT EXISTS ops_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  kind VARCHAR(100) NOT NULL,
  tags TEXT[] DEFAULT '{}',
  payload JSONB,
  mission_id UUID REFERENCES ops_missions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ops_events_kind ON ops_events (kind);
CREATE INDEX IF NOT EXISTS idx_ops_events_source ON ops_events (source);
CREATE INDEX IF NOT EXISTS idx_ops_events_created_at ON ops_events (created_at DESC);

-- 5. ops_policy
CREATE TABLE IF NOT EXISTS ops_policy (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. ops_trigger_rules
CREATE TABLE IF NOT EXISTS ops_trigger_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) UNIQUE NOT NULL,
  event_kind VARCHAR(100) NOT NULL,
  condition JSONB NOT NULL DEFAULT '{}',
  proposal_template JSONB NOT NULL,
  cooldown_min INT NOT NULL DEFAULT 60,
  enabled BOOLEAN NOT NULL DEFAULT true,
  last_fired_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ops_trigger_rules_event_kind ON ops_trigger_rules (event_kind);

-- 7. ops_reactions
CREATE TABLE IF NOT EXISTS ops_reactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES ops_events(id) ON DELETE CASCADE,
  target_skill VARCHAR(50) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_reactions_status ON ops_reactions (status);
CREATE INDEX IF NOT EXISTS idx_ops_reactions_created_at ON ops_reactions (created_at DESC);

-- 8. HookCandidate extensions (1.6.2)
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS platform VARCHAR(20);
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS content_type VARCHAR(20);
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128) UNIQUE;
ALTER TABLE hook_candidates ADD COLUMN IF NOT EXISTS metadata JSONB;
