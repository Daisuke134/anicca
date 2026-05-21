# 04 — API Routes + Kill Switch + Auth

> **元ファイル**: `../closed-loop-ops.md` Section 7, 9, 10
> **ナビ**: [← API Services](./03-api-services.md) | [README](./README.md) | [次: Step Executors →](./05-step-executors.md)

---

## 7. API ルーター統合

> **⚠️ H6修正: step/next と step/complete の正規版（FOR UPDATE SKIP LOCKED + data passing + event自動発行）は `05-step-executors.md` §16.2-16.3 を参照。実装時は 05 版を使うこと。この版は構造参考のみ。**

```javascript
// apps/api/src/routes/ops/index.js
// ★ step/next, step/complete の正規版は 05-step-executors.md §16.2-16.3

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
  error: z.string().optional(),
  events: z.array(z.object({
    kind: z.string(),
    tags: z.array(z.string()).optional(),
    payload: z.record(z.unknown()).optional()
  })).optional()  // ★ Executor が返す events を body.events として受け取る
});

// P1 #6 解消: step_kind 別の output 必須フィールド（バリデーションは warn ログのみ、reject しない）
// 理由: VPS Worker の出力を厳密に拒否すると、バージョン不一致時にステップが永久に失敗する
// 実装: output 保存後にフィールド不足を warn ログ出力（監視用）
const STEP_OUTPUT_HINTS = {
  draft_content:       ['content', 'hookId', 'platform'],
  verify_content:      ['content', 'verificationScore', 'passed'],
  post_x:              ['postId', 'platform'],
  post_tiktok:         ['postId', 'platform'],
  fetch_metrics:       ['metrics', 'postId', 'platform'],
  analyze_engagement:  ['analysis', 'isHighEngagement', 'engagementRate'],
  detect_suffering:    [],  // VPS パススルー（動的output）
  diagnose:            ['diagnosis'],
  draft_nudge:         ['nudgeContent'],
  send_nudge:          ['sent'],
  evaluate_hook:       ['shouldPost'],
  run_trend_scan:      ['savedCount', 'sources'],  // trend-hunter フルパイプライン
};

router.patch('/step/:id/complete', async (req, res) => {
  const { id } = req.params;
  const parsed = StepCompleteSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { status, output, error, events } = parsed.data;

  // H14修正: ステータスガード — running 以外のステップを完了させない
  // 二重完了や、queued→complete（runningスキップ）を防止
  const current = await prisma.opsMissionStep.findUnique({
    where: { id },
    select: { status: true, missionId: true }
  });
  if (!current || current.status !== 'running') {
    return res.status(409).json({
      error: `Step ${id} is not in 'running' state (current: ${current?.status || 'not found'})`
    });
  }

  const step = await prisma.opsMissionStep.update({
    where: { id },
    data: {
      status,
      output: output || {},
      lastError: error || null,
      completedAt: new Date()
    }
  });

  // body.events がある場合、各イベントを emitEvent で発行
  // emitEvent 契約: emitEvent(source, kind, tags, payload, missionId)
  if (events && events.length > 0) {
    // source 解決: step → mission → proposal.skillName
    const mission = await prisma.opsMission.findUnique({
      where: { id: step.missionId },
      include: { proposal: { select: { skillName: true } } }
    });
    const source = mission?.proposal?.skillName || 'unknown';

    for (const evt of events) {
      await emitEvent(
        source,
        evt.kind,
        evt.tags || [],
        { ...evt.payload, stepId: id },
        step.missionId
      );
    }
  }

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
import approvalRouter from './ops/approval.js';
import summaryRouter from './ops/summary.js';
import eventsRouter from './ops/events.js';
import agentHooksRouter from './agent/hooks.js';
import { opsAuth } from '../middleware/opsAuth.js';

// 既存のルーター（変更なし）
app.use('/api/mobile', mobileRouter);
// ...

// 新規: Ops API（全エンドポイントに opsAuth 適用）
app.use('/api/ops', opsAuth, opsRouter);
// H8修正: approval エンドポイントにも opsAuth を適用
// Slack Interactivity URL → VPS → Railway 転送パスで Bearer Token が付与される前提
app.use('/api/ops', opsAuth, approvalRouter);
app.use('/api/ops', opsAuth, summaryRouter);
app.use('/api/ops', opsAuth, eventsRouter);

// Agent API（VPS → Railway hook管理）
app.use('/api/agent', opsAuth, agentHooksRouter);
```

---

## 7.1 VPS→Railway イベント受信 API（BLOCKING #1 解消）

> **trend-hunter (VPS) が `emitEvent()` を HTTP 経由で呼ぶためのエンドポイント**

```javascript
// apps/api/src/routes/ops/events.js

import { Router } from 'express';
import { z } from 'zod';
import { emitEvent } from '../../services/ops/eventEmitter.js';
import { logger } from '../../lib/logger.js';

const router = Router();

const EventInputSchema = z.object({
  source: z.string().max(50),
  kind: z.string().max(100),
  tags: z.array(z.string().max(50)).max(10),
  payload: z.record(z.unknown()).default({})
});

/**
 * POST /api/ops/events
 * VPS (trend-hunter等) から Railway にイベントを送信
 * 内部の emitEvent() をHTTP経由で呼び出すラッパー
 */
router.post('/events', async (req, res) => {
  const parsed = EventInputSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { source, kind, tags, payload } = parsed.data;

  try {
    const event = await emitEvent(source, kind, tags, payload);
    res.status(201).json({ id: event.id });
  } catch (err) {
    logger.error('Event creation failed:', err);
    res.status(500).json({ error: err.message });
  }
});

export default router;
```

---

## 7.2 Agent Hook管理 API（BLOCKING #2 解消）

> **trend-hunter (VPS) が hook候補を Railway DB に保存/取得するためのエンドポイント**
> **注**: このエンドポイントは `hook_candidates` テーブル（02-data-layer.md）に対するCRUD。

```javascript
// apps/api/src/routes/agent/hooks.js

import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

const router = Router();

/**
 * GET /api/agent/hooks
 * 全hook候補を取得（trend-hunter が重複チェック + Thompson Sampling で使用）
 */
router.get('/hooks', async (req, res) => {
  const hooks = await prisma.hookCandidate.findMany({
    orderBy: { createdAt: 'desc' },
    take: 500  // 上限: hook数が1000超になったらページネーション追加
  });

  res.json({
    hooks: hooks.map(h => ({
      id: h.id,
      text: h.text,
      targetProblemTypes: h.targetProblemTypes,
      source: h.source,
      platform: h.platform,
      xSampleSize: h.xSampleSize,
      xEngagementRate: h.xEngagementRate,
      tiktokSampleSize: h.tiktokSampleSize,
      tiktokLikeRate: h.tiktokLikeRate,
      createdAt: h.createdAt
    }))
  });
});

const HookSaveSchema = z.object({
  text: z.string().min(1).max(500),
  targetProblemTypes: z.array(z.string()).min(1),
  source: z.string().max(50).default('trend-hunter'),
  platform: z.enum(['x', 'tiktok', 'both']).default('both'),
  contentType: z.enum(['empathy', 'solution']),
  idempotencyKey: z.string().max(128).optional(),
  metadata: z.record(z.unknown()).optional()
});

/**
 * POST /api/agent/hooks
 * 新しいhook候補を保存（trend-hunter Step 4 で使用）
 *
 * 重複チェック: text が既存hookと Jaccard bi-gram >= 0.7 の場合は
 * VPS側（trend-hunter）で事前にフィルタ済みの前提。
 * サーバー側では text 完全一致のみチェック。
 */
router.post('/hooks', async (req, res) => {
  const parsed = HookSaveSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { text, targetProblemTypes, source, platform, contentType, idempotencyKey, metadata } = parsed.data;

  // 冪等キーによる重複チェック（DLQリトライ時の二重保存防止）
  if (idempotencyKey) {
    const byKey = await prisma.hookCandidate.findFirst({
      where: { idempotencyKey },
      select: { id: true, text: true, createdAt: true }
    });
    if (byKey) {
      return res.status(200).json({ status: 'duplicate', existingId: byKey.id });
    }
  }

  // 完全一致の重複チェック
  const existing = await prisma.hookCandidate.findFirst({
    where: { text },
    select: { id: true }
  });

  if (existing) {
    return res.status(200).json({ status: 'duplicate', existingId: existing.id });
  }

  const hook = await prisma.hookCandidate.create({
    data: {
      text,
      targetProblemTypes,
      source,
      platform,
      contentType,
      ...(idempotencyKey ? { idempotencyKey } : {}),
      metadata: metadata || {}
    }
  });

  logger.info(`Hook candidate saved: ${hook.id} (${contentType}, ${targetProblemTypes.join(',')})`);
  res.status(201).json({ id: hook.id, text: hook.text, createdAt: hook.createdAt });
});

export default router;
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
| `POST /api/ops/events` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS trend-hunter からのイベント送信 |
| `GET /api/agent/hooks` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS trend-hunter からの hook取得 |
| `POST /api/agent/hooks` | Bearer Token (`ANICCA_AGENT_TOKEN`) | VPS trend-hunter からの hook保存 |

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
