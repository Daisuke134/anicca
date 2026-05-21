# 02 — Data Layer (Schema + Migration + Seeds)

> **元ファイル**: `../closed-loop-ops.md` Section 2-5
> **ナビ**: [← Overview](./01-overview-adr.md) | [README](./README.md) | [次: API Services →](./03-api-services.md)

---

## 2. DB スキーマ（Prisma）

> **規約**: 既存 schema.prisma の規約に完全準拠
> - `@db.Uuid @default(dbgenerated("gen_random_uuid()"))`
> - `@db.Timestamptz @default(now())`
> - `@map("snake_case")`, `@@map("table_names")`
> - FK制約あり（`REFERENCES ... ON DELETE CASCADE`）— 親削除時に子レコードも削除。Prisma `@relation(onDelete: Cascade)` と SQL `REFERENCES` が対応

### 2.1 ops_proposals

```prisma
model OpsProposal {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  skillName   String   @db.VarChar(50) @map("skill_name")
  source      String   @db.VarChar(20) @map("source")
  status      String   @db.VarChar(20) @default("pending")
  title       String   @db.VarChar(500)
  payload     Json     @db.JsonB
  rejectReason String? @db.Text @map("reject_reason")
  createdAt   DateTime @db.Timestamptz @default(now()) @map("created_at")
  resolvedAt  DateTime? @db.Timestamptz @map("resolved_at")

  missions    OpsMission[]

  @@index([status])
  @@index([skillName])
  @@index([createdAt(sort: Desc)])
  @@map("ops_proposals")
}
```

### 2.2 ops_missions

```prisma
model OpsMission {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  proposalId  String   @db.Uuid @map("proposal_id")
  status      String   @db.VarChar(20) @default("running")
  createdAt   DateTime @db.Timestamptz @default(now()) @map("created_at")
  completedAt DateTime? @db.Timestamptz @map("completed_at")

  proposal    OpsProposal @relation(fields: [proposalId], references: [id], onDelete: Cascade)
  steps       OpsMissionStep[]
  events      OpsEvent[]

  @@index([status])
  @@index([createdAt(sort: Desc)])
  @@map("ops_missions")
}
```

### 2.3 ops_mission_steps

```prisma
model OpsMissionStep {
  id          String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  missionId   String    @db.Uuid @map("mission_id")
  stepKind    String    @db.VarChar(50) @map("step_kind")
  stepOrder   Int       @map("step_order")
  status      String    @db.VarChar(20) @default("queued")
  input       Json?     @db.JsonB
  output      Json?     @db.JsonB
  lastError   String?   @db.Text @map("last_error")
  reservedAt  DateTime? @db.Timestamptz @map("reserved_at")
  completedAt DateTime? @db.Timestamptz @map("completed_at")
  createdAt   DateTime  @db.Timestamptz @default(now()) @map("created_at")

  mission     OpsMission @relation(fields: [missionId], references: [id], onDelete: Cascade)

  @@index([missionId, stepOrder])
  @@index([status])
  @@index([reservedAt])
  @@map("ops_mission_steps")
}
```

### 2.4 ops_events

```prisma
model OpsEvent {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  source      String   @db.VarChar(50)
  kind        String   @db.VarChar(100)
  tags        String[] @default([])
  payload     Json?    @db.JsonB
  missionId   String?  @db.Uuid @map("mission_id")
  createdAt   DateTime @db.Timestamptz @default(now()) @map("created_at")

  mission     OpsMission? @relation(fields: [missionId], references: [id], onDelete: SetNull)
  reactions   OpsReaction[]

  @@index([kind])
  @@index([source])
  @@index([createdAt(sort: Desc)])
  @@map("ops_events")
}
```

### 2.5 ops_policy

```prisma
model OpsPolicy {
  key       String   @id @db.VarChar(100)
  value     Json     @db.JsonB
  updatedAt DateTime @db.Timestamptz @default(now()) @updatedAt @map("updated_at")

  @@map("ops_policy")
}
```

### 2.6 ops_trigger_rules

```prisma
model OpsTriggerRule {
  id           String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  name         String   @db.VarChar(100) @unique
  eventKind    String   @db.VarChar(100) @map("event_kind")
  condition    Json     @db.JsonB
  proposalTemplate Json @db.JsonB @map("proposal_template")
  cooldownMin  Int      @default(60) @map("cooldown_min")
  enabled      Boolean  @default(true)
  lastFiredAt  DateTime? @db.Timestamptz @map("last_fired_at")
  createdAt    DateTime @db.Timestamptz @default(now()) @map("created_at")

  @@index([eventKind])
  @@map("ops_trigger_rules")
}
```

### 2.7 ops_reactions

```prisma
model OpsReaction {
  id          String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  eventId     String    @db.Uuid @map("event_id")
  targetSkill String    @db.VarChar(50) @map("target_skill")
  actionType  String    @db.VarChar(50) @map("action_type")
  status      String    @db.VarChar(20) @default("pending")
  createdAt   DateTime  @db.Timestamptz @default(now()) @map("created_at")
  processedAt DateTime? @db.Timestamptz @map("processed_at")

  event       OpsEvent @relation(fields: [eventId], references: [id], onDelete: Cascade)

  @@index([status])
  @@index([createdAt(sort: Desc)])
  @@map("ops_reactions")
}
```

---

## 3. マイグレーション SQL

> **方針**: 既存パターン通り SQL 手動適用 → `prisma db pull` でスキーマ同期
> **既存データへの影響**: なし（全て新規テーブル）

```sql
-- migration: 20260208_add_ops_tables.sql

-- 1. ops_proposals
CREATE TABLE ops_proposals (
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

CREATE INDEX idx_ops_proposals_status ON ops_proposals (status);
CREATE INDEX idx_ops_proposals_skill_name ON ops_proposals (skill_name);
CREATE INDEX idx_ops_proposals_created_at ON ops_proposals (created_at DESC);

-- 2. ops_missions
CREATE TABLE ops_missions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES ops_proposals(id) ON DELETE CASCADE,
  status VARCHAR(20) NOT NULL DEFAULT 'running',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ops_missions_status ON ops_missions (status);
CREATE INDEX idx_ops_missions_created_at ON ops_missions (created_at DESC);

-- 3. ops_mission_steps
CREATE TABLE ops_mission_steps (
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

CREATE INDEX idx_ops_mission_steps_mission_order ON ops_mission_steps (mission_id, step_order);
CREATE INDEX idx_ops_mission_steps_status ON ops_mission_steps (status);
CREATE INDEX idx_ops_mission_steps_reserved_at ON ops_mission_steps (reserved_at);

-- 4. ops_events
CREATE TABLE ops_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  kind VARCHAR(100) NOT NULL,
  tags TEXT[] DEFAULT '{}',
  payload JSONB,
  mission_id UUID REFERENCES ops_missions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ops_events_kind ON ops_events (kind);
CREATE INDEX idx_ops_events_source ON ops_events (source);
CREATE INDEX idx_ops_events_created_at ON ops_events (created_at DESC);

-- 5. ops_policy
CREATE TABLE ops_policy (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. ops_trigger_rules
CREATE TABLE ops_trigger_rules (
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

CREATE INDEX idx_ops_trigger_rules_event_kind ON ops_trigger_rules (event_kind);

-- 7. ops_reactions
CREATE TABLE ops_reactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES ops_events(id) ON DELETE CASCADE,
  target_skill VARCHAR(50) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX idx_ops_reactions_status ON ops_reactions (status);
CREATE INDEX idx_ops_reactions_created_at ON ops_reactions (created_at DESC);
```

---

## 4. Policy シードデータ

```sql
-- seed: 20260208_seed_ops_policy.sql
--
-- P0 #21 解消: cooldown の単位は「分」（evaluateReactionMatrix で `cooldown * 60 * 1000` → ms に変換）
-- 例: cooldown=120 → 120分 = 2時間
-- 例: cooldown=480 → 480分 = 8時間
-- cooldown_min（OpsTriggerRule）も同じ単位（分）

INSERT INTO ops_policy (key, value) VALUES
  ('auto_approve', '{
    "enabled": true,
    "allowed_step_kinds": ["draft_content", "verify_content", "detect_suffering", "analyze_engagement", "fetch_metrics", "diagnose", "draft_nudge", "evaluate_hook"]
  }'),
  ('x_daily_quota', '{ "limit": 3 }'),
  ('tiktok_daily_quota', '{ "limit": 1 }'),
  ('nudge_daily_quota', '{ "limit": 10 }'),
  ('x_autopost', '{ "enabled": true }'),
  ('tiktok_autopost', '{ "enabled": false }'),  -- Phase A では無効。Phase B で UPDATE ... SET enabled=true
  ('worker_policy', '{ "vps_only": true }'),
  ('buddhist_verification', '{ "enabled": true, "min_score": 3, "max_retries": 3 }'),
  ('stale_threshold_min', '{ "value": 30 }'),
  ('reaction_matrix', '{
    "patterns": [
      {
        "source": "x-poster",
        "tags": ["tweet", "posted"],
        "target": "trend-hunter",
        "type": "analyze_engagement",
        "probability": 0.3,
        "cooldown": 120
      },
      {
        "source": "trend-hunter",
        "tags": ["suffering", "detected"],
        "target": "app-nudge-sender",
        "type": "draft_nudge",
        "probability": 0.5,
        "cooldown": 60
      },
      {
        "source": "*",
        "tags": ["mission", "failed"],
        "target": "x-poster",
        "type": "diagnose",
        "probability": 1.0,
        "cooldown": 60
      },
      {
        "source": "trend-hunter",
        "tags": ["hook_candidate", "found"],
        "target": "x-poster",
        "type": "evaluate_hook",
        "probability": 0.5,
        "cooldown": 240,
        "payload_template": { "eventId": "{{id}}" }
      },
      {
        "source": "x-poster",
        "tags": ["engagement", "high"],
        "target": "tiktok-poster",
        "type": "draft_content",
        "probability": 0.4,
        "cooldown": 480
      }
    ]
  }')
ON CONFLICT (key) DO NOTHING;
```

---

## 5. Trigger Rule シードデータ

```sql
-- seed: 20260208_seed_ops_trigger_rules.sql

INSERT INTO ops_trigger_rules (name, event_kind, condition, proposal_template, cooldown_min, enabled) VALUES
  (
    'engagement_analysis_24h',
    'tweet_posted',
    '{ "delay_min": 1440 }',
    '{ "skill_name": "x-poster", "title": "24h後エンゲージメント分析", "steps": [{ "kind": "fetch_metrics", "order": 0 }, { "kind": "analyze_engagement", "order": 1 }] }',
    1440,
    true
  ),
  (
    'suffering_nudge',
    'suffering_detected',
    '{ "min_severity": 0.6 }',
    '{ "skill_name": "app-nudge-sender", "title": "苦しみ検出→Nudge送信", "steps": [{ "kind": "draft_nudge", "order": 0 }, { "kind": "send_nudge", "order": 1 }] }',
    60,
    true
  ),
  (
    'mission_failure_diagnosis',
    'mission:failed',
    '{}',
    '{ "skill_name": "x-poster", "title": "ミッション失敗診断", "steps": [{ "kind": "diagnose", "order": 0 }] }',
    60,
    true
  ),
  (
    'tiktok_content_check_24h',
    'tiktok_posted',
    '{ "delay_min": 1440 }',
    '{ "skill_name": "tiktok-poster", "title": "24h後TikTokメトリクス取得", "steps": [{ "kind": "fetch_metrics", "order": 0 }, { "kind": "analyze_engagement", "order": 1 }] }',
    1440,
    true
  )
ON CONFLICT (name) DO NOTHING;
```
