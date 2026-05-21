-- 1.6.2 Closed-Loop Ops: core tables

CREATE TABLE IF NOT EXISTS ops_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_name VARCHAR(50) NOT NULL,
  source VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  title VARCHAR(500) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  reject_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_proposals_status ON ops_proposals(status);
CREATE INDEX IF NOT EXISTS idx_ops_proposals_skill_name ON ops_proposals(skill_name);
CREATE INDEX IF NOT EXISTS idx_ops_proposals_created_at ON ops_proposals(created_at DESC);

CREATE TABLE IF NOT EXISTS ops_missions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_missions_status ON ops_missions(status);
CREATE INDEX IF NOT EXISTS idx_ops_missions_created_at ON ops_missions(created_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ops_missions_proposal_id_fkey'
  ) THEN
    ALTER TABLE ops_missions
    ADD CONSTRAINT ops_missions_proposal_id_fkey
    FOREIGN KEY (proposal_id) REFERENCES ops_proposals(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS ops_mission_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL,
  step_kind VARCHAR(50) NOT NULL,
  step_order INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'queued',
  input JSONB,
  output JSONB,
  last_error TEXT,
  reserved_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_mission_order ON ops_mission_steps(mission_id, step_order);
CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_status ON ops_mission_steps(status);
CREATE INDEX IF NOT EXISTS idx_ops_mission_steps_reserved_at ON ops_mission_steps(reserved_at);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ops_mission_steps_mission_id_fkey'
  ) THEN
    ALTER TABLE ops_mission_steps
    ADD CONSTRAINT ops_mission_steps_mission_id_fkey
    FOREIGN KEY (mission_id) REFERENCES ops_missions(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS ops_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  kind VARCHAR(100) NOT NULL,
  tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  payload JSONB,
  mission_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ops_events_kind ON ops_events(kind);
CREATE INDEX IF NOT EXISTS idx_ops_events_source ON ops_events(source);
CREATE INDEX IF NOT EXISTS idx_ops_events_created_at ON ops_events(created_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ops_events_mission_id_fkey'
  ) THEN
    ALTER TABLE ops_events
    ADD CONSTRAINT ops_events_mission_id_fkey
    FOREIGN KEY (mission_id) REFERENCES ops_missions(id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS ops_policy (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops_trigger_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL UNIQUE,
  event_kind VARCHAR(100) NOT NULL,
  condition JSONB NOT NULL DEFAULT '{}',
  proposal_template JSONB NOT NULL,
  cooldown_min INTEGER NOT NULL DEFAULT 60,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  last_fired_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ops_trigger_rules_event_kind ON ops_trigger_rules(event_kind);

CREATE TABLE IF NOT EXISTS ops_reactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL,
  target_skill VARCHAR(50) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ops_reactions_status ON ops_reactions(status);
CREATE INDEX IF NOT EXISTS idx_ops_reactions_created_at ON ops_reactions(created_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ops_reactions_event_id_fkey'
  ) THEN
    ALTER TABLE ops_reactions
    ADD CONSTRAINT ops_reactions_event_id_fkey
    FOREIGN KEY (event_id) REFERENCES ops_events(id) ON DELETE CASCADE;
  END IF;
END $$;
