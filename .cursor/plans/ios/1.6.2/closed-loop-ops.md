# Anicca Closed-Loop Ops Layer 実装仕様書

> **⚠️ ARCHIVE — 実装時は `closed-loop-ops/` サブフォルダの分割版を参照すること。**
> **このファイルは分割前のマスターであり、分割版との差異がある場合は分割版が正（canonical）。**
>
> **目的**: VoxYZ 閉ループアーキテクチャを Anicca 1.6.2 に適用し、Cron一方通行から Event-driven 循環システムへ移行する
> **最終更新**: 2026-02-08
> **ステータス**: アーカイブ（分割版が canonical）
> **参照元**: VoxYZ記事 (`vox.md`)、1.6.2-ultimate-spec.md、既存 Prisma schema
> **前提**: Railway PostgreSQL（Supabase不使用）、OpenClaw VPS (46.225.70.241)、Railway API (Node.js)

---

## 0. Executive Summary

| 項目 | 内容 |
|------|------|
| **何を解決するか** | 現行のCron一方通行（実行→終了）を、閉ループ（提案→承認→実行→イベント→トリガー→提案...）に変える |
| **なぜ必要か** | 「x-posterが投稿した結果を次のx-posterが知らない」「trend-hunterの検出をapp-nudge-senderが知らない」というスキル間断絶を解消する |
| **VoxYZの教訓** | 3つの落とし穴（二重実行者、トリガー→提案の断絶、キュー肥大）を事前に回避する |
| **変更規模** | 新規7テーブル + 新規4エンドポイント + 既存Skill改修5本 + Cron統合 |
| **変更しないもの** | Thompson Sampling (hookSelector.js)、content-verifier (verifier.js)、memU テーブル、iOS向けAPI全て |

---

## 1. アーキテクチャ決定記録

### ADR-004: Closed-Loop Ops Layer

**決定**: VoxYZ 方式の Proposal→Mission→Step 閉ループを Railway PostgreSQL + Railway API + OpenClaw VPS で実装する

| 選択肢 | 評価 | 理由 |
|--------|------|------|
| **A: Railway PostgreSQL（採用）** | ✅ | 既存DB活用、Prisma互換、移行不要 |
| B: Supabase 追加 | ❌ | 2DB管理、移行コスト大、リアルタイムsubscription不要（5分ポーリングで十分） |
| C: OpenClaw Memory のみ | ❌ | ファイルベース、ACID保証なし、クエリ能力不足 |

**VoxYZとの差分**:

| VoxYZ | Anicca | 理由 |
|-------|--------|------|
| Supabase（状態管理） | Railway PostgreSQL | 既存DB活用。リアルタイムsubscription不要 |
| Vercel（制御プレーン） | Railway API | 既存APIサーバー活用。Vercelの追加コスト不要 |
| OpenClaw VPS（実行） | OpenClaw VPS（同一） | 完全一致 |

### ADR-005: 実行者の一元化（Pitfall 1 回避）

**決定**: VPS を唯一の実行者（Executor）とする。Railway API は制御プレーン（Control Plane）のみ

**根拠**: VoxYZの Pitfall 1 — VPSとVercel両方がタスクを実行し、race conditionが発生した。修正: 実行者を1つに絞る

```
VPS (OpenClaw)  = Think + Execute（唯一の実行者）
Railway API     = Approve + Monitor（制御プレーンのみ）
Railway PostgreSQL = All State（共有記憶）
```

### ADR-006: 提案サービスの単一エントリポイント（Pitfall 2 回避）

**決定**: 全ての提案作成は `createProposalAndMaybeAutoApprove()` を通す。直接 INSERT 禁止

**根拠**: VoxYZの Pitfall 2 — トリガーが直接 proposals テーブルに INSERT し、auto-approve と mission 生成がスキップされた

### ADR-007: Cap Gate による事前リジェクト（Pitfall 3 回避）

**決定**: クォータ超過は提案段階でリジェクト。Mission/Step を生成しない

**根拠**: VoxYZの Pitfall 3 — クォータ超過でもMission/Stepが生成され続け、キューが肥大化した

---

## 2. DB スキーマ（Prisma）

> **規約**: 既存 schema.prisma の規約に完全準拠
> - `@db.Uuid @default(dbgenerated("gen_random_uuid()"))`
> - `@db.Timestamptz @default(now())`
> - `@map("snake_case")`, `@@map("table_names")`
> - FK制約あり（`REFERENCES ... ON DELETE CASCADE/SET NULL`）— 親削除時に子レコードも削除。Prisma `@relation(onDelete: Cascade)` と SQL `REFERENCES` が対応

### 2.1 ops_proposals

```prisma
// apps/api/prisma/schema.prisma に追加

/// 全ての「やるべきこと」の入口。x-poster投稿もtrend-hunter検出も、まずここに提案として入る
model OpsProposal {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  skillName   String   @db.VarChar(50) @map("skill_name")   // 'x-poster', 'trend-hunter', etc.
  source      String   @db.VarChar(20) @map("source")       // 'cron' | 'trigger' | 'reaction' | 'manual'
  status      String   @db.VarChar(20) @default("pending")  // 'pending' | 'accepted' | 'rejected'
  title       String   @db.VarChar(500)
  payload     Json     @db.JsonB                              // スキル固有のパラメータ
  rejectReason String? @db.Text @map("reject_reason")        // リジェクト理由（Cap Gate等）
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
/// 承認された提案が「ミッション」になる。複数ステップを持つ
model OpsMission {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  proposalId  String   @db.Uuid @map("proposal_id")
  status      String   @db.VarChar(20) @default("running")  // 'running' | 'succeeded' | 'failed'
  createdAt   DateTime @db.Timestamptz @default(now()) @map("created_at")
  completedAt DateTime? @db.Timestamptz @map("completed_at")

  proposal    OpsProposal @relation(fields: [proposalId], references: [id], onDelete: Cascade)
  steps       OpsMissionStep[]

  @@index([status])
  @@index([createdAt(sort: Desc)])
  @@map("ops_missions")
}
```

### 2.3 ops_mission_steps

```prisma
/// ミッションの各ステップ。VPS Workerが1つずつ実行する
model OpsMissionStep {
  id          String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  missionId   String    @db.Uuid @map("mission_id")
  stepKind    String    @db.VarChar(50) @map("step_kind")    // 'draft_content' | 'verify_content' | 'post_x' | etc.
  stepOrder   Int       @map("step_order")                    // 実行順序 (0-indexed)
  status      String    @db.VarChar(20) @default("queued")   // 'queued' | 'running' | 'succeeded' | 'failed'
  input       Json?     @db.JsonB                             // ステップへの入力データ
  output      Json?     @db.JsonB                             // ステップの出力データ
  lastError   String?   @db.Text @map("last_error")
  reservedAt  DateTime? @db.Timestamptz @map("reserved_at")  // Worker が claim した時刻
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
/// 全てのイベント記録。「x-posterが投稿した」「trend-hunterが苦しみを見つけた」等
model OpsEvent {
  id          String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  source      String   @db.VarChar(50)                       // 'x-poster', 'trend-hunter', etc.
  kind        String   @db.VarChar(100)                      // 'tweet_posted', 'suffering_detected', etc.
  tags        String[] @default([])                           // ['tweet', 'posted'], ['mission', 'failed']
  payload     Json?    @db.JsonB                              // イベント固有データ
  missionId   String?  @db.Uuid @map("mission_id")           // 関連するミッション（あれば）
  createdAt   DateTime @db.Timestamptz @default(now()) @map("created_at")

  @@index([kind])
  @@index([source])
  @@index([createdAt(sort: Desc)])
  @@map("ops_events")
}
```

### 2.5 ops_policy

```prisma
/// 設定値をJSONで保管。再デプロイ不要で変更可能
model OpsPolicy {
  key       String   @id @db.VarChar(100)
  value     Json     @db.JsonB
  updatedAt DateTime @db.Timestamptz @default(now()) @updatedAt @map("updated_at")

  @@map("ops_policy")
}
```

### 2.6 ops_trigger_rules

```prisma
/// 「エンゲージメント5%超→分析提案」等のトリガー条件
model OpsTriggerRule {
  id           String   @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  name         String   @db.VarChar(100) @unique
  eventKind    String   @db.VarChar(100) @map("event_kind")  // マッチするイベント種別
  condition    Json     @db.JsonB                              // 追加条件（JSON式）
  proposalTemplate Json @db.JsonB @map("proposal_template")   // 生成する提案のテンプレート
  cooldownMin  Int      @default(60) @map("cooldown_min")     // クールダウン（分）
  enabled      Boolean  @default(true)
  lastFiredAt  DateTime? @db.Timestamptz @map("last_fired_at")
  createdAt    DateTime @db.Timestamptz @default(now()) @map("created_at")

  @@index([eventKind])
  @@map("ops_trigger_rules")
}
```

### 2.7 ops_reactions

```prisma
/// エージェント間の連鎖反応キュー
model OpsReaction {
  id          String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  eventId     String    @db.Uuid @map("event_id")            // トリガーとなったイベント
  targetSkill String    @db.VarChar(50) @map("target_skill")  // 反応するスキル
  actionType  String    @db.VarChar(50) @map("action_type")   // 'analyze', 'diagnose', 'cross_post', etc.
  status      String    @db.VarChar(20) @default("pending")   // 'pending' | 'processed' | 'skipped'
  createdAt   DateTime  @db.Timestamptz @default(now()) @map("created_at")
  processedAt DateTime? @db.Timestamptz @map("processed_at")

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
  mission_id UUID,
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
  event_id UUID NOT NULL,
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

INSERT INTO ops_policy (key, value) VALUES
  ('auto_approve', '{
    "enabled": true,
    "allowed_step_kinds": ["draft_content", "verify_content", "detect_suffering", "analyze_engagement", "fetch_metrics"]
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
        "type": "send_relevant_nudge",
        "probability": 0.5,
        "cooldown": 60
      },
      {
        "source": "*",
        "tags": ["mission:failed"],
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
        "cooldown": 240
      },
      {
        "source": "x-poster",
        "tags": ["engagement", "high"],
        "target": "tiktok-poster",
        "type": "cross_post",
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

---

## 6. API 実装（Railway API）

### 6.1 Proposal Service（閉ループの核心）

> **VoxYZ Pitfall 2 修正**: 全ての提案作成がこの1つの関数を通る

```javascript
// apps/api/src/services/ops/proposalService.js

import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

/**
 * 提案作成 + Cap Gate + Auto-Approve + Mission生成
 * 全ソース（Cron, Trigger, Reaction, Manual）がこの関数を通る
 *
 * @param {Object} input
 * @param {string} input.skillName - スキル名
 * @param {string} input.source - 'cron' | 'trigger' | 'reaction' | 'manual'
 * @param {string} input.title - 提案タイトル
 * @param {Object} input.payload - スキル固有パラメータ
 * @param {Array<{kind: string, order: number}>} input.steps - ミッションステップ定義
 * @returns {Object} { proposalId, status, missionId?, rejectReason? }
 */
export async function createProposalAndMaybeAutoApprove(input) {
  const { skillName, source, title, payload, steps } = input;

  // 1. 日次提案数上限チェック（暴走防止）
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayCount = await prisma.opsProposal.count({
    where: { createdAt: { gte: todayStart } }
  });
  if (todayCount >= 100) {
    logger.warn(`Daily proposal limit reached (${todayCount}/100)`);
    return { proposalId: null, status: 'rejected', rejectReason: 'daily_proposal_limit' };
  }

  // 2. Cap Gate チェック（ステップ種別ごとの制限）
  for (const step of steps) {
    const gateResult = await checkCapGate(step.kind);
    if (!gateResult.ok) {
      // リジェクト：提案を記録するがMissionは作らない
      const proposal = await prisma.opsProposal.create({
        data: {
          skillName,
          source,
          status: 'rejected',
          title,
          payload,
          rejectReason: gateResult.reason,
          resolvedAt: new Date()
        }
      });

      // リジェクトイベント記録
      await emitEvent(skillName, 'proposal:rejected', ['proposal', 'rejected'], {
        proposalId: proposal.id,
        reason: gateResult.reason
      });

      logger.info(`Proposal rejected: ${title} — ${gateResult.reason}`);
      return { proposalId: proposal.id, status: 'rejected', rejectReason: gateResult.reason };
    }
  }

  // 3. 提案を INSERT
  const proposal = await prisma.opsProposal.create({
    data: {
      skillName,
      source,
      status: 'pending',
      title,
      payload
    }
  });

  // 4. イベント記録
  await emitEvent(skillName, 'proposal:created', ['proposal', 'created'], {
    proposalId: proposal.id,
    source
  });

  // 5. Auto-Approve 評価
  const autoApprovePolicy = await getPolicy('auto_approve');
  const allStepsAutoApprovable = steps.every(
    s => autoApprovePolicy?.allowed_step_kinds?.includes(s.kind)
  );

  if (autoApprovePolicy?.enabled && allStepsAutoApprovable) {
    // 自動承認 → Mission + Steps 作成
    const mission = await prisma.opsMission.create({
      data: {
        proposalId: proposal.id,
        status: 'running',
        steps: {
          create: steps.map(s => ({
            stepKind: s.kind,
            stepOrder: s.order,
            status: 'queued',
            input: s.input || {}
          }))
        }
      },
      include: { steps: true }
    });

    // 提案を accepted に更新
    await prisma.opsProposal.update({
      where: { id: proposal.id },
      data: { status: 'accepted', resolvedAt: new Date() }
    });

    await emitEvent(skillName, 'proposal:auto_approved', ['proposal', 'approved', 'auto'], {
      proposalId: proposal.id,
      missionId: mission.id
    });

    logger.info(`Proposal auto-approved: ${title} → Mission ${mission.id}`);
    return { proposalId: proposal.id, status: 'accepted', missionId: mission.id };
  }

  // 自動承認対象外 → pending のまま（人間承認待ち）
  logger.info(`Proposal awaiting approval: ${title} (contains non-auto-approvable steps)`);
  return { proposalId: proposal.id, status: 'pending' };
}
```

### 6.2 Cap Gate 実装

```javascript
// apps/api/src/services/ops/capGates.js

import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';

/**
 * ステップ種別ごとの Cap Gate チェック
 *
 * @param {string} stepKind - ステップ種別
 * @returns {{ ok: boolean, reason?: string }}
 */
export async function checkCapGate(stepKind) {
  const gates = {
    post_x: checkPostXGate,
    post_tiktok: checkPostTiktokGate,
    send_nudge: checkSendNudgeGate
  };

  const gateFn = gates[stepKind];
  if (!gateFn) return { ok: true }; // Gate が定義されていない種別は通過
  return gateFn();
}

/**
 * X投稿 Cap Gate
 */
async function checkPostXGate() {
  // x_autopost が無効ならリジェクト
  const autopost = await getPolicy('x_autopost');
  if (autopost?.enabled === false) {
    return { ok: false, reason: 'x_autopost disabled' };
  }

  // 日次クォータチェック
  const quota = await getPolicy('x_daily_quota');
  const limit = quota?.limit ?? 3;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'tweet_posted',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `X daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}

/**
 * TikTok投稿 Cap Gate
 */
async function checkPostTiktokGate() {
  const autopost = await getPolicy('tiktok_autopost');
  if (autopost?.enabled === false) {
    return { ok: false, reason: 'tiktok_autopost disabled' };
  }

  const quota = await getPolicy('tiktok_daily_quota');
  const limit = quota?.limit ?? 1;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'tiktok_posted',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `TikTok daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}

/**
 * Nudge送信 Cap Gate
 * 既存の FATIGUE_CONFIG をopsレイヤーで統合
 */
async function checkSendNudgeGate() {
  const quota = await getPolicy('nudge_daily_quota');
  const limit = quota?.limit ?? 10;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'nudge_sent',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `Nudge daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}
```

### 6.3 Policy Service

```javascript
// apps/api/src/services/ops/policyService.js

import { prisma } from '../../lib/prisma.js';

// インメモリキャッシュ（5分TTL）
const cache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

/**
 * Policy値を取得（キャッシュ付き）
 *
 * @param {string} key - Policy キー
 * @returns {Object|null} Policy の value（JSON）
 */
export async function getPolicy(key) {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
    return cached.value;
  }

  const row = await prisma.opsPolicy.findUnique({ where: { key } });
  const value = row?.value ?? null;

  cache.set(key, { value, fetchedAt: Date.now() });
  return value;
}

/**
 * Policy値を更新
 *
 * @param {string} key - Policy キー
 * @param {Object} value - 新しい値
 */
export async function setPolicy(key, value) {
  await prisma.opsPolicy.upsert({
    where: { key },
    create: { key, value },
    update: { value, updatedAt: new Date() }
  });

  // キャッシュ無効化
  cache.delete(key);
}
```

### 6.4 Event Emitter

```javascript
// apps/api/src/services/ops/eventEmitter.js

import { prisma } from '../../lib/prisma.js';

/**
 * イベント発行
 *
 * @param {string} source - イベント発生源 ('x-poster', 'trend-hunter', etc.)
 * @param {string} kind - イベント種別 ('tweet_posted', 'suffering_detected', etc.)
 * @param {string[]} tags - タグ配列 (['tweet', 'posted'])
 * @param {Object} payload - イベント固有データ
 * @param {string} [missionId] - 関連ミッションID
 * @returns {Object} 作成されたイベント
 */
export async function emitEvent(source, kind, tags, payload = {}, missionId = null) {
  return prisma.opsEvent.create({
    data: {
      source,
      kind,
      tags,
      payload,
      missionId
    }
  });
}
```

### 6.5 Heartbeat エンドポイント

> **VPS の crontab から5分毎に呼ばれる**: `*/5 * * * * curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" https://anicca-proxy-staging.up.railway.app/api/ops/heartbeat`

```javascript
// apps/api/src/routes/ops/heartbeat.js

import { Router } from 'express';
import { evaluateTriggers } from '../../services/ops/triggerEvaluator.js';
import { processReactionQueue } from '../../services/ops/reactionProcessor.js';
import { recoverStaleSteps } from '../../services/ops/staleRecovery.js';
import { promoteInsights } from '../../services/ops/insightPromoter.js';
import { logger } from '../../lib/logger.js';

const router = Router();

/**
 * GET /api/ops/heartbeat
 * 5分毎にVPSから呼ばれる制御プレーン
 *
 * 4つの処理を順次実行:
 * 1. evaluateTriggers — イベントを評価し、条件合致で新提案を生成
 * 2. processReactionQueue — Reaction Matrix に基づく連鎖反応を処理
 * 3. promoteInsights — shared-learnings から長期記憶への昇格
 * 4. recoverStaleSteps — 30分以上停滞したステップを failed に
 */
router.get('/heartbeat', async (req, res) => {
  const start = Date.now();

  try {
    const results = {
      triggers: await evaluateTriggers(4000),   // 4秒タイムアウト
      reactions: await processReactionQueue(3000), // 3秒タイムアウト
      insights: await promoteInsights(),
      stale: await recoverStaleSteps()
    };

    const elapsed = Date.now() - start;
    logger.info(`Heartbeat completed in ${elapsed}ms`, results);

    res.json({ ok: true, elapsed, ...results });
  } catch (error) {
    logger.error('Heartbeat failed:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

export default router;
```

### 6.6 Trigger Evaluator

```javascript
// apps/api/src/services/ops/triggerEvaluator.js

import { prisma } from '../../lib/prisma.js';
import { createProposalAndMaybeAutoApprove } from './proposalService.js';
import { logger } from '../../lib/logger.js';

/**
 * 未処理イベントを評価し、条件合致でトリガーを発火→提案を生成
 *
 * @param {number} timeoutMs - タイムアウト（ms）
 * @returns {{ evaluated: number, fired: number }}
 */
export async function evaluateTriggers(timeoutMs = 4000) {
  const deadline = Date.now() + timeoutMs;
  let evaluated = 0;
  let fired = 0;

  // 有効なトリガールールを取得
  const rules = await prisma.opsTriggerRule.findMany({
    where: { enabled: true }
  });

  for (const rule of rules) {
    if (Date.now() > deadline) break;

    // クールダウンチェック
    if (rule.lastFiredAt) {
      const minutesSince = (Date.now() - rule.lastFiredAt.getTime()) / (1000 * 60);
      if (minutesSince < rule.cooldownMin) continue;
    }

    // マッチするイベントを検索（直近5分 + lastFiredAt以降）
    const since = rule.lastFiredAt || new Date(Date.now() - 5 * 60 * 1000);
    const matchingEvents = await prisma.opsEvent.findMany({
      where: {
        kind: rule.eventKind,
        createdAt: { gt: since }
      },
      take: 10,
      orderBy: { createdAt: 'desc' }
    });

    evaluated += matchingEvents.length;

    if (matchingEvents.length > 0) {
      // 追加条件チェック（delay_min, min_severity等）
      const conditionMet = checkTriggerCondition(rule.condition, matchingEvents[0]);
      if (!conditionMet) continue;

      // トリガー発火 → 提案生成
      const template = rule.proposalTemplate;
      const result = await createProposalAndMaybeAutoApprove({
        skillName: template.skill_name,
        source: 'trigger',
        title: template.title,
        payload: { triggeredBy: rule.name, eventId: matchingEvents[0].id },
        steps: template.steps.map(s => ({ kind: s.kind, order: s.order }))
      });

      // lastFiredAt 更新
      await prisma.opsTriggerRule.update({
        where: { id: rule.id },
        data: { lastFiredAt: new Date() }
      });

      fired++;
      logger.info(`Trigger fired: ${rule.name} → proposal ${result.proposalId}`);
    }
  }

  return { evaluated, fired };
}

/**
 * トリガー追加条件のチェック
 */
function checkTriggerCondition(condition, event) {
  // delay_min: イベントからN分後に発火
  if (condition.delay_min) {
    const eventAge = (Date.now() - event.createdAt.getTime()) / (1000 * 60);
    if (eventAge < condition.delay_min) return false;
  }

  // min_severity: ペイロードの severity が閾値以上
  if (condition.min_severity) {
    const severity = event.payload?.severity ?? 0;
    if (severity < condition.min_severity) return false;
  }

  return true;
}
```

### 6.7 Reaction Processor

```javascript
// apps/api/src/services/ops/reactionProcessor.js

import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';
import { createProposalAndMaybeAutoApprove } from './proposalService.js';
import { logger } from '../../lib/logger.js';

/**
 * Reaction Matrix に基づく連鎖反応を処理
 * 確率的に反応するかどうかを決定（VoxYZの「100%決定論 = ロボット」回避）
 *
 * @param {number} timeoutMs - タイムアウト（ms）
 * @returns {{ processed: number, proposals: number }}
 */
export async function processReactionQueue(timeoutMs = 3000) {
  const deadline = Date.now() + timeoutMs;
  let processed = 0;
  let proposals = 0;

  // pending のリアクションを取得
  const pendingReactions = await prisma.opsReaction.findMany({
    where: { status: 'pending' },
    take: 20,
    orderBy: { createdAt: 'asc' }
  });

  for (const reaction of pendingReactions) {
    if (Date.now() > deadline) break;

    // 提案を生成
    const result = await createProposalAndMaybeAutoApprove({
      skillName: reaction.targetSkill,
      source: 'reaction',
      title: `Reaction: ${reaction.actionType} (from event ${reaction.eventId})`,
      payload: { eventId: reaction.eventId, actionType: reaction.actionType },
      steps: [{ kind: reaction.actionType, order: 0 }]
    });

    // リアクションをprocessed に更新
    await prisma.opsReaction.update({
      where: { id: reaction.id },
      data: { status: 'processed', processedAt: new Date() }
    });

    processed++;
    if (result.status === 'accepted') proposals++;
  }

  return { processed, proposals };
}

/**
 * イベント発行時に Reaction Matrix を評価し、リアクションをキューに追加
 * emitEvent() から呼ばれる
 *
 * @param {Object} event - 発行されたイベント
 */
export async function evaluateReactionMatrix(event) {
  const matrix = await getPolicy('reaction_matrix');
  if (!matrix?.patterns) return;

  for (const pattern of matrix.patterns) {
    // source マッチ（'*' は全てにマッチ）
    if (pattern.source !== '*' && pattern.source !== event.source) continue;

    // tags マッチ（パターンの全tagsがイベントに含まれるか）
    const tagsMatch = pattern.tags.every(t => event.tags.includes(t));
    if (!tagsMatch) continue;

    // 確率判定
    if (Math.random() > pattern.probability) continue;

    // クールダウンチェック
    const recentReaction = await prisma.opsReaction.findFirst({
      where: {
        targetSkill: pattern.target,
        actionType: pattern.type,
        createdAt: { gt: new Date(Date.now() - pattern.cooldown * 60 * 1000) }
      }
    });
    if (recentReaction) continue;

    // リアクションをキューに追加
    await prisma.opsReaction.create({
      data: {
        eventId: event.id,
        targetSkill: pattern.target,
        actionType: pattern.type,
        status: 'pending'
      }
    });

    logger.info(`Reaction queued: ${event.source}→${pattern.target} (${pattern.type}, p=${pattern.probability})`);
  }
}
```

### 6.8 Stale Recovery（自己回復）

```javascript
// apps/api/src/services/ops/staleRecovery.js

import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';
import { logger } from '../../lib/logger.js';

/**
 * 30分以上 running のまま停滞したステップを failed に
 * VPS再起動、ネットワーク障害等で処理が中断した場合の自動回復
 *
 * @returns {{ recovered: number, missionsFailed: number }}
 */
export async function recoverStaleSteps() {
  const thresholdPolicy = await getPolicy('stale_threshold_min');
  const thresholdMin = thresholdPolicy?.value ?? 30;
  const staleThreshold = new Date(Date.now() - thresholdMin * 60 * 1000);

  // running のまま staleThreshold より前に予約されたステップ
  const staleSteps = await prisma.opsMissionStep.findMany({
    where: {
      status: 'running',
      reservedAt: { lt: staleThreshold }
    },
    select: { id: true, missionId: true }
  });

  let recovered = 0;
  let missionsFailed = 0;

  for (const step of staleSteps) {
    await prisma.opsMissionStep.update({
      where: { id: step.id },
      data: {
        status: 'failed',
        lastError: `Stale: no progress for ${thresholdMin} minutes`,
        completedAt: new Date()
      }
    });

    recovered++;

    // ミッション全体を最終化判定
    const finalized = await maybeFinalizeMission(step.missionId);
    if (finalized === 'failed') missionsFailed++;
  }

  if (recovered > 0) {
    logger.warn(`Recovered ${recovered} stale steps, ${missionsFailed} missions failed`);
  }

  return { recovered, missionsFailed };
}

/**
 * ミッション最終化判定
 * 全ステップ完了 → succeeded / いずれかfailed → failed
 *
 * @param {string} missionId
 * @returns {'succeeded' | 'failed' | null} null = まだ完了していない
 */
export async function maybeFinalizeMission(missionId) {
  const steps = await prisma.opsMissionStep.findMany({
    where: { missionId },
    select: { status: true }
  });

  const allDone = steps.every(s => s.status === 'succeeded' || s.status === 'failed');
  if (!allDone) return null;

  const anyFailed = steps.some(s => s.status === 'failed');
  const finalStatus = anyFailed ? 'failed' : 'succeeded';

  await prisma.opsMission.update({
    where: { id: missionId },
    data: { status: finalStatus, completedAt: new Date() }
  });

  // イベント記録
  const { emitEvent } = await import('./eventEmitter.js');
  const mission = await prisma.opsMission.findUnique({
    where: { id: missionId },
    include: { proposal: true }
  });

  await emitEvent(
    mission.proposal.skillName,
    `mission:${finalStatus}`,
    ['mission', finalStatus],
    { missionId, proposalId: mission.proposalId }
  );

  return finalStatus;
}
```

---

## 7. API ルーター統合

```javascript
// apps/api/src/routes/ops/index.js

import { Router } from 'express';
import heartbeatRouter from './heartbeat.js';
import { z } from 'zod';
import { createProposalAndMaybeAutoApprove } from '../../services/ops/proposalService.js';
import { prisma } from '../../lib/prisma.js';
import { maybeFinalizeMission } from '../../services/ops/staleRecovery.js';

const router = Router();

// Heartbeat
router.use(heartbeatRouter);

// --- Proposal API ---

const ProposalInputSchema = z.object({
  skillName: z.string().max(50),
  source: z.enum(['cron', 'trigger', 'reaction', 'manual']),
  title: z.string().max(500),
  payload: z.record(z.unknown()).default({}),
  steps: z.array(z.object({
    kind: z.string().max(50),
    order: z.number().int().min(0),
    input: z.record(z.unknown()).optional()
  })).min(1)
});

/**
 * POST /api/ops/proposal
 * 新しい提案を作成
 */
router.post('/proposal', async (req, res) => {
  const parsed = ProposalInputSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }
  const result = await createProposalAndMaybeAutoApprove(parsed.data);
  res.json(result);
});

// --- Step Execution API (VPS Worker 用) ---

/**
 * GET /api/ops/step/next
 * 次の実行待ちステップを取得（VPS Worker が polling）
 */
router.get('/step/next', async (req, res) => {
  // queued ステップを step_order 昇順で1件取得し、running に更新
  const step = await prisma.$transaction(async (tx) => {
    const next = await tx.opsMissionStep.findFirst({
      where: { status: 'queued' },
      orderBy: [
        { createdAt: 'asc' },
        { stepOrder: 'asc' }
      ],
      include: {
        mission: {
          include: { proposal: true }
        }
      }
    });

    if (!next) return null;

    // 同一ミッション内で前のステップが完了しているか確認
    if (next.stepOrder > 0) {
      const prevStep = await tx.opsMissionStep.findFirst({
        where: {
          missionId: next.missionId,
          stepOrder: next.stepOrder - 1
        }
      });
      if (prevStep && prevStep.status !== 'succeeded') {
        return null; // 前のステップがまだ完了していない
      }
    }

    // running に更新（claim）
    await tx.opsMissionStep.update({
      where: { id: next.id },
      data: { status: 'running', reservedAt: new Date() }
    });

    return next;
  });

  if (!step) {
    return res.json({ step: null });
  }

  res.json({
    step: {
      id: step.id,
      missionId: step.missionId,
      stepKind: step.stepKind,
      stepOrder: step.stepOrder,
      input: step.input,
      proposalPayload: step.mission.proposal.payload,
      skillName: step.mission.proposal.skillName
    }
  });
});

/**
 * PATCH /api/ops/step/:id/complete
 * ステップ完了報告
 */
const StepCompleteSchema = z.object({
  status: z.enum(['succeeded', 'failed']),
  output: z.record(z.unknown()).optional(),
  error: z.string().optional()
});

router.patch('/step/:id/complete', async (req, res) => {
  const { id } = req.params;
  const parsed = StepCompleteSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { status, output, error } = parsed.data;

  const step = await prisma.opsMissionStep.update({
    where: { id },
    data: {
      status,
      output: output || {},
      lastError: error || null,
      completedAt: new Date()
    }
  });

  // ミッション最終化判定
  const missionStatus = await maybeFinalizeMission(step.missionId);

  res.json({ ok: true, stepStatus: status, missionStatus });
});

export default router;
```

### ルーターのマウント

```javascript
// apps/api/src/routes/index.js に追加

import opsRouter from './ops/index.js';

// 既存のルーター（変更なし）
app.use('/api/mobile', mobileRouter);
// ...

// 新規: Ops API
app.use('/api/ops', opsRouter);
```

---

## 8. VPS Worker（OpenClaw スキル側）

### 8.1 Mission Worker スキル

> **VPSのOpenClawから5分毎に呼ばれる。次の queued ステップを取得→実行→完了報告**

```yaml
---
name: mission-worker
description: Ops閉ループの実行エンジン。queued ステップを取得して実行する
metadata: { "openclaw": { "emoji": "⚙️", "requires": { "env": ["ANICCA_AGENT_TOKEN"] } } }
---

# mission-worker

## Instructions

1. `GET /api/ops/step/next` で次の実行待ちステップを取得
2. ステップがなければ正常終了（何もしない）
3. ステップがあれば、step_kind に応じた処理を実行:
   - `draft_content`: hookSelector.js でhook選択 → LLMでコンテンツ生成
   - `verify_content`: verifier.js でコンテンツ検証（3/5以上で合格）
   - `post_x`: X API で投稿
   - `post_tiktok`: TikTok API で投稿
   - `detect_suffering`: 苦しみキーワード検索
   - `send_nudge`: app-nudge-sender 経由でNudge送信
   - `fetch_metrics`: X/TikTok のエンゲージメントデータ取得
   - `analyze_engagement`: メトリクスを分析し shared-learnings に記録
   - `diagnose`: ミッション失敗の原因分析
4. 実行結果を `PATCH /api/ops/step/:id/complete` で報告
5. イベントを発行（投稿成功、苦しみ検出等）

## Required Tools

- `exec` (API呼び出し、コンテンツ生成)
- `web_search` (トレンド検出)
- `slack` (通知)
- `read` / `write` (shared-learnings)

## Error Handling

| エラー | 対応 |
|--------|------|
| API呼び出し失敗 | リトライ3回後、step を failed で報告 |
| LLM生成失敗 | フォールバックチェーン（OpenAI → Anthropic → Groq） |
| X API rate limit | step を failed で報告（次回Heartbeat で再スケジュール可能） |
```

### 8.2 Cron 統合（schedule.yaml 変更）

> **既存の個別Cronを mission-worker + heartbeat に集約**

```yaml
# ~/.openclaw/schedule.yaml（AFTER: 閉ループ対応）
timezone: Asia/Tokyo

jobs:
  # --- 閉ループ制御 ---

  # Heartbeat: 5分毎にRailway APIの制御プレーンを叩く
  ops-heartbeat:
    cron: "*/5 * * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
        https://anicca-proxy-staging.up.railway.app/api/ops/heartbeat

  # Mission Worker: 1分毎に次のステップを取得→実行
  ops-worker:
    skill: mission-worker
    cron: "* * * * *"
    session: isolated

  # --- 提案生成（閉ループの入口）---

  # x-poster: 朝と夜に投稿提案を生成
  x-poster-morning:
    cron: "0 9 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "x-poster",
        "source": "cron",
        "title": "X朝投稿",
        "payload": { "slot": "morning" },
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_x", "order": 2 }
        ]
      }

  x-poster-evening:
    cron: "0 21 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "x-poster",
        "source": "cron",
        "title": "X夜投稿",
        "payload": { "slot": "evening" },
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_x", "order": 2 }
        ]
      }

  tiktok-poster:
    cron: "0 20 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "tiktok-poster",
        "source": "cron",
        "title": "TikTok日次投稿",
        "payload": {},
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_tiktok", "order": 2 }
        ]
      }

  trend-hunter:
    cron: "0 */4 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "trend-hunter",
        "source": "cron",
        "title": "トレンド検出",
        "payload": {},
        "steps": [
          { "kind": "detect_suffering", "order": 0 }
        ]
      }

  # --- 既存（変更なし）---

  daily-metrics-reporter:
    # 既存のまま（ops対象外）
    cron: "0 20 * * *"
    session: isolated

  hookpost-ttl-cleaner:
    skill: hookpost-ttl-cleaner
    cron: "0 3 * * *"
    session: isolated

  sto-weekly-refresh:
    skill: sto-weekly-refresh
    cron: "0 3 * * 0"
    session: isolated
```

---

## 9. Kill Switch（自動承認しない操作）

| step_kind | 自動承認 | 理由 |
|-----------|---------|------|
| `draft_content` | ✅ 許可 | 下書きは安全。外部に影響なし |
| `verify_content` | ✅ 許可 | 検証するだけ。外部に影響なし |
| `detect_suffering` | ✅ 許可 | 検出するだけ。行動しない |
| `fetch_metrics` | ✅ 許可 | データ取得のみ |
| `analyze_engagement` | ✅ 許可 | 分析するだけ。外部に影響なし |
| `diagnose` | ✅ 許可 | 診断するだけ |
| **`post_x`** | **❌ 禁止** | 公開投稿。VoxYZ: "post_tweet will never auto-approve" |
| **`post_tiktok`** | **❌ 禁止** | 公開投稿 |
| **`send_nudge`** | **❌ 禁止** | ユーザーへの直接介入。仏教原則: ehipassiko |
| **`deploy`** | **❌ 永久禁止** | インフラ変更 |
| **`reply_dm`** | **❌ 永久禁止** | テーラヴァーダの不請法則に違反 |

**「post_x を auto-approve しないのに、どうやって自動投稿するのか？」**

答え: 現フェーズ（P2相当）では、post_x を含む提案は `status: 'pending'` のまま止まる。人間がSlack通知を見て承認する。将来 P3（自動実行+事後報告）に昇格した時点で、`auto_approve.allowed_step_kinds` に `post_x` を追加する。これは ops_policy テーブルの1行を更新するだけ。コード変更不要。

---

## 10. 認証

| エンドポイント | 認証方式 | 理由 |
|--------------|---------|------|
| `POST /api/ops/proposal` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS Worker からのみ呼ばれる |
| `GET /api/ops/heartbeat` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS crontab からのみ呼ばれる |
| `GET /api/ops/step/next` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS Worker からのみ呼ばれる |
| `PATCH /api/ops/step/:id/complete` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS Worker からのみ呼ばれる |

```javascript
// apps/api/src/middleware/opsAuth.js

/**
 * Ops API 認証ミドルウェア
 * ANICCA_AGENT_TOKEN で Bearer 認証
 */
export function opsAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  const token = authHeader?.replace('Bearer ', '');

  if (!token || token !== process.env.ANICCA_AGENT_TOKEN) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}
```

---

## 11. テストマトリックス

| # | テスト対象 | テスト名 | 種別 | カバー |
|---|-----------|---------|------|--------|
| T1 | Proposal Service | `test_createProposal_accepted` | Unit | 正常系 — auto-approve対象 |
| T2 | Proposal Service | `test_createProposal_rejected_capGate` | Unit | Cap Gateリジェクト |
| T3 | Proposal Service | `test_createProposal_pending_noAutoApprove` | Unit | auto-approve対象外 → pending |
| T4 | Proposal Service | `test_createProposal_dailyLimit` | Unit | 日次100件上限 |
| T5 | Cap Gate | `test_postXGate_quotaReached` | Unit | X日次クォータ |
| T6 | Cap Gate | `test_postXGate_disabled` | Unit | x_autopost=false |
| T7 | Cap Gate | `test_sendNudgeGate_quotaReached` | Unit | Nudge日次クォータ |
| T8 | Policy Service | `test_getPolicy_cached` | Unit | キャッシュヒット |
| T9 | Policy Service | `test_setPolicy_invalidatesCache` | Unit | キャッシュ無効化 |
| T10 | Trigger Evaluator | `test_evaluateTriggers_fireOnMatch` | Unit | イベント合致→提案生成 |
| T11 | Trigger Evaluator | `test_evaluateTriggers_cooldown` | Unit | クールダウン内→スキップ |
| T12 | Trigger Evaluator | `test_evaluateTriggers_delayCondition` | Unit | delay_min 未到達→スキップ |
| T13 | Reaction Processor | `test_processReactionQueue_createProposal` | Unit | pending→提案生成 |
| T14 | Reaction Matrix | `test_evaluateReactionMatrix_probability` | Unit | 確率判定 |
| T15 | Reaction Matrix | `test_evaluateReactionMatrix_cooldown` | Unit | クールダウン内→スキップ |
| T16 | Stale Recovery | `test_recoverStaleSteps_markFailed` | Unit | 30分超→failed |
| T17 | Stale Recovery | `test_maybeFinalizeMission_allSucceeded` | Unit | 全ステップ成功→mission succeeded |
| T18 | Stale Recovery | `test_maybeFinalizeMission_anyFailed` | Unit | 1つfailed→mission failed |
| T19 | Heartbeat API | `test_heartbeat_returns200` | Integration | 正常レスポンス |
| T20 | Proposal API | `test_proposal_validInput` | Integration | Zodバリデーション |
| T21 | Proposal API | `test_proposal_invalidInput` | Integration | バリデーションエラー |
| T22 | Step Next API | `test_stepNext_noSteps` | Integration | ステップなし→null |
| T23 | Step Next API | `test_stepNext_claimStep` | Integration | ステップ取得+running更新 |
| T24 | Step Complete API | `test_stepComplete_succeeded` | Integration | 成功報告 |
| T25 | Step Complete API | `test_stepComplete_missionFinalized` | Integration | ミッション最終化 |
| T26 | Auth | `test_opsAuth_rejectNoToken` | Unit | トークンなし→401 |
| T27 | Auth | `test_opsAuth_rejectBadToken` | Unit | 不正トークン→401 |

---

## 12. 実装チェックリスト

| # | タスク | AC（受け入れ条件） | 状態 |
|---|--------|-------------------|------|
| 12.1 | マイグレーション SQL 適用 | `prisma db pull` で全opsテーブルがスキーマに反映 | ⬜ |
| 12.2 | Policy シードデータ投入 | `SELECT * FROM ops_policy` で9行 | ⬜ |
| 12.3 | Trigger Rule シードデータ投入 | `SELECT * FROM ops_trigger_rules` で4行 | ⬜ |
| 12.4 | proposalService.js 実装 | T1-T4 全PASS | ⬜ |
| 12.5 | capGates.js 実装 | T5-T7 全PASS | ⬜ |
| 12.6 | policyService.js 実装 | T8-T9 全PASS | ⬜ |
| 12.7 | eventEmitter.js 実装 | 手動テストでops_eventsに記録 | ⬜ |
| 12.8 | triggerEvaluator.js 実装 | T10-T12 全PASS | ⬜ |
| 12.9 | reactionProcessor.js 実装 | T13-T15 全PASS | ⬜ |
| 12.10 | staleRecovery.js 実装 | T16-T18 全PASS | ⬜ |
| 12.11 | Heartbeat ルーター実装 | T19 PASS | ⬜ |
| 12.12 | Proposal/Step ルーター実装 | T20-T27 全PASS | ⬜ |
| 12.13 | opsAuth ミドルウェア実装 | T26-T27 PASS | ⬜ |
| 12.14 | mission-worker SKILL.md 作成 | `openclaw skills list` に表示 | ⬜ |
| 12.15 | schedule.yaml 更新 | `openclaw cron list` で新ジョブ表示 | ⬜ |
| 12.16 | Staging デプロイ + E2Eテスト | 手動提案→Mission→Step実行→完了の全フロー | ⬜ |

---

## 13. 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| iOS アプリ変更 | ops レイヤーはバックエンドのみ |
| 既存 `/api/mobile/*` 変更 | 後方互換維持。破壊的変更禁止 |
| memU テーブル変更 | 別の責務（長期記憶 vs 運用状態） |
| hookSelector.js 変更 | Thompson Sampling ロジックは不変 |
| verifier.js 変更 | content-verifier ロジックは不変 |
| Supabase 導入 | Railway PostgreSQL で十分（ADR-004） |
| Dashboard UI | 将来（Phase C以降で検討） |
| Moltbook 連携 | 別スコープ（Phase 4） |

---

## 14. ファイル構成（新規作成）

```
apps/api/
├── prisma/
│   └── schema.prisma                      # ← ops テーブル追加
├── sql/
│   ├── 20260208_add_ops_tables.sql        # マイグレーション
│   ├── 20260208_seed_ops_policy.sql       # Policy シード
│   └── 20260208_seed_ops_trigger_rules.sql # Trigger Rule シード
└── src/
    ├── middleware/
    │   └── opsAuth.js                      # 認証ミドルウェア
    ├── routes/
    │   └── ops/
    │       ├── index.js                    # Proposal/Step ルーター
    │       └── heartbeat.js                # Heartbeat ルーター
    └── services/
        └── ops/
            ├── proposalService.js          # 閉ループの核心
            ├── capGates.js                 # Cap Gate
            ├── policyService.js            # Policy CRUD + キャッシュ
            ├── eventEmitter.js             # イベント発行
            ├── triggerEvaluator.js          # トリガー評価
            ├── reactionProcessor.js         # Reaction Matrix
            ├── staleRecovery.js            # 自己回復
            └── insightPromoter.js          # shared-learnings → memU昇格

VPS (~/.openclaw/workspace/skills/):
└── mission-worker/
    └── SKILL.md                            # Mission Worker スキル
```

---

## 15. Step Executor 実装（step_kind ごとの具体処理）

> **Gap P0 #1 解消**: 各 step_kind が「何をするか」を具体的に定義する
> **設計方針**: Strategy パターンで step_kind → executor 関数をマッピング。新しい step_kind の追加は Map に1行追加するだけ。

### 15.1 Executor Registry

```javascript
// apps/api/src/services/ops/stepExecutors/registry.js

import { executeDraftContent } from './executeDraftContent.js';
import { executeVerifyContent } from './executeVerifyContent.js';
import { executePostX } from './executePostX.js';
import { executePostTiktok } from './executePostTiktok.js';
import { executeFetchMetrics } from './executeFetchMetrics.js';
import { executeAnalyzeEngagement } from './executeAnalyzeEngagement.js';
import { executeDiagnose } from './executeDiagnose.js';
import { executeDetectSuffering } from './executeDetectSuffering.js';
import { executeDraftNudge } from './executeDraftNudge.js';
import { executeSendNudge } from './executeSendNudge.js';
import { executeEvaluateHook } from './executeEvaluateHook.js';

/**
 * step_kind → executor 関数のマッピング
 * 新しい step_kind の追加はここに1行追加するだけ
 */
const EXECUTOR_MAP = new Map([
  ['draft_content',       executeDraftContent],
  ['verify_content',      executeVerifyContent],
  ['post_x',              executePostX],
  ['post_tiktok',         executePostTiktok],
  ['fetch_metrics',       executeFetchMetrics],
  ['analyze_engagement',  executeAnalyzeEngagement],
  ['diagnose',            executeDiagnose],
  ['detect_suffering',    executeDetectSuffering],
  ['draft_nudge',         executeDraftNudge],
  ['send_nudge',          executeSendNudge],
  ['evaluate_hook',       executeEvaluateHook],
]);

/**
 * step_kind に対応する executor を取得
 * @param {string} stepKind
 * @returns {Function} executor 関数
 * @throws {Error} 未知の step_kind
 */
export function getExecutor(stepKind) {
  const executor = EXECUTOR_MAP.get(stepKind);
  if (!executor) {
    throw new Error(`Unknown step_kind: ${stepKind}. Available: ${[...EXECUTOR_MAP.keys()].join(', ')}`);
  }
  return executor;
}
```

### 15.2 Executor Interface（共通シグネチャ）

```typescript
// 全 executor はこのシグネチャに従う（TypeScript型参考）
type StepExecutor = (context: {
  stepId: string;
  missionId: string;
  skillName: string;
  input: Record<string, unknown>;       // 前ステップの output またはミッション payload
  proposalPayload: Record<string, unknown>; // 元の提案 payload
}) => Promise<{
  output: Record<string, unknown>;  // 次ステップへの引き継ぎデータ
  events?: Array<{                  // 発行するイベント（0個以上）
    kind: string;
    tags: string[];
    payload?: Record<string, unknown>;
  }>;
}>;
```

### 15.3 各 Executor の実装

#### draft_content（コンテンツ下書き生成）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDraftContent.js

import { selectHookThompson } from '../../hookSelector.js';
import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * Hook選択 → LLMでコンテンツ下書き生成
 *
 * Input: { slot?: 'morning'|'evening' } (cron payload から)
 * Output: { content: string, hookId: string, hookText: string, platform: string }
 */
export async function executeDraftContent({ input, proposalPayload, skillName }) {
  const platform = skillName === 'tiktok-poster' ? 'tiktok' : 'x';
  const slot = input?.slot || proposalPayload?.slot || 'morning';

  // 1. Hook候補をDBから取得
  const hooks = await prisma.hookCandidate.findMany({
    where: {
      relevanceScore: { gt: 0.3 },
      // platform に応じたフィルタ
      ...(platform === 'x' ? { xImpressions: { gt: 0 } } : { tiktokViews: { gt: 0 } })
    },
    orderBy: { createdAt: 'desc' },
    take: 20
  });

  if (hooks.length === 0) {
    throw new Error('No hook candidates available');
  }

  // 2. Thompson Sampling でhook選択
  const selectedHook = await selectHookThompson(hooks.map(h => ({
    ...h,
    successCount: platform === 'x' ? h.xEngagements : h.tiktokEngagements,
    failureCount: Math.max(0,
      (platform === 'x' ? h.xImpressions : h.tiktokViews) -
      (platform === 'x' ? h.xEngagements : h.tiktokEngagements)
    )
  })));

  // 3. LLMでコンテンツ生成
  const prompt = buildDraftPrompt(selectedHook, platform, slot);
  const content = await callLLM(prompt);

  logger.info(`Draft content generated for ${platform} (hook: ${selectedHook.id})`);

  return {
    output: {
      content,
      hookId: selectedHook.id,
      hookText: selectedHook.hookText,
      platform
    },
    events: [] // draft は外部影響なし。イベント不要
  };
}

function buildDraftPrompt(hook, platform, slot) {
  const charLimit = platform === 'x' ? 280 : 2200;
  return `あなたは仏教の行動変容アプリ Anicca のSNSマーケター。
以下のhookをベースに ${platform} 向けの投稿を作成:

Hook: "${hook.hookText}"
関連する苦しみ: ${hook.problemTypes?.join(', ') || '一般'}
時間帯: ${slot}
文字数制限: ${charLimit}文字以内

ルール:
- 「簡単に習慣化！」等の軽い表現は絶対禁止
- 挫折経験を共感で包むトーン
- 直接的な宣伝・リンクは入れない（1.6.2 フェーズでは）
- ハッシュタグは2-3個まで`;
}
```

#### verify_content（コンテンツ検証）

```javascript
// apps/api/src/services/ops/stepExecutors/executeVerifyContent.js

import { verifyWithRegeneration } from '../../verifier.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 生成コンテンツを仏教原則で検証
 *
 * Input: { content: string, hookId: string, platform: string } (draft_content の output)
 * Output: { content: string, verificationScore: number, passed: boolean, attempts: number }
 */
export async function executeVerifyContent({ input }) {
  const { content, platform } = input;

  if (!content) {
    throw new Error('verify_content requires input.content from previous step');
  }

  // verifier.js の verifyWithRegeneration を使用
  // 不合格の場合は自動再生成（最大3回）
  const result = await verifyWithRegeneration(
    async (feedback) => {
      if (!feedback) return content; // 初回はそのまま
      // 再生成: フィードバックを反映
      return callLLM(`以下のコンテンツを修正してください。
元のコンテンツ: "${content}"
フィードバック: ${feedback}
プラットフォーム: ${platform}`);
    },
    {
      threshold: 3, // 5点中3点以上で合格
      maxRetries: 3,
      skillName: 'verify_content',
      context: { platform }
    }
  );

  logger.info(`Content verification: ${result.passed ? 'PASSED' : 'FAILED'} (score: ${result.score}, attempts: ${result.attempts})`);

  if (!result.passed) {
    throw new Error(`Content verification failed after ${result.attempts} attempts (score: ${result.score}/5)`);
  }

  return {
    output: {
      content: result.content, // 検証済み（再生成された可能性あり）
      verificationScore: result.score,
      passed: result.passed,
      attempts: result.attempts,
      // 前ステップのデータも引き継ぎ
      ...input
    },
    events: []
  };
}
```

#### post_x（X投稿実行）

```javascript
// apps/api/src/services/ops/stepExecutors/executePostX.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * X (Twitter) API で投稿
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string, tweetUrl: string }
 * Events: tweet_posted
 *
 * 注意: VPS Worker から呼ばれる。実際のX API呼び出しはVPS側のexecツールで実行。
 * Railway API側ではDB記録とイベント発行のみ。
 */
export async function executePostX({ input, missionId }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_x requires input.content');
  }

  // XPostテーブルに記録（既存スキーマの XPost モデル活用）
  const xPost = await prisma.xPost.create({
    data: {
      content,
      hookCandidateId: hookId || null,
      verificationScore: verificationScore || 0,
      // tweetId は VPS 側で投稿後に更新
      status: 'posted'
    }
  });

  logger.info(`X post recorded: ${xPost.id}`);

  return {
    output: {
      postId: xPost.id,
      dbRecordId: xPost.id,
      platform: 'x'
    },
    events: [{
      kind: 'tweet_posted',
      tags: ['tweet', 'posted'],
      payload: {
        postId: xPost.id,
        hookId,
        verificationScore,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}
```

#### post_tiktok（TikTok投稿実行）

```javascript
// apps/api/src/services/ops/stepExecutors/executePostTiktok.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * TikTok投稿
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string }
 * Events: tiktok_posted
 */
export async function executePostTiktok({ input, missionId }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_tiktok requires input.content');
  }

  const tiktokPost = await prisma.tiktokPost.create({
    data: {
      caption: content,
      hookCandidateId: hookId || null,
      verificationScore: verificationScore || 0,
      status: 'posted'
    }
  });

  logger.info(`TikTok post recorded: ${tiktokPost.id}`);

  return {
    output: {
      postId: tiktokPost.id,
      platform: 'tiktok'
    },
    events: [{
      kind: 'tiktok_posted',
      tags: ['tiktok', 'posted'],
      payload: {
        postId: tiktokPost.id,
        hookId,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}
```

#### fetch_metrics（エンゲージメントデータ取得）

```javascript
// apps/api/src/services/ops/stepExecutors/executeFetchMetrics.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * 投稿のエンゲージメントデータ取得
 * VPS側で X API / TikTok API を呼び出し、結果を返す
 *
 * Input: { triggeredBy: string, eventId: string } (trigger payload から)
 * Output: { metrics: { impressions, engagements, engagementRate }, postId: string }
 */
export async function executeFetchMetrics({ input, proposalPayload }) {
  // トリガーイベントから元の投稿を特定
  const event = await prisma.opsEvent.findUnique({
    where: { id: input.eventId || proposalPayload.eventId }
  });

  if (!event) {
    throw new Error(`Event not found: ${input.eventId}`);
  }

  const postId = event.payload?.postId;
  const platform = event.kind.includes('tweet') ? 'x' : 'tiktok';

  // メトリクスは VPS Worker が X/TikTok API から取得してこのoutputに格納する
  // ここではDBに記録されているメトリクスを返す（VPS Worker が事前にDB更新している想定）

  let metrics;
  if (platform === 'x') {
    const post = await prisma.xPost.findUnique({ where: { id: postId } });
    metrics = {
      impressions: post?.impressions || 0,
      engagements: post?.engagements || 0,
      engagementRate: post?.impressions > 0
        ? (post.engagements / post.impressions * 100).toFixed(2)
        : '0'
    };
  } else {
    const post = await prisma.tiktokPost.findUnique({ where: { id: postId } });
    metrics = {
      views: post?.views || 0,
      likes: post?.likes || 0,
      engagementRate: post?.views > 0
        ? (post.likes / post.views * 100).toFixed(2)
        : '0'
    };
  }

  logger.info(`Metrics fetched for ${platform} post ${postId}: ${JSON.stringify(metrics)}`);

  return {
    output: { metrics, postId, platform },
    events: [{
      kind: `${platform}_metrics_fetched`,
      tags: [platform, 'metrics', 'fetched'],
      payload: { postId, ...metrics }
    }]
  };
}
```

#### analyze_engagement（エンゲージメント分析）

```javascript
// apps/api/src/services/ops/stepExecutors/executeAnalyzeEngagement.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * メトリクスを分析 → shared-learnings に記録 → hook_candidates 更新
 *
 * Input: { metrics: Object, postId: string, platform: string }
 * Output: { analysis: string, isHighEngagement: boolean, learnings: string[] }
 * Events: engagement:high (閾値超) or engagement:low
 */
export async function executeAnalyzeEngagement({ input, missionId }) {
  const { metrics, postId, platform } = input;

  if (!metrics) {
    throw new Error('analyze_engagement requires input.metrics from fetch_metrics step');
  }

  const engagementRate = parseFloat(metrics.engagementRate || '0');
  const isHighEngagement = engagementRate > 5.0; // 5%以上を「高エンゲージメント」

  // LLMで分析
  const analysis = await callLLM(`以下の投稿メトリクスを分析し、学びを3つ箇条書きで:
Platform: ${platform}
Metrics: ${JSON.stringify(metrics)}
Engagement Rate: ${engagementRate}%
判定: ${isHighEngagement ? '高エンゲージメント' : '低エンゲージメント'}`);

  // hook_candidates のスコア更新（Thompson Sampling フィードバック）
  if (postId) {
    const post = platform === 'x'
      ? await prisma.xPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } })
      : await prisma.tiktokPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } });

    if (post?.hookCandidateId) {
      const updateField = platform === 'x'
        ? { xEngagements: { increment: isHighEngagement ? 1 : 0 } }
        : { tiktokEngagements: { increment: isHighEngagement ? 1 : 0 } };

      await prisma.hookCandidate.update({
        where: { id: post.hookCandidateId },
        data: updateField
      });
    }
  }

  logger.info(`Engagement analysis: ${platform} post ${postId} — ${isHighEngagement ? 'HIGH' : 'LOW'} (${engagementRate}%)`);

  return {
    output: {
      analysis,
      isHighEngagement,
      engagementRate,
      platform
    },
    events: [{
      kind: isHighEngagement ? 'engagement:high' : 'engagement:low',
      tags: ['engagement', isHighEngagement ? 'high' : 'low'],
      payload: { postId, platform, engagementRate, analysis: analysis.substring(0, 200) }
    }]
  };
}
```

#### detect_suffering（苦しみ検出）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDetectSuffering.js

import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * Web検索で苦しみに関するトレンド・投稿を検出
 * VPS Worker の web_search ツールで実行
 *
 * Input: {} (パラメータなし)
 * Output: { detections: Array<{text, severity, problemType, source}> }
 * Events: suffering_detected (severity >= 0.6)
 */
export async function executeDetectSuffering({ skillName }) {
  // この関数は VPS Worker から呼ばれ、web_search ツールを使う
  // Railway API 側ではスケルトンのみ定義。実際の検出ロジックは SKILL.md に記述

  // VPS Worker が検出結果を output に格納して step/complete に報告する想定
  // ここでは「VPS が返した output をそのまま通す」パススルー構造

  logger.info('detect_suffering: VPS Worker が web_search で検出を実行');

  return {
    output: {
      note: 'VPS Worker executes web_search and returns detections in step/complete output'
    },
    events: []
    // 注: 実際のイベント発行は VPS Worker が step/complete を呼ぶ際に、
    // Railway API の completeStep ハンドラが output.detections を見てイベントを発行する
  };
}
```

#### diagnose（ミッション失敗診断）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDiagnose.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 失敗したミッションの原因を分析し、学びを記録
 *
 * Input: { eventId: string } (mission:failed イベントから)
 * Output: { diagnosis: string, rootCause: string, recommendation: string }
 */
export async function executeDiagnose({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload.eventId;
  const event = await prisma.opsEvent.findUnique({ where: { id: eventId } });

  if (!event) {
    throw new Error(`Event not found: ${eventId}`);
  }

  // 失敗したミッションの詳細を取得
  const missionId = event.payload?.missionId;
  const mission = missionId ? await prisma.opsMission.findUnique({
    where: { id: missionId },
    include: {
      steps: { orderBy: { stepOrder: 'asc' } },
      proposal: true
    }
  }) : null;

  const failedSteps = mission?.steps?.filter(s => s.status === 'failed') || [];

  // LLMで診断
  const diagnosis = await callLLM(`以下のミッション失敗を診断:
Mission: ${mission?.proposal?.title || 'unknown'}
Skill: ${event.source}
Failed Steps: ${JSON.stringify(failedSteps.map(s => ({
    kind: s.stepKind,
    error: s.lastError
  })))}

根本原因を特定し、再発防止策を提案:`);

  logger.info(`Diagnosis complete for mission ${missionId}`);

  return {
    output: {
      diagnosis,
      failedMissionId: missionId,
      failedStepKinds: failedSteps.map(s => s.stepKind)
    },
    events: [{
      kind: 'diagnosis:completed',
      tags: ['diagnosis', 'completed'],
      payload: { missionId, diagnosisPreview: diagnosis.substring(0, 200) }
    }]
  };
}
```

#### draft_nudge / send_nudge / evaluate_hook

```javascript
// apps/api/src/services/ops/stepExecutors/executeDraftNudge.js

import { callLLM } from '../../../lib/llm.js';

/**
 * 苦しみ検出結果に基づいてNudge下書きを生成
 *
 * Input: { detections: Array<{text, severity, problemType}> } (detect_suffering の output)
 * Output: { nudgeContent: string, targetProblemType: string, severity: number }
 */
export async function executeDraftNudge({ input }) {
  const detections = input.detections || [];
  const topDetection = detections.sort((a, b) => (b.severity || 0) - (a.severity || 0))[0];

  if (!topDetection) {
    return { output: { nudgeContent: null, skipped: true }, events: [] };
  }

  const nudgeContent = await callLLM(`以下の苦しみに対する Nudge メッセージ（通知文）を生成:
苦しみ: "${topDetection.text}"
種別: ${topDetection.problemType}
重要度: ${topDetection.severity}

ルール:
- 責めない、共感するトーン
- 小さすぎるステップを提案
- 50文字以内`);

  return {
    output: {
      nudgeContent,
      targetProblemType: topDetection.problemType,
      severity: topDetection.severity
    },
    events: []
  };
}
```

```javascript
// apps/api/src/services/ops/stepExecutors/executeSendNudge.js

import { logger } from '../../../lib/logger.js';

/**
 * Nudge送信（Push通知）
 *
 * Input: { nudgeContent: string, targetProblemType: string }
 * Output: { sent: boolean }
 * Events: nudge_sent
 *
 * 注: 実際の送信は VPS Worker が Railway API の /api/mobile/nudge/ を呼ぶ
 */
export async function executeSendNudge({ input }) {
  const { nudgeContent, targetProblemType } = input;

  if (!nudgeContent || input.skipped) {
    logger.info('send_nudge skipped: no content');
    return { output: { sent: false, skipped: true }, events: [] };
  }

  // VPS Worker が実際に送信を実行
  logger.info(`Nudge ready to send: ${targetProblemType} — "${nudgeContent}"`);

  return {
    output: {
      sent: true,
      nudgeContent,
      targetProblemType
    },
    events: [{
      kind: 'nudge_sent',
      tags: ['nudge', 'sent'],
      payload: { targetProblemType, contentPreview: nudgeContent.substring(0, 30) }
    }]
  };
}
```

```javascript
// apps/api/src/services/ops/stepExecutors/executeEvaluateHook.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * trend-hunter が見つけた hook_candidate を x-poster が評価
 *
 * Input: { eventId: string } (hook_saved イベントの eventId。Reaction Matrix が payload.hookId → eventId を注入)
 * Output: { evaluation: string, shouldPost: boolean }
 */
export async function executeEvaluateHook({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload.eventId;
  const event = await prisma.opsEvent.findUnique({ where: { id: eventId } });

  if (!event?.payload?.hookId) {
    return { output: { shouldPost: false, reason: 'no hook in event' }, events: [] };
  }

  const hook = await prisma.hookCandidate.findUnique({
    where: { id: event.payload.hookId }
  });

  if (!hook) {
    return { output: { shouldPost: false, reason: 'hook not found' }, events: [] };
  }

  const evaluation = await callLLM(`以下の hook を X 投稿に使えるか評価:
Hook: "${hook.hookText}"
Problem Types: ${hook.problemTypes?.join(', ')}
Relevance Score: ${hook.relevanceScore}

判定基準:
1. ターゲットペルソナ（6-7年挫折した25-35歳）に刺さるか
2. 「簡単に習慣化！」系の軽い表現でないか
3. 共感ベースのトーンか
→ shouldPost: true/false で回答`);

  const shouldPost = evaluation.toLowerCase().includes('true');

  logger.info(`Hook evaluation: ${hook.id} — shouldPost: ${shouldPost}`);

  return {
    output: { evaluation, shouldPost, hookId: hook.id },
    events: shouldPost ? [{
      kind: 'hook:approved_for_post',
      tags: ['hook', 'approved'],
      payload: { hookId: hook.id, hookText: hook.hookText }
    }] : []
  };
}
```

### 15.4 VPS Worker が Executor を呼ぶフロー

```
VPS Worker (1分毎ポーリング)
    |
    v
GET /api/ops/step/next
    |
    v (step が返ってきた)
    |
    v
step.stepKind を確認
    |
    +----> 'draft_content'  → hookSelector + LLM（VPS上で直接実行）
    +----> 'verify_content' → verifier.js（VPS上で直接実行）
    +----> 'post_x'         → X API 呼び出し（VPS上で exec ツール）
    +----> 'detect_suffering'→ web_search（VPS上で web_search ツール）
    +----> ...
    |
    v
PATCH /api/ops/step/:id/complete { status, output, events }
    |
    v
Railway API が output を DB に保存 + body.events があればイベント発行 → 次のステップの input になる
```

> **重要**: Railway API 側の executor はロジックの「定義」。VPS Worker は SKILL.md に従って
> 実際のAPI呼び出しやLLM呼び出しを実行し、その結果を step/complete で報告する。
> Railway API 側の executor は「どんなデータが流れるか」を規定するインターフェース。

---

## 16. Step-to-Step データパッシング

> **Gap P0 #6 解消**: Step 0 の output が Step 1 の input になる仕組み
> **設計方針**: Temporal Workflow の子ワークフロー引数渡しパターンを参考に、
> シンプルに「前ステップの output を次ステップの input にマージ」する

### 16.1 データフロー図（x-poster パイプライン例）

```
Step 0: draft_content
  input:  { slot: "morning" }  ← proposalPayload から
  output: { content: "挫折は恥じゃない...", hookId: "abc", platform: "x" }
                  ↓
Step 1: verify_content
  input:  { content: "挫折は恥じゃない...", hookId: "abc", platform: "x" }  ← Step 0 の output
  output: { content: "挫折は恥じゃない...", verificationScore: 4, passed: true, hookId: "abc", platform: "x" }
                  ↓
Step 2: post_x
  input:  { content: "挫折は恥じゃない...", verificationScore: 4, hookId: "abc", platform: "x" }  ← Step 1 の output
  output: { postId: "xyz", platform: "x" }
  events: [{ kind: "tweet_posted", tags: ["tweet", "posted"], payload: { postId: "xyz", hookId: "abc" } }]
```

### 16.2 GET /api/ops/step/next の修正（前ステップ output 注入）

```javascript
// 既存の GET /api/ops/step/next を修正
// 変更箇所: ★ マーク

router.get('/step/next', async (req, res) => {
  const step = await prisma.$transaction(async (tx) => {
    const next = await tx.opsMissionStep.findFirst({
      where: { status: 'queued' },
      orderBy: [
        { createdAt: 'asc' },
        { stepOrder: 'asc' }
      ],
      include: {
        mission: {
          include: { proposal: true }
        }
      }
    });

    if (!next) return null;

    // 同一ミッション内で前のステップが完了しているか確認
    let previousOutput = {};  // ★ 追加
    if (next.stepOrder > 0) {
      const prevStep = await tx.opsMissionStep.findFirst({
        where: {
          missionId: next.missionId,
          stepOrder: next.stepOrder - 1
        }
      });
      if (prevStep && prevStep.status !== 'succeeded') {
        return null; // 前のステップがまだ完了していない
      }
      previousOutput = prevStep?.output || {};  // ★ 追加: 前ステップの output を取得
    }

    // running に更新（claim）
    await tx.opsMissionStep.update({
      where: { id: next.id },
      data: {
        status: 'running',
        reservedAt: new Date(),
        // ★ 追加: 前ステップの output を input にマージ
        input: {
          ...(next.input || {}),         // ミッション作成時の静的 input
          ...previousOutput               // 前ステップの output（動的データ）
        }
      }
    });

    return { ...next, mergedInput: { ...(next.input || {}), ...previousOutput } };
  });

  if (!step) {
    return res.json({ step: null });
  }

  res.json({
    step: {
      id: step.id,
      missionId: step.missionId,
      stepKind: step.stepKind,
      stepOrder: step.stepOrder,
      input: step.mergedInput,  // ★ 変更: マージ済み input を返す
      proposalPayload: step.mission.proposal.payload,
      skillName: step.mission.proposal.skillName
    }
  });
});
```

### 16.3 PATCH /api/ops/step/:id/complete の修正（イベント自動発行）

```javascript
// 既存の PATCH /api/ops/step/:id/complete を修正
// 変更箇所: ★ マーク

router.patch('/step/:id/complete', async (req, res) => {
  const { id } = req.params;
  const parsed = StepCompleteSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { status, output, error } = parsed.data;

  const step = await prisma.opsMissionStep.update({
    where: { id },
    data: {
      status,
      output: output || {},
      lastError: error || null,
      completedAt: new Date()
    },
    include: {  // ★ 追加: mission + proposal を include
      mission: { include: { proposal: true } }
    }
  });

  // ★ 追加: body.events があればイベントを発行（正規版は 05-step-executors.md §16.3 参照）
  const { events: bodyEvents } = parsed.data;
  const { emitEvent } = await import('../../services/ops/eventEmitter.js');
  if (bodyEvents && Array.isArray(bodyEvents)) {
    for (const evt of bodyEvents) {
      await emitEvent(
        step.mission.proposal.skillName,
        evt.kind,
        evt.tags || [],
        evt.payload || {},
        step.missionId
      );
    }
  }

  // ★ 追加: detect_suffering の detections からイベント発行
  if (step.stepKind === 'detect_suffering' && output?.detections) {
    for (const detection of output.detections) {
      if (detection.severity >= 0.6) {
        await emitEvent(
          step.mission.proposal.skillName,
          'suffering_detected',
          ['suffering', 'detected'],
          detection,
          step.missionId
        );
      }
    }
  }

  // ミッション最終化判定
  const missionStatus = await maybeFinalizeMission(step.missionId);

  res.json({ ok: true, stepStatus: status, missionStatus });
});
```

---

## 17. Slack Interactive 承認フロー

> **Gap P1 #2 解消**: `post_x`, `post_tiktok`, `send_nudge` 等の auto-approve 対象外ステップの人間承認
> **設計方針**: Slack Block Kit の Approve/Reject ボタン → OpenClaw が Webhook 受信 → Railway API で承認処理
> **参考**: Slack Block Actions Payload Reference (docs.slack.dev)

### 17.1 承認通知の送信

```javascript
// apps/api/src/services/ops/approvalNotifier.js

import { logger } from '../../lib/logger.js';

const APPROVAL_CHANNEL = process.env.SLACK_CHANNEL_OPS || '#ops-approval';

/**
 * pending 状態の提案に対して Slack 承認通知を送信
 * createProposalAndMaybeAutoApprove() で auto-approve されなかった場合に呼ばれる
 *
 * @param {Object} proposal - OpsProposal
 */
export async function sendApprovalNotification(proposal) {
  const blocks = [
    {
      type: 'header',
      text: { type: 'plain_text', text: `承認リクエスト: ${proposal.title}` }
    },
    {
      type: 'section',
      fields: [
        { type: 'mrkdwn', text: `*Skill:*\n${proposal.skillName}` },
        { type: 'mrkdwn', text: `*Source:*\n${proposal.source}` },
        { type: 'mrkdwn', text: `*Proposal ID:*\n\`${proposal.id}\`` }
      ]
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Payload:*\n\`\`\`${JSON.stringify(proposal.payload, null, 2)}\`\`\``
      }
    },
    {
      type: 'actions',
      block_id: `ops_approval_${proposal.id}`,
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Approve' },
          style: 'primary',
          action_id: 'ops_approve',
          value: proposal.id
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Reject' },
          style: 'danger',
          action_id: 'ops_reject',
          value: proposal.id
        }
      ]
    }
  ];

  // OpenClaw の slack ツール経由で送信
  // VPS から: openclaw message send --channel slack --target "<CHANNEL_ID>" --message <blocks JSON>
  // または Railway API から Slack Web API 直接:
  logger.info(`Approval notification sent for proposal ${proposal.id}`);

  return { blocks, channel: APPROVAL_CHANNEL };
}
```

### 17.2 承認/リジェクト処理

```javascript
// apps/api/src/services/ops/approvalHandler.js

import { prisma } from '../../lib/prisma.js';
import { emitEvent } from './eventEmitter.js';
import { logger } from '../../lib/logger.js';

/**
 * 提案を承認 → Mission + Steps を作成
 *
 * @param {string} proposalId
 * @returns {Object} { missionId }
 */
export async function approveProposal(proposalId) {
  const proposal = await prisma.opsProposal.findUnique({
    where: { id: proposalId }
  });

  if (!proposal || proposal.status !== 'pending') {
    throw new Error(`Proposal ${proposalId} is not in pending state (current: ${proposal?.status})`);
  }

  // payload からステップ定義を復元
  // 提案作成時に steps 情報も payload に保存しておく必要がある
  const stepDefs = proposal.payload?.steps || [];
  if (stepDefs.length === 0) {
    throw new Error(`Proposal ${proposalId} has no step definitions in payload`);
  }

  // Mission + Steps 作成
  const mission = await prisma.opsMission.create({
    data: {
      proposalId: proposal.id,
      status: 'running',
      steps: {
        create: stepDefs.map(s => ({
          stepKind: s.kind,
          stepOrder: s.order,
          status: 'queued',
          input: s.input || {}
        }))
      }
    },
    include: { steps: true }
  });

  // 提案を accepted に更新
  await prisma.opsProposal.update({
    where: { id: proposalId },
    data: { status: 'accepted', resolvedAt: new Date() }
  });

  await emitEvent(proposal.skillName, 'proposal:manually_approved', ['proposal', 'approved', 'manual'], {
    proposalId: proposal.id,
    missionId: mission.id
  });

  logger.info(`Proposal manually approved: ${proposal.title} → Mission ${mission.id}`);
  return { missionId: mission.id };
}

/**
 * 提案をリジェクト
 *
 * @param {string} proposalId
 * @param {string} reason - リジェクト理由
 */
export async function rejectProposal(proposalId, reason = 'Manually rejected') {
  await prisma.opsProposal.update({
    where: { id: proposalId },
    data: {
      status: 'rejected',
      rejectReason: reason,
      resolvedAt: new Date()
    }
  });

  const proposal = await prisma.opsProposal.findUnique({ where: { id: proposalId } });

  await emitEvent(proposal.skillName, 'proposal:manually_rejected', ['proposal', 'rejected', 'manual'], {
    proposalId,
    reason
  });

  logger.info(`Proposal manually rejected: ${proposalId} — ${reason}`);
}
```

### 17.3 API エンドポイント（Slack Webhook 受信用）

```javascript
// apps/api/src/routes/ops/approval.js

import { Router } from 'express';
import { approveProposal, rejectProposal } from '../../services/ops/approvalHandler.js';
import { logger } from '../../lib/logger.js';

const router = Router();

/**
 * POST /api/ops/approval
 * Slack Block Kit の block_actions ペイロードを受信
 *
 * OpenClaw VPS 側から転送される:
 * Slack → OpenClaw Gateway → exec で Railway API に転送
 *
 * 代替: Slack App の Interactivity URL を直接 Railway に向ける
 */
router.post('/approval', async (req, res) => {
  try {
    // Slack block_actions payload のパース
    const payload = typeof req.body.payload === 'string'
      ? JSON.parse(req.body.payload)
      : req.body;

    const action = payload.actions?.[0];
    if (!action) {
      return res.status(400).json({ error: 'No action in payload' });
    }

    const proposalId = action.value;
    const actionId = action.action_id;

    if (actionId === 'ops_approve') {
      const result = await approveProposal(proposalId);
      // Slack にレスポンス（ボタンを更新）
      res.json({
        replace_original: true,
        text: `✅ 承認済み: Mission ${result.missionId} が開始されました`
      });
    } else if (actionId === 'ops_reject') {
      await rejectProposal(proposalId, 'Rejected via Slack');
      res.json({
        replace_original: true,
        text: `❌ リジェクト済み: Proposal ${proposalId}`
      });
    } else {
      res.status(400).json({ error: `Unknown action: ${actionId}` });
    }
  } catch (error) {
    logger.error('Approval handler error:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

### 17.4 proposalService.js への統合（pending 時に通知送信）

```javascript
// createProposalAndMaybeAutoApprove() の末尾に追加:

  // 自動承認対象外 → pending のまま（人間承認待ち）
  // ★ 追加: Slack 承認通知を送信
  const { sendApprovalNotification } = await import('./approvalNotifier.js');
  await sendApprovalNotification(proposal);

  logger.info(`Proposal awaiting approval: ${title} (contains non-auto-approvable steps)`);
  return { proposalId: proposal.id, status: 'pending' };
```

### 17.5 proposalService.js の steps 保存修正

```javascript
// createProposalAndMaybeAutoApprove() の提案INSERT部分を修正:

  // 3. 提案を INSERT
  // ★ 修正: payload に steps 情報も保存（承認時に復元するため）
  const proposal = await prisma.opsProposal.create({
    data: {
      skillName,
      source,
      status: 'pending',
      title,
      payload: { ...payload, steps }  // ★ steps を payload に含める
    }
  });
```

---

## 18. 既存 Skill 移行パス

> **Gap P1 #4 解消**: 既存のスキルを閉ループ対応に移行する方法
> **方針**: 既存 SKILL.md を「閉ループ対応版」に書き換え。skill-creator で再作成

### 18.1 移行チェックリスト

| # | スキル | 現行 | 閉ループ対応後 | 移行難易度 |
|---|--------|------|---------------|-----------|
| 1 | x-poster | 直接 X API 呼び出し + Slack 報告 | Proposal → Mission → Steps (draft→verify→post) | 中 |
| 2 | tiktok-poster | 直接 TikTok API 呼び出し + Slack 報告 | Proposal → Mission → Steps (draft→verify→post) | 中 |
| 3 | trend-hunter | web_search → hook_candidates INSERT | Proposal → Mission → Step (run_trend_scan) — 単一ステップ内で4ソース収集→フィルタ→hook生成→保存→イベント発行を全実行 | 低 |
| 4 | suffering-detector | Moltbook 検索 → 返信 | Proposal → Mission → Step (detect_suffering) | 低 |
| 5 | app-nudge-sender | 直接 Push通知 | Proposal → Mission → Steps (draft_nudge→send_nudge) | 中 |

### 18.2 x-poster SKILL.md Before/After

**BEFORE（現行: 直接実行型）:**
```yaml
---
name: x-poster
description: X(Twitter)にAnicca関連の投稿をする
---

# x-poster

1. hook_candidates テーブルから候補を取得
2. Thompson Sampling でhook選択
3. LLMでコンテンツ生成
4. verifier.js で検証（3/5以上で合格）
5. X API で投稿
6. Slackに結果報告
```

**AFTER（閉ループ対応: Proposal 経由）:**
```yaml
---
name: x-poster
description: X(Twitter)にAnicca関連の投稿をする（閉ループ対応）
metadata:
  openclaw:
    emoji: "🐦"
    requires:
      env: ["ANICCA_AGENT_TOKEN"]
---

# x-poster（閉ループ版）

## 概要
Cron から呼ばれた時、直接投稿せずに Proposal を生成する。
実際の実行は mission-worker が行う。

## Instructions

1. Cron メッセージから slot (morning/evening) を受け取る
2. 以下のJSONを POST /api/ops/proposal に送信:
   ```json
   {
     "skillName": "x-poster",
     "source": "cron",
     "title": "X{slot}投稿",
     "payload": { "slot": "{slot}" },
     "steps": [
       { "kind": "draft_content", "order": 0 },
       { "kind": "verify_content", "order": 1 },
       { "kind": "post_x", "order": 2 }
     ]
   }
   ```
3. レスポンスを確認:
   - `status: "accepted"` → ログに記録（mission-worker が実行する）
   - `status: "rejected"` → リジェクト理由をログに記録
   - `status: "pending"` → 人間承認待ち（Slack通知済み）

## 注意
- 直接 X API を呼んではいけない（mission-worker の担当）
- このスキルは「提案を作る」だけ。実行はしない
```

### 18.3 mission-worker SKILL.md（詳細版）

```yaml
---
name: mission-worker
description: Ops閉ループの実行エンジン。queued ステップを取得→実行→完了報告
metadata:
  openclaw:
    emoji: "⚙️"
    requires:
      env: ["ANICCA_AGENT_TOKEN"]
      tools: ["exec", "web_search", "slack", "read", "write"]
---

# mission-worker

## 概要
1分毎にポーリングし、次の queued ステップを取得→実行→完了報告する。
全ての外部API呼び出し（X API, TikTok API, LLM等）はこのワーカーが担当。

## Instructions

### 1. ステップ取得
```bash
curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  $API_BASE_URL/api/ops/step/next
```

レスポンス `step: null` の場合 → 正常終了（何もしない）

### 2. ステップ実行（step_kind 別）

| step_kind | 処理内容 | 使用ツール |
|-----------|---------|-----------|
| `draft_content` | hookSelector → LLMでコンテンツ生成 | exec (API呼び出し) |
| `verify_content` | verifier.js でコンテンツ検証 | exec (API呼び出し) |
| `post_x` | X API v2 で投稿 | exec (curl) |
| `post_tiktok` | TikTok API で投稿 | exec (curl) |
| `fetch_metrics` | X/TikTok API でメトリクス取得 | exec (curl) |
| `analyze_engagement` | LLMで分析 + shared-learnings 記録 | exec, write |
| `detect_suffering` | Web検索で苦しみ関連トレンド検出 | web_search |
| `draft_nudge` | LLMでNudge下書き生成 | exec |
| `send_nudge` | Railway API 経由でPush通知 | exec |
| `diagnose` | 失敗ミッションの原因分析 | exec, read |
| `evaluate_hook` | hook_candidate の投稿適合性評価 | exec |

### 3. 完了報告
```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "succeeded", "output": {...}}' \
  $API_BASE_URL/api/ops/step/{stepId}/complete
```

### 4. エラーハンドリング

| エラー | 対応 |
|--------|------|
| API呼び出し失敗 | 3回リトライ（Equal Jitter Backoff）後、status: "failed" で報告 |
| LLM生成失敗 | フォールバックチェーン: OpenAI → Anthropic → Groq |
| X/TikTok rate limit | status: "failed" + error: "rate_limited" で報告 |
| タイムアウト | 5分で強制終了 + status: "failed" で報告 |

### 5. output に含めるべきデータ

step_kind ごとの output スキーマ（次ステップの input になる）:

| step_kind | output 必須フィールド |
|-----------|---------------------|
| `draft_content` | `content`, `hookId`, `hookText`, `platform` |
| `verify_content` | `content`, `verificationScore`, `passed` |
| `post_x` | `postId`, `tweetUrl` |
| `post_tiktok` | `postId` |
| `fetch_metrics` | `metrics`, `postId`, `platform` |
| `analyze_engagement` | `analysis`, `isHighEngagement`, `engagementRate` |
| `detect_suffering` | `detections[]` (各: text, severity, problemType) |
```

---

## 19. delay_min トリガーロジック修正

> **Gap P1 #7 解消**: delay_min の検索範囲が5分では足りない問題
> **問題**: `delay_min: 1440` (24時間) のトリガーは、24時間前のイベントを検索する必要があるが、
> 現行は「lastFiredAt 以降 or 直近5分」しか検索しない。24時間前のイベントが漏れる。

### 19.1 修正方針

`delay_min` がある場合、検索範囲を `delay_min` + バッファに広げる。

### 19.2 triggerEvaluator.js 修正箇所

```javascript
// 修正前（Section 6.6 の since 計算）:
const since = rule.lastFiredAt || new Date(Date.now() - 5 * 60 * 1000);

// 修正後:
// delay_min がある場合、検索範囲を delay_min × 1.5 に広げる（バッファ付き）
const delayMin = rule.condition?.delay_min || 0;
const searchWindowMs = delayMin > 0
  ? delayMin * 1.5 * 60 * 1000     // delay_min × 1.5（バッファ）
  : 5 * 60 * 1000;                   // デフォルト5分
const since = rule.lastFiredAt || new Date(Date.now() - searchWindowMs);
```

### 19.3 checkTriggerCondition の修正

```javascript
// 修正後: delay_min は「イベント発生からN分経過したか」をチェック
function checkTriggerCondition(condition, event) {
  // delay_min: イベント発生からN分経過して初めて発火
  if (condition.delay_min) {
    const eventAgeMin = (Date.now() - event.createdAt.getTime()) / (1000 * 60);
    // N分未満なら「まだ早い」→ false
    if (eventAgeMin < condition.delay_min) return false;
    // N分 × 2 以上なら「古すぎる」→ false（二重発火防止）
    if (eventAgeMin > condition.delay_min * 2) return false;
  }

  // min_severity: ペイロードの severity が閾値以上
  if (condition.min_severity) {
    const severity = event.payload?.severity ?? 0;
    if (severity < condition.min_severity) return false;
  }

  return true;
}
```

---

## 20. emitEvent → evaluateReactionMatrix 接続

> **Gap P2 #5 解消**: イベント発行後に Reaction Matrix を自動評価する
> **修正箇所**: eventEmitter.js のみ

### 20.1 eventEmitter.js 修正

```javascript
// apps/api/src/services/ops/eventEmitter.js（修正版）

import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

/**
 * イベント発行 + Reaction Matrix 自動評価
 *
 * @param {string} source
 * @param {string} kind
 * @param {string[]} tags
 * @param {Object} payload
 * @param {string} [missionId]
 * @returns {Object} 作成されたイベント
 */
export async function emitEvent(source, kind, tags, payload = {}, missionId = null) {
  const event = await prisma.opsEvent.create({
    data: {
      source,
      kind,
      tags,
      payload,
      missionId
    }
  });

  // ★ Reaction Matrix 自動評価
  // 循環参照を避けるため動的 import
  try {
    const { evaluateReactionMatrix } = await import('./reactionProcessor.js');
    await evaluateReactionMatrix(event);
  } catch (err) {
    // Reaction 評価の失敗はイベント発行自体を止めない
    logger.warn(`Reaction matrix evaluation failed for event ${event.id}:`, err.message);
  }

  return event;
}
```

---

## 21. テスト基盤（Vitest + Supertest + Prisma Mock）

> **Gap P2 #8 解消**: テスト実行環境の具体的なセットアップ
> **方針**: Vitest v4 + `vitest-mock-extended` で Prisma クライアントをモック

### 21.1 Vitest 設定

```javascript
// apps/api/vitest.config.js

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.js'],
    coverage: {
      provider: 'v8',
      include: ['src/services/ops/**'],
      threshold: { lines: 80, branches: 80, functions: 80 }
    },
    setupFiles: ['./src/test/setup.js']
  }
});
```

### 21.2 テストセットアップ（Prisma Mock）

```javascript
// apps/api/src/test/setup.js

import { vi, beforeEach } from 'vitest';
import { mockDeep, mockReset } from 'vitest-mock-extended';

// Prisma クライアントのモック
const prismaMock = mockDeep();

vi.mock('../lib/prisma.js', () => ({
  prisma: prismaMock
}));

// 各テスト前にモックリセット
beforeEach(() => {
  mockReset(prismaMock);
});

export { prismaMock };
```

### 21.3 ユニットテスト例（T1: proposalService）

```javascript
// apps/api/src/services/ops/__tests__/proposalService.test.js

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { prismaMock } from '../../../test/setup.js';
import { createProposalAndMaybeAutoApprove } from '../proposalService.js';

// policyService をモック
vi.mock('../policyService.js', () => ({
  getPolicy: vi.fn()
}));

import { getPolicy } from '../policyService.js';

describe('createProposalAndMaybeAutoApprove', () => {
  const validInput = {
    skillName: 'x-poster',
    source: 'cron',
    title: 'X朝投稿',
    payload: { slot: 'morning' },
    steps: [
      { kind: 'draft_content', order: 0 },
      { kind: 'verify_content', order: 1 }
    ]
  };

  beforeEach(() => {
    // 日次提案数 = 0（上限に達していない）
    prismaMock.opsProposal.count.mockResolvedValue(0);

    // auto_approve ポリシー
    getPolicy.mockImplementation(async (key) => {
      if (key === 'auto_approve') {
        return {
          enabled: true,
          allowed_step_kinds: ['draft_content', 'verify_content', 'detect_suffering', 'analyze_engagement', 'fetch_metrics']
        };
      }
      return null;
    });
  });

  // T1: 正常系 — auto-approve 対象
  it('should auto-approve when all steps are auto-approvable', async () => {
    const mockProposal = { id: 'proposal-1', ...validInput, status: 'pending' };
    const mockMission = { id: 'mission-1', steps: [] };

    prismaMock.opsProposal.create.mockResolvedValue(mockProposal);
    prismaMock.opsMission.create.mockResolvedValue(mockMission);
    prismaMock.opsProposal.update.mockResolvedValue({ ...mockProposal, status: 'accepted' });
    prismaMock.opsEvent.create.mockResolvedValue({});

    const result = await createProposalAndMaybeAutoApprove(validInput);

    expect(result.status).toBe('accepted');
    expect(result.missionId).toBe('mission-1');
    expect(prismaMock.opsMission.create).toHaveBeenCalledOnce();
  });

  // T3: auto-approve 対象外 → pending
  it('should remain pending when steps contain non-auto-approvable kinds', async () => {
    const inputWithPostX = {
      ...validInput,
      steps: [
        { kind: 'draft_content', order: 0 },
        { kind: 'post_x', order: 1 }  // auto-approve 対象外
      ]
    };

    const mockProposal = { id: 'proposal-2', ...inputWithPostX, status: 'pending', payload: { ...inputWithPostX.payload, steps: inputWithPostX.steps } };
    prismaMock.opsProposal.create.mockResolvedValue(mockProposal);
    prismaMock.opsEvent.create.mockResolvedValue({});

    const result = await createProposalAndMaybeAutoApprove(inputWithPostX);

    expect(result.status).toBe('pending');
    expect(result.missionId).toBeUndefined();
    expect(prismaMock.opsMission.create).not.toHaveBeenCalled();
  });

  // T4: 日次上限到達
  it('should reject when daily proposal limit reached', async () => {
    prismaMock.opsProposal.count.mockResolvedValue(100); // 上限

    const result = await createProposalAndMaybeAutoApprove(validInput);

    expect(result.status).toBe('rejected');
    expect(result.rejectReason).toBe('daily_proposal_limit');
  });
});
```

### 21.4 Integration テスト例（T19: Heartbeat API）

```javascript
// apps/api/src/routes/ops/__tests__/heartbeat.integration.test.js

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { app } from '../../../app.js'; // Express app

describe('GET /api/ops/heartbeat', () => {
  const AGENT_TOKEN = process.env.ANICCA_AGENT_TOKEN || 'test-token';

  // T19: 正常レスポンス
  it('should return 200 with heartbeat results', async () => {
    const res = await request(app)
      .get('/api/ops/heartbeat')
      .set('Authorization', `Bearer ${AGENT_TOKEN}`);

    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(res.body).toHaveProperty('elapsed');
    expect(res.body).toHaveProperty('triggers');
    expect(res.body).toHaveProperty('reactions');
    expect(res.body).toHaveProperty('stale');
  });

  // T26: トークンなし→401
  it('should return 401 without token', async () => {
    const res = await request(app)
      .get('/api/ops/heartbeat');

    expect(res.status).toBe(401);
  });

  // T27: 不正トークン→401
  it('should return 401 with bad token', async () => {
    const res = await request(app)
      .get('/api/ops/heartbeat')
      .set('Authorization', 'Bearer wrong-token');

    expect(res.status).toBe(401);
  });
});
```

### 21.5 テスト実行コマンド

```bash
# ユニットテスト
cd apps/api && npx vitest run

# カバレッジ付き
cd apps/api && npx vitest run --coverage

# 特定ファイル
cd apps/api && npx vitest run src/services/ops/__tests__/proposalService.test.js

# ウォッチモード
cd apps/api && npx vitest
```

---

## 22. 監視・アラート

> **Gap P2 #10 解消**: 失敗スパイク検知 + 日次 Ops サマリー

### 22.1 失敗アラート（Heartbeat 内で判定）

```javascript
// apps/api/src/services/ops/opsMonitor.js

import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

const FAILURE_THRESHOLD = 5;  // 直近1時間で5回以上失敗 → アラート
const ALERT_COOLDOWN_MS = 60 * 60 * 1000; // 1時間に1回まで

let lastAlertAt = 0;

/**
 * Heartbeat 内で呼ばれる監視チェック
 *
 * @returns {{ alert: boolean, failureCount: number, message?: string }}
 */
export async function checkOpsHealth() {
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);

  // 直近1時間の failed ステップ数
  const failureCount = await prisma.opsMissionStep.count({
    where: {
      status: 'failed',
      completedAt: { gte: oneHourAgo }
    }
  });

  // 直近1時間の pending 提案数（承認されていない）
  const pendingCount = await prisma.opsProposal.count({
    where: {
      status: 'pending',
      createdAt: { gte: oneHourAgo }
    }
  });

  const shouldAlert = failureCount >= FAILURE_THRESHOLD
    && (Date.now() - lastAlertAt > ALERT_COOLDOWN_MS);

  if (shouldAlert) {
    lastAlertAt = Date.now();
    const message = `⚠️ Ops Alert: ${failureCount} step failures in the last hour. ${pendingCount} proposals pending approval.`;
    logger.warn(message);

    return { alert: true, failureCount, pendingCount, message };
  }

  return { alert: false, failureCount, pendingCount };
}
```

### 22.2 日次 Ops サマリー（Cron で毎朝実行）

```yaml
# schedule.yaml に追加
ops-daily-summary:
  cron: "0 6 * * *"  # 毎日06:00 JST
  session: isolated
  kind: agentTurn
  delivery:
    mode: "none"
  message: |
    以下のAPIを叩いて、結果を #ops-summary チャンネルに投稿してください:
    GET /api/ops/summary/daily
```

```javascript
// apps/api/src/routes/ops/summary.js

import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

/**
 * GET /api/ops/summary/daily
 * 直近24時間の Ops サマリーを返す
 */
router.get('/summary/daily', async (req, res) => {
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000);

  const [proposals, missions, steps, events] = await Promise.all([
    prisma.opsProposal.groupBy({
      by: ['status'],
      where: { createdAt: { gte: since } },
      _count: true
    }),
    prisma.opsMission.groupBy({
      by: ['status'],
      where: { createdAt: { gte: since } },
      _count: true
    }),
    prisma.opsMissionStep.groupBy({
      by: ['status'],
      where: { createdAt: { gte: since } },
      _count: true
    }),
    prisma.opsEvent.count({ where: { createdAt: { gte: since } } })
  ]);

  const toMap = (groups) => Object.fromEntries(groups.map(g => [g.status, g._count]));

  res.json({
    period: '24h',
    since: since.toISOString(),
    proposals: toMap(proposals),
    missions: toMap(missions),
    steps: toMap(steps),
    totalEvents: events,
    generatedAt: new Date().toISOString()
  });
});

export default router;
```

### 22.3 Heartbeat への監視統合

```javascript
// heartbeat.js 修正: checkOpsHealth を追加

import { checkOpsHealth } from '../../services/ops/opsMonitor.js';

router.get('/heartbeat', async (req, res) => {
  const start = Date.now();

  try {
    const results = {
      triggers: await evaluateTriggers(4000),
      reactions: await processReactionQueue(3000),
      insights: await promoteInsights(),
      stale: await recoverStaleSteps(),
      health: await checkOpsHealth()  // ★ 追加
    };

    // ★ アラートがあれば Slack に通知
    if (results.health.alert) {
      // OpenClaw exec で Slack 送信（VPS から呼ばれるため）
      logger.warn(`OPS ALERT: ${results.health.message}`);
    }

    const elapsed = Date.now() - start;
    logger.info(`Heartbeat completed in ${elapsed}ms`, results);

    res.json({ ok: true, elapsed, ...results });
  } catch (error) {
    logger.error('Heartbeat failed:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});
```

---

## 23. insightPromoter.js（shared-learnings → memU 昇格）

> **Gap P3 #3 解消**: 短期記憶（shared-learnings）から長期記憶（memU/WisdomPattern）への昇格
> **方針**: 一定回数以上引用された学びを memU テーブルに昇格。Heartbeat で5分毎に軽量チェック。

### 23.1 昇格基準

| 基準 | 閾値 | 理由 |
|------|------|------|
| 引用回数 | >= 3回 | 3回以上引用 = 汎用的な学び |
| 期間 | 7日以上経過 | 一時的なトレンドではない |
| 既存重複 | WisdomPattern に類似なし | 重複を避ける |

### 23.2 実装

```javascript
// apps/api/src/services/ops/insightPromoter.js

import { prisma } from '../../lib/prisma.js';
import { callLLM } from '../../lib/llm.js';
import { logger } from '../../lib/logger.js';

const CITATION_THRESHOLD = 3;
const AGE_THRESHOLD_DAYS = 7;

/**
 * shared-learnings から長期記憶への昇格
 * Heartbeat で5分毎に呼ばれるが、実際の昇格は条件を満たした時のみ
 *
 * @returns {{ promoted: number, checked: number }}
 */
export async function promoteInsights() {
  // shared-learnings は VPS の memory ファイルに保存されている
  // Railway API からは直接アクセスできないため、
  // analyze_engagement の output に含まれる learnings を OpsEvent から集計する

  const ageThreshold = new Date(Date.now() - AGE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000);

  // analyze_engagement 完了イベントから学びを集計
  const analysisEvents = await prisma.opsEvent.findMany({
    where: {
      kind: { in: ['engagement:high', 'engagement:low'] },
      createdAt: { gte: ageThreshold }
    },
    orderBy: { createdAt: 'desc' },
    take: 100
  });

  if (analysisEvents.length < CITATION_THRESHOLD) {
    return { promoted: 0, checked: analysisEvents.length };
  }

  // 高エンゲージメントパターンの抽出
  const highEngagementEvents = analysisEvents.filter(e => e.kind === 'engagement:high');
  if (highEngagementEvents.length < CITATION_THRESHOLD) {
    return { promoted: 0, checked: analysisEvents.length };
  }

  // LLMで共通パターンを抽出
  const patternAnalysis = await callLLM(`以下の高エンゲージメント分析結果から、共通する成功パターンを3つ抽出:
${highEngagementEvents.map(e => e.payload?.analysis || '').filter(Boolean).join('\n---\n')}

フォーマット:
1. [パターン名]: [説明]
2. [パターン名]: [説明]
3. [パターン名]: [説明]`);

  // WisdomPattern テーブルに昇格（既存スキーマ活用）
  const existingCount = await prisma.wisdomPattern.count();
  const pattern = await prisma.wisdomPattern.create({
    data: {
      content: patternAnalysis,
      source: 'ops_insight_promotion',
      tags: ['auto_promoted', 'engagement_pattern'],
      metadata: {
        basedOn: highEngagementEvents.length,
        promotedAt: new Date().toISOString()
      }
    }
  });

  logger.info(`Insight promoted to WisdomPattern: ${pattern.id} (based on ${highEngagementEvents.length} events)`);

  return { promoted: 1, checked: analysisEvents.length };
}
```

---

## 24. Staging → Production 移行手順

> **Gap P3 #9 解消**: Staging で検証後、Production に移行するステップバイステップ

### 24.1 移行チェックリスト

| # | ステップ | コマンド / アクション | 確認方法 |
|---|---------|---------------------|---------|
| 1 | Staging で全テスト PASS | `cd apps/api && npx vitest run` | 全テスト緑 |
| 2 | Staging で E2E 動作確認 | 手動: Proposal → Mission → Step → Complete の全フロー | Slack 通知 + DB 確認 |
| 3 | Production DB にマイグレーション SQL 適用 | `DATABASE_URL="$PROD_DB_URL" psql -f sql/20260208_add_ops_tables.sql` | `\dt ops_*` で7テーブル |
| 4 | Production DB に Seed データ投入 | `psql -f sql/20260208_seed_ops_policy.sql && psql -f sql/20260208_seed_ops_trigger_rules.sql` | `SELECT count(*) FROM ops_policy` = 9 |
| 5 | Prisma スキーマ同期 | `DATABASE_URL="$PROD_DB_URL" npx prisma db pull` | schema.prisma にopsテーブル反映 |
| 6 | dev → main マージ | `git checkout main && git merge dev` | CI 通過 |
| 7 | Railway Production 自動デプロイ | main push → Railway 自動ビルド | Railway ダッシュボードで確認 |
| 8 | Production ANICCA_AGENT_TOKEN 設定 | Railway Variables で設定 | `curl -H "Authorization: Bearer $TOKEN" $PROD_URL/api/ops/heartbeat` で 200 |
| 9 | VPS 環境変数を Production URL に変更 | `~/.env` の `API_BASE_URL` を `anicca-proxy-production.up.railway.app` に変更 | `ssh anicca@46.225.70.241 "grep API_BASE_URL ~/.env"` |
| 10 | VPS Gateway 再起動 | `systemctl --user restart openclaw-gateway` | `systemctl --user status openclaw-gateway` |
| 11 | Production Heartbeat 動作確認 | 5分待つ | `SELECT count(*) FROM ops_events WHERE created_at > now() - interval '10 min'` |
| 12 | Production 手動提案テスト | `curl -X POST .../api/ops/proposal` | 提案 → Mission → Step の全フロー完走 |

### 24.2 ロールバック手順

| 状況 | アクション |
|------|-----------|
| API エラー | Railway ダッシュボードから前回デプロイに Rollback |
| DB マイグレーション失敗 | `DROP TABLE IF EXISTS ops_reactions, ops_trigger_rules, ops_policy, ops_events, ops_mission_steps, ops_missions, ops_proposals CASCADE;` |
| VPS 設定ミス | `~/.env` を Staging URL に戻して Gateway 再起動 |

### 24.3 段階的ロールアウト

> **一気に全スキルを閉ループ化しない。段階的に移行する。**

| Phase | 対象 | 期間 | 成功基準 |
|-------|------|------|---------|
| Phase A | x-poster のみ | 1週間 | Mission 成功率 > 90%, ゼロ障害 |
| Phase B | + tiktok-poster | 1週間 | Mission 成功率 > 90% |
| Phase C | + trend-hunter, suffering-detector | 1週間 | Trigger 発火 + Reaction 連鎖の確認 |
| Phase D | + app-nudge-sender | 1週間 | 全スキル閉ループ化完了 |

### 24.4 各 Phase の切り替え方法

```sql
-- Phase A: x-poster のみ閉ループ対応
-- 他のスキルは既存の direct 実行を維持

-- Phase B への切り替え: tiktok_autopost を有効化
UPDATE ops_policy SET value = '{"enabled": true}' WHERE key = 'tiktok_autopost';

-- Phase D: 全スキル対応後、旧 Cron ジョブを無効化
-- schedule.yaml から旧スキル直接実行の行を削除
```

---

## 25. 更新されたファイル構成（Gap 解消後）

```
apps/api/
├── prisma/
│   └── schema.prisma                          # ← ops テーブル追加
├── sql/
│   ├── 20260208_add_ops_tables.sql            # マイグレーション
│   ├── 20260208_seed_ops_policy.sql           # Policy シード
│   └── 20260208_seed_ops_trigger_rules.sql    # Trigger Rule シード
├── vitest.config.js                            # ★ NEW: テスト設定
└── src/
    ├── test/
    │   └── setup.js                            # ★ NEW: Prisma モック
    ├── middleware/
    │   └── opsAuth.js                          # 認証ミドルウェア
    ├── routes/
    │   └── ops/
    │       ├── index.js                        # Proposal/Step ルーター
    │       ├── heartbeat.js                    # Heartbeat ルーター
    │       ├── approval.js                     # ★ NEW: Slack承認ルーター
    │       └── summary.js                      # ★ NEW: 日次サマリー
    └── services/
        └── ops/
            ├── proposalService.js              # 閉ループの核心
            ├── capGates.js                     # Cap Gate
            ├── policyService.js                # Policy CRUD + キャッシュ
            ├── eventEmitter.js                 # イベント発行 + Reaction接続
            ├── triggerEvaluator.js             # トリガー評価（delay_min修正済み）
            ├── reactionProcessor.js            # Reaction Matrix
            ├── staleRecovery.js                # 自己回復
            ├── insightPromoter.js              # ★ NEW: 学び昇格
            ├── approvalNotifier.js             # ★ NEW: Slack承認通知
            ├── approvalHandler.js              # ★ NEW: 承認/リジェクト処理
            ├── opsMonitor.js                   # ★ NEW: 監視・アラート
            ├── __tests__/
            │   ├── proposalService.test.js     # ★ NEW: T1-T4
            │   ├── capGates.test.js            # ★ NEW: T5-T7
            │   ├── policyService.test.js       # ★ NEW: T8-T9
            │   ├── triggerEvaluator.test.js    # ★ NEW: T10-T12
            │   ├── reactionProcessor.test.js   # ★ NEW: T13-T15
            │   └── staleRecovery.test.js       # ★ NEW: T16-T18
            └── stepExecutors/
                ├── registry.js                 # ★ NEW: Executor レジストリ
                ├── executeDraftContent.js       # ★ NEW
                ├── executeVerifyContent.js      # ★ NEW
                ├── executePostX.js             # ★ NEW
                ├── executePostTiktok.js         # ★ NEW
                ├── executeFetchMetrics.js       # ★ NEW
                ├── executeAnalyzeEngagement.js  # ★ NEW
                ├── executeDiagnose.js           # ★ NEW
                ├── executeDetectSuffering.js    # ★ NEW
                ├── executeDraftNudge.js         # ★ NEW
                ├── executeSendNudge.js          # ★ NEW
                └── executeEvaluateHook.js       # ★ NEW

VPS (~/.openclaw/workspace/skills/):
├── mission-worker/
│   └── SKILL.md                                # ★ NEW: 詳細版
├── x-poster/
│   └── SKILL.md                                # ★ 移行版
├── tiktok-poster/
│   └── SKILL.md                                # ★ 移行版
├── trend-hunter/
│   └── SKILL.md                                # ★ 移行版
├── suffering-detector/
│   └── SKILL.md                                # ★ 移行版
└── app-nudge-sender/
    └── SKILL.md                                # ★ 移行版
```

---

## 26. 更新されたテストマトリックス（Gap 解消後）

| # | テスト対象 | テスト名 | 種別 | カバー |
|---|-----------|---------|------|--------|
| T1 | Proposal Service | `test_createProposal_accepted` | Unit | OK |
| T2 | Proposal Service | `test_createProposal_rejected_capGate` | Unit | OK |
| T3 | Proposal Service | `test_createProposal_pending_noAutoApprove` | Unit | OK |
| T4 | Proposal Service | `test_createProposal_dailyLimit` | Unit | OK |
| T5 | Cap Gate | `test_postXGate_quotaReached` | Unit | OK |
| T6 | Cap Gate | `test_postXGate_disabled` | Unit | OK |
| T7 | Cap Gate | `test_sendNudgeGate_quotaReached` | Unit | OK |
| T8 | Policy Service | `test_getPolicy_cached` | Unit | OK |
| T9 | Policy Service | `test_setPolicy_invalidatesCache` | Unit | OK |
| T10 | Trigger Evaluator | `test_evaluateTriggers_fireOnMatch` | Unit | OK |
| T11 | Trigger Evaluator | `test_evaluateTriggers_cooldown` | Unit | OK |
| T12 | Trigger Evaluator | `test_evaluateTriggers_delayCondition` | Unit | OK |
| T13 | Reaction Processor | `test_processReactionQueue_createProposal` | Unit | OK |
| T14 | Reaction Matrix | `test_evaluateReactionMatrix_probability` | Unit | OK |
| T15 | Reaction Matrix | `test_evaluateReactionMatrix_cooldown` | Unit | OK |
| T16 | Stale Recovery | `test_recoverStaleSteps_markFailed` | Unit | OK |
| T17 | Stale Recovery | `test_maybeFinalizeMission_allSucceeded` | Unit | OK |
| T18 | Stale Recovery | `test_maybeFinalizeMission_anyFailed` | Unit | OK |
| T19 | Heartbeat API | `test_heartbeat_returns200` | Integration | OK |
| T20 | Proposal API | `test_proposal_validInput` | Integration | OK |
| T21 | Proposal API | `test_proposal_invalidInput` | Integration | OK |
| T22 | Step Next API | `test_stepNext_noSteps` | Integration | OK |
| T23 | Step Next API | `test_stepNext_claimStep` | Integration | OK |
| T24 | Step Complete API | `test_stepComplete_succeeded` | Integration | OK |
| T25 | Step Complete API | `test_stepComplete_missionFinalized` | Integration | OK |
| T26 | Auth | `test_opsAuth_rejectNoToken` | Unit | OK |
| T27 | Auth | `test_opsAuth_rejectBadToken` | Unit | OK |
| **T28** | **Step Data Pass** | `test_stepNext_injectsPreviousOutput` | **Unit** | **★ NEW** |
| **T29** | **Step Data Pass** | `test_stepNext_blocksPendingPrevStep` | **Unit** | **★ NEW** |
| **T30** | **Approval** | `test_approveProposal_createsMission` | **Unit** | **★ NEW** |
| **T31** | **Approval** | `test_rejectProposal_updatesStatus` | **Unit** | **★ NEW** |
| **T32** | **Approval API** | `test_slackApproval_approve` | **Integration** | **★ NEW** |
| **T33** | **Approval API** | `test_slackApproval_reject` | **Integration** | **★ NEW** |
| **T34** | **Executor** | `test_executeDraftContent_returnsContent` | **Unit** | **★ NEW** |
| **T35** | **Executor** | `test_executeVerifyContent_passes` | **Unit** | **★ NEW** |
| **T36** | **Executor** | `test_executeVerifyContent_failsAfterRetries` | **Unit** | **★ NEW** |
| **T37** | **Executor** | `test_executorRegistry_unknownKind` | **Unit** | **★ NEW** |
| **T38** | **emitEvent** | `test_emitEvent_triggersReactionMatrix` | **Unit** | **★ NEW** |
| **T39** | **Trigger** | `test_delayMin_tooEarly` | **Unit** | **★ NEW** |
| **T40** | **Trigger** | `test_delayMin_tooOld` | **Unit** | **★ NEW** |
| **T41** | **Monitor** | `test_checkOpsHealth_alertOnSpike` | **Unit** | **★ NEW** |
| **T42** | **Monitor** | `test_checkOpsHealth_noAlertBelowThreshold` | **Unit** | **★ NEW** |
| **T43** | **Summary API** | `test_dailySummary_returns24hData` | **Integration** | **★ NEW** |

---

## 27. 更新された実装チェックリスト（Gap 解消後）

| # | タスク | AC | 状態 |
|---|--------|---|------|
| 12.1 | マイグレーション SQL 適用 | `prisma db pull` で全opsテーブルがスキーマに反映 | ⬜ |
| 12.2 | Policy シードデータ投入 | `SELECT * FROM ops_policy` で9行 | ⬜ |
| 12.3 | Trigger Rule シードデータ投入 | `SELECT * FROM ops_trigger_rules` で4行 | ⬜ |
| 12.4 | proposalService.js 実装 | T1-T4 全PASS | ⬜ |
| 12.5 | capGates.js 実装 | T5-T7 全PASS | ⬜ |
| 12.6 | policyService.js 実装 | T8-T9 全PASS | ⬜ |
| 12.7 | eventEmitter.js 実装（Reaction接続込み） | T38 PASS | ⬜ |
| 12.8 | triggerEvaluator.js 実装（delay_min修正込み） | T10-T12, T39-T40 全PASS | ⬜ |
| 12.9 | reactionProcessor.js 実装 | T13-T15 全PASS | ⬜ |
| 12.10 | staleRecovery.js 実装 | T16-T18 全PASS | ⬜ |
| 12.11 | Heartbeat ルーター実装（監視込み） | T19, T41-T42 PASS | ⬜ |
| 12.12 | Proposal/Step ルーター実装（data pass込み） | T20-T29 全PASS | ⬜ |
| 12.13 | opsAuth ミドルウェア実装 | T26-T27 PASS | ⬜ |
| **12.14** | **Step Executor Registry + 12個の executor** | **T34-T37, T44-T53, T61 PASS** | ⬜ |
| **12.15** | **approvalNotifier + approvalHandler 実装** | **T30-T33 PASS** | ⬜ |
| **12.16** | **Approval API ルーター実装** | **T32-T33 PASS** | ⬜ |
| **12.17** | **insightPromoter.js 実装** | **手動テストで WisdomPattern に昇格確認** | ⬜ |
| **12.18** | **opsMonitor.js 実装** | **T41-T42 PASS** | ⬜ |
| **12.19** | **Summary API 実装** | **T43 PASS** | ⬜ |
| 12.20 | mission-worker SKILL.md 作成（詳細版） | `openclaw skills list` に表示 | ⬜ |
| 12.21 | 既存スキル移行（x-poster） | 提案経由で投稿成功 | ⬜ |
| 12.22 | schedule.yaml 更新 | `openclaw cron list` で新ジョブ表示 | ⬜ |
| 12.23 | Vitest + Prisma Mock セットアップ | `npx vitest run` で全テスト PASS | ⬜ |
| 12.24 | Staging デプロイ + E2Eテスト | 全フロー完走 | ⬜ |
| 12.25 | Production 段階的ロールアウト（Phase A: x-poster） | 1週間 Mission 成功率 > 90% | ⬜ |
