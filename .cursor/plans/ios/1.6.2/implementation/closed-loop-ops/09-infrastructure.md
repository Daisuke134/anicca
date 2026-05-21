# 09 — Infrastructure (監視 + insightPromoter + デプロイ)

> **元ファイル**: `../closed-loop-ops.md` Section 22-24
> **ナビ**: [← Event System](./08-event-trigger-system.md) | [README](./README.md) | [次: Test Matrix →](./10-test-matrix-checklist.md)

---

## 22. 監視・アラート

> **Gap P2 #10 解消**: 失敗スパイク検知 + 日次 Ops サマリー

### 22.1 失敗アラート（opsMonitor.js）

```javascript
// apps/api/src/services/ops/opsMonitor.js

import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

const FAILURE_THRESHOLD = 5;
const ALERT_COOLDOWN_MS = 60 * 60 * 1000;
let lastAlertAt = 0;

export async function checkOpsHealth() {
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);

  const failureCount = await prisma.opsMissionStep.count({
    where: { status: 'failed', completedAt: { gte: oneHourAgo } }
  });

  const pendingCount = await prisma.opsProposal.count({
    where: { status: 'pending', createdAt: { gte: oneHourAgo } }
  });

  const shouldAlert = failureCount >= FAILURE_THRESHOLD
    && (Date.now() - lastAlertAt > ALERT_COOLDOWN_MS);

  if (shouldAlert) {
    lastAlertAt = Date.now();
    const message = `Ops Alert: ${failureCount} step failures in the last hour. ${pendingCount} proposals pending approval.`;
    logger.warn(message);
    return { alert: true, failureCount, pendingCount, message };
  }

  return { alert: false, failureCount, pendingCount };
}
```

### 22.2 日次 Ops サマリー

```yaml
# schedule.yaml に追加
ops-daily-summary:
  cron: "0 6 * * *"  # 毎日06:00 JST
  session: isolated
  kind: agentTurn
  delivery:
    mode: "none"
  message: |
    GET /api/ops/summary/daily を叩いて #ops-summary に投稿
```

```javascript
// apps/api/src/routes/ops/summary.js
import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';

const router = Router();

router.get('/summary/daily', async (req, res) => {
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000);

  const [proposals, missions, steps, events] = await Promise.all([
    prisma.opsProposal.groupBy({ by: ['status'], where: { createdAt: { gte: since } }, _count: true }),
    prisma.opsMission.groupBy({ by: ['status'], where: { createdAt: { gte: since } }, _count: true }),
    prisma.opsMissionStep.groupBy({ by: ['status'], where: { createdAt: { gte: since } }, _count: true }),
    prisma.opsEvent.count({ where: { createdAt: { gte: since } } })
  ]);

  const toMap = (groups) => Object.fromEntries(groups.map(g => [g.status, g._count]));

  res.json({
    period: '24h', since: since.toISOString(),
    proposals: toMap(proposals), missions: toMap(missions),
    steps: toMap(steps), totalEvents: events,
    generatedAt: new Date().toISOString()
  });
});

export default router;
```

### 22.3 Heartbeat への監視統合

```javascript
// heartbeat.js に checkOpsHealth を追加
import { checkOpsHealth } from '../../services/ops/opsMonitor.js';

// heartbeat 内:
const results = {
  triggers: await evaluateTriggers(4000),
  reactions: await processReactionQueue(3000),
  insights: await promoteInsights(),
  stale: await recoverStaleSteps(),
  health: await checkOpsHealth()  // 追加
};
```

---

## 23. insightPromoter.js（shared-learnings → memU 昇格）

> **Gap P3 #3 解消**: 短期記憶→長期記憶への昇格

### 昇格基準

| 基準 | 閾値 | 理由 |
|------|------|------|
| 引用回数 | >= 3回 | 3回以上引用 = 汎用的な学び |
| 期間 | 7日以上経過 | 一時的なトレンドではない |
| 既存重複 | WisdomPattern に類似なし | 重複を避ける |

```javascript
// apps/api/src/services/ops/insightPromoter.js

import { prisma } from '../../lib/prisma.js';
import { callLLM } from '../../lib/llm.js';
import { logger } from '../../lib/logger.js';

const CITATION_THRESHOLD = 3;
const AGE_THRESHOLD_DAYS = 7;

export async function promoteInsights() {
  // H1修正: 前回昇格時刻を policy から取得（無限ループ防止）
  // 前回昇格後のイベントのみ対象にすることで、同じイベントを繰り返し処理しない
  const { getPolicy, setPolicy } = await import('./policyService.js');
  const lastPromotion = await getPolicy('last_insight_promotion');
  const since = lastPromotion?.promotedAt
    ? new Date(lastPromotion.promotedAt)
    : new Date(Date.now() - AGE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000);

  const analysisEvents = await prisma.opsEvent.findMany({
    where: { kind: { in: ['engagement:high', 'engagement:low'] }, createdAt: { gt: since } },
    orderBy: { createdAt: 'desc' }, take: 100
  });

  if (analysisEvents.length < CITATION_THRESHOLD) {
    return { promoted: 0, checked: analysisEvents.length };
  }

  const highEngagementEvents = analysisEvents.filter(e => e.kind === 'engagement:high');
  if (highEngagementEvents.length < CITATION_THRESHOLD) {
    return { promoted: 0, checked: analysisEvents.length };
  }

  const patternAnalysis = await callLLM(`以下の高エンゲージメント分析から共通パターンを3つ抽出:
${highEngagementEvents.map(e => e.payload?.analysis || '').filter(Boolean).join('\n---\n')}`);

  // H11-H12修正: WisdomPattern の実スキーマに合わせる
  // 実スキーマ: patternName(unique), description, targetUserTypes, effectiveTone,
  //   effectiveHookPattern, effectiveContentLength, appEvidence(JsonB), tiktokEvidence(JsonB),
  //   confidence(Decimal), verifiedAt
  // ※ content, source, tags, metadata フィールドは存在しない
  const patternName = `auto_insight_${Date.now()}`;
  const pattern = await prisma.wisdomPattern.create({
    data: {
      patternName,
      description: patternAnalysis,
      targetUserTypes: [],
      appEvidence: {
        basedOn: highEngagementEvents.length,
        promotedAt: new Date().toISOString(),
        source: 'ops_insight_promotion'
      },
      tiktokEvidence: {},
      confidence: 0.5
    }
  });

  // H1修正: 昇格時刻を更新（次回は以降のイベントのみ対象にする）
  await setPolicy('last_insight_promotion', { promotedAt: new Date().toISOString() });

  logger.info(`Insight promoted: ${pattern.id} (based on ${highEngagementEvents.length} events)`);
  return { promoted: 1, checked: analysisEvents.length };
}
```

---

## 24. Staging → Production 移行手順

### 移行チェックリスト

| # | ステップ | コマンド / アクション | 確認方法 |
|---|---------|---------------------|---------|
| 1 | Staging で全テスト PASS | `cd apps/api && npx vitest run` | 全テスト緑 |
| 2 | Staging で E2E 動作確認 | 手動: Proposal→Mission→Step→Complete | Slack通知 + DB確認 |
| 3 | Production DB マイグレーション | P1 #14: Railway Variables から `DATABASE_URL` をコピー → `DATABASE_URL="postgresql://..." psql -f sql/20260208_add_ops_tables.sql`（または Railway CLI: `railway run psql -f sql/20260208_add_ops_tables.sql`） | `\dt ops_*` で7テーブル |
| 4 | Production Seed データ | `psql -f sql/20260208_seed_ops_policy.sql && psql -f ...trigger_rules.sql` | ops_policy=9行 |
| 5 | Prisma スキーマ同期 | `npx prisma db pull` | schema.prisma にops反映 |
| 6 | dev → main マージ | `git checkout main && git merge dev` | CI通過 |
| 7 | Railway Production 自動デプロイ | main push | Railway ダッシュボード確認 |
| 8 | Production TOKEN 設定 | Railway Variables | Heartbeat で 200 |
| 9 | VPS Production URL設定 | `~/.env` の `API_BASE_URL` 変更 | grep で確認 |
| 10 | VPS Gateway再起動 | `systemctl --user restart openclaw-gateway` | status確認 |
| 11 | Heartbeat動作確認 | 5分待つ | ops_events にレコード |
| 12 | 手動提案テスト | `curl -X POST .../api/ops/proposal` | 全フロー完走 |

### ロールバック

| 状況 | アクション |
|------|-----------|
| API エラー | Railway ダッシュボード→前回デプロイに Rollback |
| DB マイグレーション失敗 | `DROP TABLE IF EXISTS ops_reactions, ops_trigger_rules, ops_policy, ops_events, ops_mission_steps, ops_missions, ops_proposals CASCADE;` |
| VPS 設定ミス | `~/.env` を Staging URL に戻して Gateway 再起動 |

### 段階的ロールアウト

| Phase | 対象 | 期間 | 成功基準 |
|-------|------|------|---------|
| Phase A | x-poster のみ | 1週間 | Mission成功率 > 90%, ゼロ障害 |
| Phase B | + tiktok-poster | 1週間 | Mission成功率 > 90% |
| Phase C | + trend-hunter, suffering-detector | 1週間 | Trigger発火 + Reaction連鎖確認 |
| Phase D | + app-nudge-sender | 1週間 | 全スキル閉ループ化完了 |

### Phase 切り替え方法

```sql
-- Phase B: tiktok_autopost 有効化
UPDATE ops_policy SET value = '{"enabled": true}' WHERE key = 'tiktok_autopost';

-- Phase D 完了後: 旧 Cron ジョブを schedule.yaml から削除
```
