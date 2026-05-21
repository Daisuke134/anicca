# 10 — テストマトリックス + チェックリスト + 境界

> **元ファイル**: `../closed-loop-ops.md` Section 11-14, 21, 25-27
> **ナビ**: [← README](./README.md) | [エージェント評価 →](./11-agent-evaluation.md) | [E2E統合 →](./12-e2e-integration-tests.md)

---

## テストマトリックス（T1-T67）

> **TDD対応**: 各テストに入力/前提と期待結果を明記。テストファースト時にassert対象が一意に決まる。

| # | テスト対象 | テスト名 | 種別 | 入力/前提 | 期待結果 |
|---|-----------|---------|------|----------|---------|
| T1 | Proposal Service | `test_createProposal_accepted` | Unit | skillName='x-poster', steps=[draft_content, verify_content, post_x] | status='accepted', missionId != null |
| T2 | Proposal Service | `test_createProposal_rejected_capGate` | Unit | skillName='x-poster', 当日X投稿3件済み | status='rejected', rejectReason='x_daily_quota' |
| T3 | Proposal Service | `test_createProposal_pending_noAutoApprove` | Unit | steps に post_x 含む（Kill Switch対象） | status='pending', missionId == null |
| T4 | Proposal Service | `test_createProposal_dailyLimit` | Unit | 当日提案100件済み | status='rejected', rejectReason='daily_proposal_limit' |
| T5 | Cap Gate | `test_postXGate_quotaReached` | Unit | policy.x_daily_quota.limit=3, 当日X投稿3件 | return false |
| T6 | Cap Gate | `test_postXGate_disabled` | Unit | policy.x_autopost.enabled=false | return false |
| T7 | Cap Gate | `test_sendNudgeGate_quotaReached` | Unit | policy.nudge_daily_quota.limit=10, 当日Nudge10件 | return false |
| T8 | Policy Service | `test_getPolicy_cached` | Unit | getPolicy('auto_approve') を2回呼ぶ | DB query 1回のみ（2回目はキャッシュ） |
| T9 | Policy Service | `test_setPolicy_invalidatesCache` | Unit | getPolicy → setPolicy → getPolicy | 3回目は新しい値を返す |
| T10 | Trigger Evaluator | `test_evaluateTriggers_fireOnMatch` | Unit | trigger rule event_kind='tweet_posted', 合致イベントあり | createProposalAndMaybeAutoApprove が呼ばれる |
| T11 | Trigger Evaluator | `test_evaluateTriggers_cooldown` | Unit | lastFiredAt=1分前, cooldownMin=60 | スキップ（提案生成なし） |
| T12 | Trigger Evaluator | `test_evaluateTriggers_delayCondition` | Unit | delay_min=1440, イベント発生10分前 | スキップ（delay未到達） |
| T13 | Reaction Processor | `test_processReactionQueue_createProposal` | Unit | status='pending' のReactionレコード1件 | createProposal呼出 + status='processed' |
| T14 | Reaction Matrix | `test_evaluateReactionMatrix_probability` | Unit | probability=0.3, Math.random=0.2 | Reaction生成される |
| T15 | Reaction Matrix | `test_evaluateReactionMatrix_cooldown` | Unit | cooldown=120, 前回発火60分前 | Reaction生成されない |
| T16 | Stale Recovery | `test_recoverStaleSteps_markFailed` | Unit | step.reservedAt=35分前, threshold=30 | status='failed', lastError含む |
| T17 | Stale Recovery | `test_maybeFinalizeMission_allSucceeded` | Unit | 全steps.status='succeeded' | mission.status='succeeded' |
| T18 | Stale Recovery | `test_maybeFinalizeMission_anyFailed` | Unit | 1つのstep.status='failed' | mission.status='failed' + mission:failed イベント |
| T19 | Heartbeat API | `test_heartbeat_returns200` | Integration | GET /api/ops/heartbeat, 有効token | 200 + { evaluated, promoted, recovered } |
| T20 | Proposal API | `test_proposal_validInput` | Integration | POST /api/ops/proposal, 正常JSON | 200/201 + proposalId |
| T21 | Proposal API | `test_proposal_invalidInput` | Integration | POST /api/ops/proposal, skillName欠落 | 400 + Zodエラー |
| T22 | Step Next API | `test_stepNext_noSteps` | Integration | GET /api/ops/step/next, queuedステップなし | 200 + null |
| T23 | Step Next API | `test_stepNext_claimStep` | Integration | GET /api/ops/step/next, queuedステップ1件 | 200 + step + status='running' |
| T24 | Step Complete API | `test_stepComplete_succeeded` | Integration | PATCH /step/:id/complete, status='succeeded' | 200 + output保存 |
| T25 | Step Complete API | `test_stepComplete_missionFinalized` | Integration | 最終step完了報告 | mission.status='succeeded' |
| T26 | Auth | `test_opsAuth_rejectNoToken` | Unit | Authorization header なし | 401 |
| T27 | Auth | `test_opsAuth_rejectBadToken` | Unit | Authorization: Bearer invalid | 401 |
| T28 | Step Data Pass | `test_stepNext_injectsPreviousOutput` | Unit | step_order=1, 前step.output={content:'x'} | input に content='x' が含まれる |
| T29 | Step Data Pass | `test_stepNext_blocksPendingPrevStep` | Unit | step_order=1, 前step.status='running' | null（ブロック） |
| T30 | Approval | `test_approveProposal_createsMission` | Unit | proposal.status='pending', approve=true | mission作成 + proposal.status='accepted' |
| T31 | Approval | `test_rejectProposal_updatesStatus` | Unit | proposal.status='pending', approve=false | proposal.status='rejected' |
| T32 | Approval API | `test_slackApproval_approve` | Integration | POST /api/ops/approval action='approve' | proposal accepted + mission created |
| T33 | Approval API | `test_slackApproval_reject` | Integration | POST /api/ops/approval action='reject' | proposal rejected |
| T34 | Executor | `test_executeDraftContent_returnsContent` | Unit | mock callLLM='生成文', mock hookSelector | output.content != null, output.hookId != null |
| T35 | Executor | `test_executeVerifyContent_passes` | Unit | mock verifier score=4 | output.passed=true, output.verificationScore=4 |
| T36 | Executor | `test_executeVerifyContent_failsAfterRetries` | Unit | mock verifier score=1 (3回) | output.passed=false, attempts=3 |
| T37 | Executor | `test_executorRegistry_unknownKind` | Unit | getExecutor('nonexistent') | Error thrown: 'Unknown step_kind' |
| T38 | emitEvent | `test_emitEvent_triggersReactionMatrix` | Unit | emit 'tweet_posted', matrix has matching pattern | Reaction レコード作成 |
| T39 | Trigger | `test_delayMin_tooEarly` | Unit | delay_min=1440, イベント発生10分前 | trigger発火しない |
| T40 | Trigger | `test_delayMin_tooOld` | Unit | delay_min=1440, イベント発生3000分前 | trigger発火しない（window超過） |
| T41 | Monitor | `test_checkOpsHealth_alertOnSpike` | Unit | 1時間内に failed step 6件（閾値5） | Slack通知呼出 |
| T42 | Monitor | `test_checkOpsHealth_noAlertBelowThreshold` | Unit | 1時間内に failed step 3件（閾値5） | Slack通知なし |
| T43 | Summary API | `test_dailySummary_returns24hData` | Integration | GET /api/ops/summary/daily | 200 + proposalCount, missionCount, successRate |
| T44 | Executor: post_x | `test_executePostX_createsXPost` | Unit | mock Blotato API成功 | output.postId != null, events=[tweet_posted] |
| T45 | Executor: post_tiktok | `test_executePostTiktok_createsTiktokPost` | Unit | mock Blotato API成功 | output.postId != null, events=[tiktok_posted] |
| T46 | Executor: fetch_metrics | `test_executeFetchMetrics_xBigIntConversion` | Unit | mock X API返却(BigInt tweet_id) | output.metrics.impressions=Number |
| T47 | Executor: fetch_metrics | `test_executeFetchMetrics_tiktokMetrics` | Unit | mock Apify返却 | output.metrics.engagementRate=Number |
| T48 | Executor: analyze_engagement | `test_executeAnalyzeEngagement_highThreshold` | Unit | metrics.engagementRate=0.06 | output.isHighEngagement=true, hookスコア更新 |
| T49 | Executor: diagnose | `test_executeDiagnose_extractsFailedSteps` | Unit | mission with 1 failed step | output.failedSteps.length=1, output.diagnosis != null |
| T50 | Executor: detect_suffering | `test_executeDetectSuffering_passthrough` | Unit | mock web_search結果 | output.detections is Array |
| T51 | Executor: draft_nudge | `test_executeDraftNudge_topSeveritySelection` | Unit | detections=[{severity:0.8},{severity:0.6}] | 最高severity(0.8)を選択, content.length<=50 |
| T52 | Executor: send_nudge | `test_executeSendNudge_skipsWhenNoContent` | Unit | input.nudgeContent=null | output.skipped=true, events=[] |
| T53 | Executor: evaluate_hook | `test_executeEvaluateHook_shouldPostDecision` | Unit | mock LLM='true', hookCandidate存在 | output.shouldPost=true, events=[hook:approved_for_post] |
| T54 | callLLM | `test_callLLM_returnsString` | Unit | mock OpenAI応答='hello' | return 'hello' |
| T55 | callLLM | `test_callLLM_throwsOnFailure` | Unit | mock OpenAI API Error | Error thrown |
| T56 | verifier | `test_verifyWithRegeneration_passesOnFirstTry` | Unit | mock scorer score=4 | passed=true, attempts=1 |
| T57 | verifier | `test_verifyWithRegeneration_regeneratesOnFailure` | Unit | mock scorer: 1回目score=2, 2回目score=4 | passed=true, attempts=2 |
| T58 | verifier | `test_verifyWithRegeneration_failsAfterMaxRetries` | Unit | mock scorer score=1 (3回連続) | passed=false, attempts=3 |
| T59 | SAFE-T | `test_scoreContent_crisisDetection` | Unit | content='死にたい' | score=0, crisis=true |
| T60 | SAFE-T | `test_detectSuffering_crisisEvent` | Unit | detection.severity=0.95 | emitEvent('crisis:detected') 呼出 |
| **T61** | **Executor: run_trend_scan** | `test_executeRunTrendScan_interfaceShape` | **Unit** | **空input** | **output.savedCount=Number, output.sources=Array** |
| T62 | Hook API Contract | `test_hookSave_normalCreation` | Integration | POST /api/agent/hooks, 正常HookSaveSchema準拠JSON | 201 + { id, text, createdAt } |
| T63 | Hook API Contract | `test_hookSave_duplicateText` | Integration | POST /api/agent/hooks, 既存hookと同一text | 200 + { status: 'duplicate', existingId } |
| T64 | Hook API Contract | `test_hookSave_idempotencyKey` | Integration | POST /api/agent/hooks, 同じidempotencyKeyで2回送信 | 1回目: 201, 2回目: 200 + duplicate |
| T65 | Hook API Contract | `test_hookSave_invalidSchema` | Integration | POST /api/agent/hooks, targetProblemTypes欠落 | 400 + Zodエラー |
| T66 | Event API Contract | `test_eventPost_hookSaved` | Integration | POST /api/ops/events, kind='hook_saved', tags=['hook_candidate','found'] | 201 + Reaction生成確認 |
| T67 | Event API Contract | `test_eventPost_scanCompleted` | Integration | POST /api/ops/events, kind='scan_completed', tags=['scan','completed'] | 201 + Reaction生成なし |

---

## テスト基盤（Vitest + Supertest + Prisma Mock）

### Vitest 設定

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

### テストセットアップ（Prisma Mock）

```javascript
// apps/api/src/test/setup.js
import { vi, beforeEach } from 'vitest';
import { mockDeep, mockReset } from 'vitest-mock-extended';

const prismaMock = mockDeep();

vi.mock('../lib/prisma.js', () => ({
  prisma: prismaMock
}));

beforeEach(() => {
  mockReset(prismaMock);
});

export { prismaMock };
```

### テスト実行コマンド

```bash
cd apps/api && npx vitest run                    # 全テスト
cd apps/api && npx vitest run --coverage         # カバレッジ付き
cd apps/api && npx vitest run src/services/ops/  # opsのみ
cd apps/api && npx vitest                        # ウォッチモード
```

---

## 実装チェックリスト（12.1〜12.25）

| # | タスク | AC（受け入れ条件） | 状態 |
|---|--------|-------------------|------|
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

---

## 境界（やらないこと）

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

## ファイル構成（最終版）

```
apps/api/
├── prisma/
│   └── schema.prisma                          # ← ops テーブル追加
├── sql/
│   ├── 20260208_add_ops_tables.sql
│   ├── 20260208_seed_ops_policy.sql
│   └── 20260208_seed_ops_trigger_rules.sql
├── vitest.config.js
└── src/
    ├── test/
    │   └── setup.js
    ├── middleware/
    │   └── opsAuth.js
    ├── routes/
    │   └── ops/
    │       ├── index.js
    │       ├── heartbeat.js
    │       ├── approval.js
    │       └── summary.js
    └── services/
        └── ops/
            ├── proposalService.js
            ├── capGates.js
            ├── policyService.js
            ├── eventEmitter.js
            ├── triggerEvaluator.js
            ├── reactionProcessor.js
            ├── staleRecovery.js
            ├── insightPromoter.js
            ├── approvalNotifier.js
            ├── approvalHandler.js
            ├── opsMonitor.js
            ├── __tests__/
            │   ├── proposalService.test.js
            │   ├── capGates.test.js
            │   ├── policyService.test.js
            │   ├── triggerEvaluator.test.js
            │   ├── reactionProcessor.test.js
            │   ├── staleRecovery.test.js
            │   ├── approvalHandler.test.js
            │   └── opsMonitor.test.js
            └── stepExecutors/
                ├── registry.js
                ├── executeDraftContent.js
                ├── executeVerifyContent.js
                ├── executePostX.js
                ├── executePostTiktok.js
                ├── executeFetchMetrics.js
                ├── executeAnalyzeEngagement.js
                ├── executeDiagnose.js
                ├── executeDetectSuffering.js
                ├── executeDraftNudge.js
                ├── executeSendNudge.js
                ├── executeEvaluateHook.js
                ├── executeRunTrendScan.js
                └── __tests__/
                    ├── registry.test.js
                    ├── executeDraftContent.test.js
                    ├── executeVerifyContent.test.js
                    ├── executePostX.test.js
                    ├── executePostTiktok.test.js
                    ├── executeFetchMetrics.test.js
                    ├── executeAnalyzeEngagement.test.js
                    ├── executeDiagnose.test.js
                    ├── executeDetectSuffering.test.js
                    ├── executeDraftNudge.test.js
                    ├── executeSendNudge.test.js
                    ├── executeEvaluateHook.test.js
                    └── executeRunTrendScan.test.js
    ├── lib/
    │   ├── llm.js
    │   └── __tests__/
    │       └── llm.test.js
    ├── services/
    │   ├── verifier.js
    │   └── __tests__/
    │       └── verifier.test.js

VPS (~/.openclaw/workspace/skills/):
├── mission-worker/
│   └── SKILL.md
├── x-poster/
│   └── SKILL.md（移行版）
├── tiktok-poster/
│   └── SKILL.md（移行版）
├── trend-hunter/
│   └── SKILL.md（移行版）
├── suffering-detector/
│   └── SKILL.md（移行版）
└── app-nudge-sender/
    └── SKILL.md（移行版）
```
