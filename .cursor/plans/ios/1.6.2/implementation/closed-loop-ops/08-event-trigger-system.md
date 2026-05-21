# 08 — Event-Trigger System (delay_min修正 + Reaction接続)

> **元ファイル**: `../closed-loop-ops.md` Section 19-20
> **ナビ**: [← VPS Worker](./07-vps-worker-migration.md) | [README](./README.md) | [次: Infrastructure →](./09-infrastructure.md)

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
// P0 #25 解消: delay_min の値ごとの挙動を明示
// delay_min=undefined or null → デフォルト5分検索窓（即時トリガー）
// delay_min=0               → 明示的に0分 = 即時トリガー（デフォルト5分検索窓）
// delay_min=1440            → 1440×1.5=2160分=36時間検索窓（24時間後に発火）
const delayMin = rule.condition?.delay_min ?? 0;  // ?? を使用（|| だと 0 が falsy）
const searchWindowMs = delayMin > 0
  ? delayMin * 1.5 * 60 * 1000     // delay_min × 1.5（バッファ）
  : 5 * 60 * 1000;                   // デフォルト5分（delay_min=0 or 未設定）
const since = rule.lastFiredAt || new Date(Date.now() - searchWindowMs);
```

### 19.3 checkTriggerCondition の修正

```javascript
// 修正後: delay_min は「イベント発生からN分経過したか」をチェック
function checkTriggerCondition(condition, event) {
  // P0 #25 解消: delay_min の挙動を明確化
  // delay_min=undefined → チェックスキップ（即時発火）
  // delay_min=0         → チェックスキップ（明示的即時発火 — 0は「遅延なし」の意味）
  // delay_min=1440      → 1440分（24時間）経過後に発火、2880分（48時間）超は古すぎて拒否
  const delayMin = condition.delay_min ?? null;  // undefined/null → null
  if (delayMin != null && delayMin > 0) {
    const eventAgeMin = (Date.now() - event.createdAt.getTime()) / (1000 * 60);
    // N分未満なら「まだ早い」→ false
    if (eventAgeMin < delayMin) return false;
    // N分 × 2 以上なら「古すぎる」→ false（二重発火防止）
    if (eventAgeMin > delayMin * 2) return false;
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
 */
export async function emitEvent(source, kind, tags, payload = {}, missionId = null) {
  const event = await prisma.opsEvent.create({
    data: { source, kind, tags, payload, missionId }
  });

  // Reaction Matrix 自動評価（循環参照を避けるため動的 import）
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

### 20.2 接続後のデータフロー

```
Step完了 (post_x succeeded)
    │
    ▼
emitEvent('x-poster', 'tweet_posted', ['tweet', 'posted'], {...})
    │
    ├──→ ops_events に INSERT（イベント記録）
    │
    └──→ evaluateReactionMatrix(event)
              │
              ├──→ reaction_matrix パターンマッチ
              │     source='x-poster', tags=['tweet','posted'] → target='trend-hunter', type='analyze_engagement', p=0.3
              │
              ├──→ 確率判定 (Math.random() < 0.3)
              │
              ├──→ クールダウンチェック
              │
              └──→ ops_reactions に INSERT（リアクションキュー）
                        │
                        ▼
                  次回 Heartbeat で processReactionQueue() が処理
                        │
                        ▼
                  createProposalAndMaybeAutoApprove({ skillName: 'trend-hunter', ... })
```
