# Anicca Filesystem Agent Architecture TODO

最終更新: 2026-02-12  
目的: 「会社/生活をFilesystemとして扱う」設計を、Aniccaの実装タスクに落とす。

---

## 0. ゴール定義

- [ ] Aniccaの状態管理を `state/` 配下に統一する
- [ ] すべての自動化ジョブを `read -> decide -> write` で実装する
- [ ] 監査・権限・安全ポリシーを共通化する
- [ ] iOS/App Nudge + Slack + Gmail + Calendar の4チャネルを同じループに接続する

---

## 1. ディレクトリ規約（最小）

- [ ] `state/users/<userId>/profile.json`
- [ ] `state/users/<userId>/preferences.json`
- [ ] `state/events/<yyyy-mm-dd>.jsonl`
- [ ] `state/inbox/gmail/<yyyy-mm-dd>.jsonl`
- [ ] `state/calendar/<yyyy-mm-dd>.json`
- [ ] `state/nudges/queue.jsonl`
- [ ] `state/nudges/outcomes/<yyyy-mm-dd>.jsonl`
- [ ] `state/tasks/school/<yyyy-mm-dd>.jsonl`
- [ ] `state/tasks/work/<yyyy-mm-dd>.jsonl`
- [ ] `state/tasks/personal/<yyyy-mm-dd>.jsonl`
- [ ] `state/briefings/<yyyy-mm-dd>.md`
- [ ] `state/audit/<yyyy-mm-dd>.jsonl`
- [ ] `state/policies/policy.json`
- [ ] `state/meta/schema-version.json`

---

## 2. スキーマ規約

- [ ] 全JSONに `id`, `source`, `createdAt`, `updatedAt`, `traceId` を持たせる
- [ ] `events` は append-only（上書き禁止）
- [ ] `outcomes` は `eventId`/`actionId` を必須にして因果を追えるようにする
- [ ] `tasks` は `domain`（school/work/personal）と `priorityScore` を必須化する
- [ ] `nudges` は `channel`（app/slack/email）と `status` を必須化する

---

## 3. 実行パターン統一（EPAF）

- [ ] Event Ingest: Gmail/Calendar/Slack/iOSイベントを `state/events` に正規化
- [ ] Policy Engine: SAFE-T, quota, kill-switch, approval-gate を共通適用
- [ ] Action Executor: `draft_email`, `send_nudge`, `send_slack`, `create_brief` を実装
- [ ] Feedback: 反応/成果を `state/nudges/outcomes` と `state/audit` に記録

---

## 4. 権限・ガバナンス

- [ ] P0: `send_email` は禁止、`draft_email` のみ許可
- [ ] P0: 公開投稿/課金/DM返信は approval-gate 経由のみ
- [ ] P0: 危機検知時は SAFE-T で通常フローを強制中断
- [ ] P0: すべてのActionを `audit` に記録（who/why/input/output）
- [ ] P1: ロール別アクセス境界（operator/reviewer/admin）を定義

---

## 5. 実装タスク（Backend）

### Phase 1: 土台修復
- [ ] `NUDGE_ALPHA_USER_ID` を設定して `app-nudge-sender` 復旧
- [ ] Ops Prisma不整合を修正（client再生成 + 再デプロイ）
- [ ] `/api/ops/heartbeat` 5ステップを全緑化

### Phase 2: Filesystem State Writer
- [ ] `apps/api/src/services/state/` を新設
- [ ] `StateWriter`（appendJsonl / writeJson / readJson）を実装
- [ ] 既存 `sufferingDetectorJob` の出力を `state/events` に二重書き
- [ ] 既存 `appNudgeSenderJob` の結果を `state/nudges/outcomes` に書き込み

### Phase 3: Gmail Triage
- [ ] `apps/api/src/integrations/google/gmailClient.js` 追加
- [ ] `apps/api/src/jobs/emailTriageJob.js` 追加
- [ ] `/api/admin/jobs/email-triage` 追加
- [ ] 生成は `draft_email` のみ（送信禁止）
- [ ] 実行結果を `state/inbox/gmail` + `state/audit` に保存

### Phase 4: Calendar Meeting Prep
- [ ] `apps/api/src/integrations/google/calendarClient.js` 追加
- [ ] `apps/api/src/jobs/meetingPrepJob.js` 追加
- [ ] 会議ごとに `state/briefings/<date>.md` を生成
- [ ] Slack通知（要約 + リンク）を送信

### Phase 5: Unified Task Router
- [ ] `apps/api/src/jobs/lifeTaskRouterJob.js` 追加
- [ ] school/work/personal を同一優先度キューで処理
- [ ] 当日「次アクション3件」を App/Slack へ配信

---

## 6. テストTODO

- [ ] `state writer` のユニットテスト追加（破損JSON, 同時書き込み, ローテーション）
- [ ] `jobs` APIテストに `email-triage` / `meeting-prep` を追加
- [ ] SAFE-T割り込み時に action が停止するE2Eテスト追加
- [ ] `traceId` で event -> action -> outcome が辿れることを検証

---

## 7. 運用KPI

- [ ] Time Saved（週あたり削減時間）
- [ ] Draft Acceptance Rate（下書き採用率）
- [ ] Nudge Follow-through（24h実行率）
- [ ] Human Escalation Rate（人間介入率）
- [ ] SAFE-T Accuracy（誤検知/見逃し率）

---

## 8. 完了条件（Definition of Done）

- [ ] 4チャネル（App/Slack/Gmail/Calendar）のイベントが `state/events` に統一保存される
- [ ] 高リスク操作が approval-gate なしで実行されない
- [ ] 1日分の `event -> decision -> action -> outcome` が監査可能
- [ ] 日次で失敗件数・介入件数・効果指標が自動集計される

