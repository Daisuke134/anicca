# 03 — API コアサービス群

> **元ファイル**: `../closed-loop-ops.md` Section 6
> **ナビ**: [← Data Layer](./02-data-layer.md) | [README](./README.md) | [次: API Routes →](./04-api-routes-security.md)

---

## 6. API 実装（Railway API）

### 6.1 Proposal Service（閉ループの核心）

> **VoxYZ Pitfall 2 修正**: 全ての提案作成がこの1つの関数を通る

```javascript
// apps/api/src/services/ops/proposalService.js

import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';
import { checkCapGate } from './capGateService.js';
import { getPolicy } from './policyService.js';
import { emitEvent } from './eventEmitter.js';

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
  // B5修正: payload に steps 情報も保存（承認時に approvalHandler が payload.steps から復元するため）
  const proposal = await prisma.opsProposal.create({
    data: {
      skillName,
      source,
      status: 'pending',
      title,
      payload: { ...payload, steps }  // ★ steps を payload に含める
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
  // H10修正: Slack 承認通知を送信（06-slack-approval.md 参照）
  try {
    const { sendApprovalNotification } = await import('./approvalNotifier.js');
    await sendApprovalNotification(proposal);
  } catch (err) {
    logger.warn(`Failed to send approval notification: ${err.message}`);
    // 通知失敗は提案作成自体を止めない
  }

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

> **⚠️ H4修正: このファイルの eventEmitter は基本版。正規版（Reaction Matrix 接続込み）は `08-event-trigger-system.md` §20.1 を参照。実装時は 08 の版を使うこと。**

```javascript
// apps/api/src/services/ops/eventEmitter.js
// ⚠️ 警告: この版は構造参考のみ — 実装禁止
// ⚠️ 正規版: 08-event-trigger-system.md §20.1（evaluateReactionMatrix 接続済み）
// ⚠️ この版との違い: 正規版は emitEvent 後に evaluateReactionMatrix() を自動呼び出しする
// ⚠️ この版を実装すると Reaction が永久に発火しないサイレント不具合になる

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

> **VPS の crontab から5分毎に呼ばれる**: `*/5 * * * * curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" ${API_BASE_URL}/api/ops/heartbeat`

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

> **⚠️ H5修正: checkTriggerCondition の正規版（delay_min ×2 上限 + 検索窓拡大）は `08-event-trigger-system.md` §19 を参照。実装時は 08 版を使うこと。**

```javascript
// apps/api/src/services/ops/triggerEvaluator.js
// ⚠️ 警告: この版は構造参考のみ — 実装禁止
// ⚠️ 正規版: 08-event-trigger-system.md §19.3（delay_min ?? 修正済み + since 計算が異なる）
// ⚠️ この版との違い: since 計算が5分固定窓、正規版は delay_min * 1.5 の動的窓

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

      // P0 #22 解消: トリガー発火 + lastFiredAt更新をトランザクションで保護
      // 理由: 発火後にクラッシュすると lastFiredAt が更新されず、次の Heartbeat で重複発火する
      // lastFiredAt を先に更新（楽観的ロック）→ 提案失敗時はロールバック
      const template = rule.proposalTemplate;
      try {
        await prisma.$transaction(async (tx) => {
          // 1. lastFiredAt を先に更新（次の Heartbeat での重複防止）
          await tx.opsTriggerRule.update({
            where: { id: rule.id },
            data: { lastFiredAt: new Date() }
          });

          // 2. 提案生成（tx 外 — createProposal は独自の tx を持つため）
        });

        const result = await createProposalAndMaybeAutoApprove({
          skillName: template.skill_name,
          source: 'trigger',
          title: template.title,
          payload: { triggeredBy: rule.name, eventId: matchingEvents[0].id },
          steps: template.steps.map(s => ({ kind: s.kind, order: s.order }))
        });

        fired++;
        logger.info(`Trigger fired: ${rule.name} → proposal ${result.proposalId}`);
      } catch (err) {
        // P0 #22: 提案生成失敗時は lastFiredAt はそのまま（次回リトライ可能）
        // lastFiredAt 更新が先なので、失敗時はクールダウン期間後に再試行される
        logger.warn(`Trigger ${rule.name} failed:`, err.message);
      }
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
  // P0 #24 解消: ステップ状態読み取り → ミッション更新をトランザクションで保護
  // 理由: 2つのステップが同時に完了すると、一方が「まだ未完了あり」と判定してしまう
  return prisma.$transaction(async (tx) => {
    const steps = await tx.opsMissionStep.findMany({
      where: { missionId },
      select: { status: true }
    });

    const allDone = steps.every(s => s.status === 'succeeded' || s.status === 'failed');
    if (!allDone) return null;

    const anyFailed = steps.some(s => s.status === 'failed');
    const finalStatus = anyFailed ? 'failed' : 'succeeded';

    await tx.opsMission.update({
      where: { id: missionId },
      data: { status: finalStatus, completedAt: new Date() }
    });

    // イベント記録（tx 外 — emitEvent は独自の tx/Reaction 評価を持つため）
    const mission = await tx.opsMission.findUnique({
      where: { id: missionId },
      include: { proposal: true }
    });

    // tx 完了後にイベント発行（副作用を分離）
    setImmediate(async () => {
      const { emitEvent } = await import('./eventEmitter.js');
      await emitEvent(
        mission.proposal.skillName,
        `mission:${finalStatus}`,
        ['mission', finalStatus],
        { missionId, proposalId: mission.proposalId }
      );
    });

    return finalStatus;
  });
}
```
