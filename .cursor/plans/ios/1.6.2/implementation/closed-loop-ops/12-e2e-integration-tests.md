# 12 — E2E統合テスト マトリックス

> **ステータス**: NEW（スキル間ループの統合検証）
> **ナビ**: [← README](./README.md) | [エージェント評価 →](./11-agent-evaluation.md)

---

## 目的

T1-T67 は個別コンポーネントの正当性を検証する（Unit/Integration）。
このマトリックスは **スキル間の閉ループが正しく循環するか** を検証する。

---

## テスト境界モデル（5段階）

```
B1 ──→ B2 ──→ B3 ──→ B4 ──→ B5
単体    DB経由   イベント  トリガー  全ループ
        連鎖    記録     評価     循環
```

| 境界 | 範囲 | テスト方法 | CI実行 | 実行時間 |
|------|------|-----------|--------|---------|
| **B1** | 単一サービスの入出力 | Vitest + Prisma Mock | 毎回 | < 10秒 |
| **B2** | Proposal → Mission → Steps のDB連鎖 | Vitest + 実DB (test schema) | 毎回 | < 30秒 |
| **B3** | Step完了 → Event記録 → Reaction Queue投入 | Vitest + 実DB | 毎回 | < 30秒 |
| **B4** | Event → Trigger評価 → 新Proposal生成 | Vitest + 実DB + freezegun | 日次 | < 1分 |
| **B5** | 全ループ（Cron → Proposal → Mission → Steps → Event → Trigger → 新Proposal） | Staging E2E (curl) | 週次/リリース前 | < 5分 |

---

## B2: DB連鎖テスト

| # | テスト名 | シナリオ | 期待結果 |
|---|---------|---------|---------|
| I1 | `test_proposal_to_mission_chain` | Proposal作成(auto-approve) → Mission自動生成 | Mission.proposalId = Proposal.id, Steps が正しい順序で作成 |
| I2 | `test_mission_steps_sequential` | Step 0 を succeeded → Step 1 が next で取得可能 | Step 1 の input に Step 0 の output が注入 |
| I3 | `test_mission_finalization_success` | 全Steps succeeded | Mission.status = 'succeeded', completedAt 設定 |
| I4 | `test_mission_finalization_failure` | Step 1 が failed | Mission.status = 'failed', 残りSteps はそのまま |
| I5 | `test_cap_gate_prevents_mission` | X日次クォータ到達後にProposal | Proposal.status = 'rejected', Mission未作成 |

---

## B3: イベント連鎖テスト

| # | テスト名 | シナリオ | 期待結果 |
|---|---------|---------|---------|
| I6 | `test_step_complete_emits_event` | post_x Step を succeeded + body.events あり | ops_events に tweet_posted イベント記録 |
| I7 | `test_event_triggers_reaction` | tweet_posted イベント発行 | ops_reactions に analyze_engagement リアクション追加（probability依存） |
| I8 | `test_suffering_detected_emits_event` | detect_suffering Step を succeeded + output.detections (severity >= 0.6) | ops_events に suffering_detected イベント記録 |
| I9 | `test_mission_failed_emits_event` | Mission 全体が failed | ops_events に mission:failed イベント記録 |
| I10 | `test_reaction_cooldown` | 同一 target+type のリアクションがクールダウン内 | リアクション追加されない |

---

## B4: トリガー評価テスト

| # | テスト名 | シナリオ | 期待結果 |
|---|---------|---------|---------|
| I11 | `test_trigger_fire_on_event_match` | tweet_posted イベント (24h前) + engagement_analysis_24h ルール | 新Proposal (fetch_metrics + analyze_engagement) 生成 |
| I12 | `test_trigger_delay_min_too_early` | tweet_posted イベント (12h前) + delay_min=1440 | トリガー発火せず |
| I13 | `test_trigger_delay_min_too_old` | tweet_posted イベント (72h前) + delay_min=1440 | トリガー発火せず（二重発火防止） |
| I14 | `test_trigger_cooldown_respected` | ルール lastFiredAt = 5分前, cooldownMin=60 | トリガー発火せず |
| I15 | `test_suffering_trigger_nudge` | suffering_detected イベント (severity=0.8) | 新Proposal (draft_nudge + send_nudge) 生成 |
| I16 | `test_suffering_trigger_min_severity` | suffering_detected イベント (severity=0.3) | トリガー発火せず（min_severity=0.6 未満） |

### 時間依存テスト用: freezegun パターン

```javascript
import { vi } from 'vitest';

// delay_min テスト: 「24時間後」をシミュレート
it('should fire trigger after delay_min', async () => {
  // Step 1: イベントを「24時間前」に作成
  const eventTime = new Date(Date.now() - 24 * 60 * 60 * 1000);
  await prisma.opsEvent.create({
    data: { kind: 'tweet_posted', source: 'x-poster', createdAt: eventTime, tags: ['tweet', 'posted'] }
  });

  // Step 2: 「今」evaluateTriggers を実行
  const result = await evaluateTriggers(4000);

  // Step 3: 発火を確認
  expect(result.fired).toBe(1);
});
```

---

## B5: 全ループ E2E テスト（Staging環境）

| # | テスト名 | シナリオ | 確認手順 | 期待結果 |
|---|---------|---------|---------|---------|
| I17 | `e2e_x_poster_full_loop` | Cron → x-poster Proposal → Mission → draft→verify→post_x (pending for approval) | 1. POST /api/ops/proposal (x-poster) 2. GET /api/ops/step/next 3. 各step実行+complete 4. Event確認 | 全Steps完了 + tweet_posted イベント |
| I18 | `e2e_trigger_chain` | tweet_posted (24h前) → Heartbeat → fetch_metrics Proposal → 実行 → analyze_engagement | 1. DB にイベント挿入(24h前) 2. GET /api/ops/heartbeat 3. 新Proposal確認 | Trigger発火 + 新Mission作成 |
| I19 | `e2e_reaction_chain` | suffering_detected → Reaction Queue → draft_nudge + send_nudge Proposal | 1. suffering_detected イベント挿入 2. Heartbeat 3. Reaction処理確認 | Nudge Proposal 作成 |
| I20 | `e2e_stale_recovery` | Step を running のまま35分放置 → Heartbeat | 1. Step を running + reservedAt=35分前 に設定 2. Heartbeat | Step が failed に回復 |
| I21 | `e2e_approval_flow` | post_x 含む Proposal → pending → Slack承認 → Mission開始 | 1. POST Proposal (post_x含む) 2. POST /api/ops/approval (approve) | Mission作成 + Steps queued |
| I22 | `e2e_trend_hunter_loop` | Cron → trend-hunter Proposal → run_trend_scan Step → hook_saved + scan_completed イベント → evaluate_hook Reaction | 1. POST /api/ops/proposal (trend-hunter, run_trend_scan) 2. Step実行+complete (body.events=[hook_saved, scan_completed]) 3. Heartbeat で Reaction 処理確認 | hook_saved/scan_completed イベント記録 + evaluate_hook Reaction 生成 |

---

## CI/CD 実行戦略

| テスト種別 | 境界 | 実行タイミング | 実行環境 | 失敗時 |
|-----------|------|-------------|---------|--------|
| Unit (T1-T67) | B1 | PR push / merge | GitHub Actions | PR ブロック |
| DB連鎖 (I1-I5) | B2 | PR push / merge | GitHub Actions + test DB | PR ブロック |
| イベント連鎖 (I6-I10) | B3 | PR push / merge | GitHub Actions + test DB | PR ブロック |
| トリガー評価 (I11-I16) | B4 | 日次 nightly | GitHub Actions + test DB | Slack通知 |
| 全ループ E2E (I17-I22) | B5 | リリース前 / 週次 | Staging環境 (Railway) | リリースブロック |

### GitHub Actions 設定例

```yaml
# .github/workflows/ops-tests.yml
name: Ops Tests

on:
  push:
    paths: ['apps/api/src/services/ops/**', 'apps/api/src/routes/ops/**']

jobs:
  unit-and-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd apps/api && npm ci
      - run: cd apps/api && npx vitest run  # B1-B3

  trigger-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # nightly only
    steps:
      - run: cd apps/api && npx vitest run --reporter=verbose src/services/ops/__tests__/trigger*.test.js  # B4
```

---

## テスト対 Section マッピング

| テスト | 対応するドキュメント |
|--------|-------------------|
| I1-I5 (DB連鎖) | `03-api-services.md` (Proposal Service) |
| I6-I10 (イベント) | `08-event-trigger-system.md` (emitEvent→Reaction) |
| I11-I16 (トリガー) | `08-event-trigger-system.md` (delay_min修正) |
| I17-I21 (全ループ) | 全ファイル横断 |
