# Anicca Life Automation 実装計画（決定版）

最終更新: 2026-02-12  
目的: Anicca を「苦しみ低減エージェント」として、iOS/App Nudge + Slack + Gmail + Calendar を統合し、日常タスクを自律実行する。

---

## Decision（1つに固定）

**実装は「Event-Policy-Action-Feedback（EPAF）単一アーキテクチャ」に統一する。**  
すべての自動化（メール、Slack、会議準備、学業/仕事タスク補助）は、この1本のループに載せる。

```
[Event Ingest]
  Gmail / Calendar / Slack / App Events / Manual Trigger
      ↓
[Policy Engine]
  SAFE-T, kill switch, quota, PII mask, approval gate
      ↓
[Action Executor]
  draft_email / send_slack / create_todo / send_nudge / create_brief
      ↓
[Feedback + Learning]
  outcome保存 → 次回の優先度・文体・タイミング最適化
```

---

## 1. これは何か（openclaw-anicca.md の意味）

`openclaw-anicca.md` は「OpenClaw × Anicca 運用の現時点 SSOT」。

- 何が動いているか: SAFE-T、autonomy-check、Moltbook/X/TikTok の一部
- 何が詰まっているか: `NUDGE_ALPHA_USER_ID` 未設定、Ops Prisma 不整合
- 何を次に潰すべきか: app-nudge 送信復旧、`proposal → mission → step → event` のE2E完了

つまり、**土台はあるが、全自動化に必要な「個人ワークフロー統合（Gmail/Calendar/Slack）」が未実装**という状態。

---

## 2. このリポジトリでの実装位置（確定）

### Backend Hub（既存を拡張）
- `apps/api/src/routes/admin/jobs.js`
- `apps/api/src/routes/ops/heartbeat.js`
- `apps/api/src/services/ops/proposalService.js`
- `apps/api/src/jobs/appNudgeSenderJob.js`
- `apps/api/src/jobs/sufferingDetectorJob.js`
- `apps/api/src/services/slackNotifier.js`

### iOS Channel（既存活用）
- `aniccaios/aniccaios/AppDelegate.swift`
- `aniccaios/aniccaios/Debug/E2ENotificationDebugView.swift`

---

## 3. 実装フェーズ（順序固定）

## Phase 1: 既存ブロッカー解消（最優先）
1. `NUDGE_ALPHA_USER_ID` を本番環境へ設定し、`/api/admin/jobs/app-nudge-sender` を `ok:true` 化
2. Ops Prisma client を再生成・再デプロイし、`/api/ops/proposal` 500 を解消
3. heartbeat 5ステップ（triggers/reactions/steps/insights/stale）を全緑化

完了条件:
- `app_nudge_enqueued` が監査ログに連続記録
- `ops-heartbeat` エラーが0件

## Phase 2: Gmail Triage Agent（メール自動化）
1. `apps/api/src/integrations/google/gmailClient.js` 新設
2. `apps/api/src/jobs/emailTriageJob.js` 新設
3. `apps/api/src/routes/admin/jobs.js` に `/email-triage` 追加
4. 判定結果を `opsProposal` 経由で処理（urgentはapproval必須）

実行仕様:
- 毎朝 06:00: inbox scan
- `urgent/client/sales/spam` 分類
- 返信は**送信せず draft 作成**をデフォルト
- Slack `#metrics` に「処理件数/要確認件数」を通知

## Phase 3: Calendar Meeting Prep Agent（会議準備）
1. `apps/api/src/integrations/google/calendarClient.js` 新設
2. `apps/api/src/jobs/meetingPrepJob.js` 新設
3. 予定ごとに「前回メール要点 + TODO + 本日アジェンダ」を生成
4. Slack DM または Notion連携へ出力（最初はSlack DM）

## Phase 4: Slack Work Orchestrator（業務導線）
1. `apps/api/src/jobs/slackTaskRouterJob.js` 新設
2. メンション/DMから「依頼抽出→提案化→実行」の自動ループ化
3. SAFE-T/kill switch/日次quotaを全stepに共通適用

## Phase 5: Life OS化（学業/仕事/私生活）
1. `task_source` を追加（school/work/personal/health）
2. `priority_score` を event へ保持し、当日実行順を自動最適化
3. 1日3回（朝/昼/夜）に「次アクション3件」をNudge + Slackで配信

---

## 4. ガードレール（全フェーズ共通）

1. `send_email` は初期禁止、`draft_email` のみ許可
2. 危機兆候（SAFE-T条件）で通常オートメーション中断
3. 高リスク操作（送信/公開/課金）は `opsProposal` で承認ゲート
4. 監査ログ（`agentAuditLog`）を全 action に強制

---

## 5. すぐ着手する実装タスク（次の1週間）

1. Phase 1 を完了（Nudge復旧 + Prisma整合）
2. `emailTriageJob.js` を追加し、dry-runで実データ検証
3. `meetingPrepJob.js` を追加し、Slack DM出力まで通す
4. `jobs.test.js` に2ジョブ分のAPIテスト追加
5. `openclaw-anicca.md` に「Life Automation進捗」セクション追加

---

## 6. KPI（自動化の成功判定）

- Time Saved: 週あたり削減時間
- Draft Acceptance Rate: 下書き採用率
- Nudge Follow-through: Nudge後24hの実行率
- Crisis Interruption Accuracy: SAFE-T中断の誤検知/漏れ
- Human Escalation Rate: 手動介入率（下げる）

