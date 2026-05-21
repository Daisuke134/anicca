# Tasks: x402 Factory Skill (to-agents-skill)

**Input**: Design documents from `/specs/005-x402-factory/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks grouped by user story. US1（produce）→ US2（discover）→ US3（measure）の順。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可能（別ファイル、依存なし）
- **[Story]**: [US1] / [US2] / [US3]
- 全タスクに絶対パス記載

---

## Phase 1: Setup（共有インフラ）

**Purpose**: Mac Mini ワークスペース初期化 + リポジトリ構造準備

- [ ] T001 Mac Mini に to-agents ワークスペースを作成: `ssh anicca@100.99.82.95 "mkdir -p /Users/anicca/.openclaw/workspace/to-agents"`
- [ ] T002 to-agents-learning.md をリポジトリからMac Miniにコピー: `scp .cursor/plans/ios/1.6.3/2026-2-18/to-agents-learning.md anicca@100.99.82.95:/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md`
- [ ] T003 Mac Mini に proposals.json を初期化: `ssh anicca@100.99.82.95 "echo '[]' > /Users/anicca/.openclaw/workspace/to-agents/proposals.json"`
- [ ] T004 Mac Mini に metrics.json を初期化: `ssh anicca@100.99.82.95 "echo '[]' > /Users/anicca/.openclaw/workspace/to-agents/metrics.json"`
- [ ] T005 Mac Mini に to-agents-skill スキルディレクトリを作成: `ssh anicca@100.99.82.95 "mkdir -p /Users/anicca/.openclaw/skills/to-agents-skill/templates"`

**Checkpoint**: Mac Mini ワークスペースとスキルディレクトリが存在する

---

## Phase 2: Foundational（全 US の前提条件）

**Purpose**: SKILL.md の共通プロンプトフレームワーク + テンプレート。全USが依存する。

**⚠️ CRITICAL**: このフェーズ完了前に US1/2/3 の実装を開始しない

- [ ] T006 SKILL.md テンプレートファイルを作成: `/Users/anicca/.openclaw/skills/to-agents-skill/templates/skill-template.md`（生成される各スキルの SKILL.md 雛形）
- [ ] T007 to-agents-skill SKILL.md を作成（YAML frontmatter + produce/discover/measure 3モード共通プロンプト）: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`
- [ ] T008 SKILL.md を Mac Mini にコピー: `scp -r .openclaw-staging/to-agents-skill/ anicca@100.99.82.95:/Users/anicca/.openclaw/skills/to-agents-skill/`（またはSSH上で直接作成）

**Checkpoint**: `ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md"` でSKILL.md が表示される

---

## Phase 3: User Story 1 — Operator triggers skill production（Priority: P1）🎯 MVP

**Goal**: `skill_name=emotion-detector` を入力 → Railway エンドポイント + ClawHub + Moltbook + learning.md + #metrics を全自動完走

**Independent Test**（quickstart.md Step 1〜5 を参照）:
1. `awal x402 pay` → 200 OK
2. `clawhub search emotion-detector` → 結果あり
3. Moltbook に宣伝投稿あり
4. `to-agents-learning.md` に emotion-detector エントリあり
5. Slack `#metrics` に完了報告あり

- [ ] T009 [US1] `emotion-detector` ハンドラを作成: `apps/api/src/routes/x402/emotionDetector.js`（buddhistCounsel.js を型に、感情検出システムプロンプトと入出力スキーマを実装）
- [ ] T010 [US1] `index.js` に emotion-detector エントリを追加（paymentMiddleware + router.use）: `apps/api/src/routes/x402/index.js`
- [ ] T011 [US1] コードをコミット＆push（Railway staging 自動デプロイ）: `git add apps/api/src/routes/x402/ && git commit && git push origin 005-x402-factory`
- [ ] T012 [US1] Railway staging デプロイ完了確認（2-3分待機）＋ `awal x402 pay` で 200 OK 検証: `npx awal@2.0.3 x402 pay https://anicca-proxy-staging.up.railway.app/api/x402/emotion-detector -X POST -d '{"text":"I feel anxious"}'`
- [ ] T013 [US1] SKILL.md の produce モードプロンプトが T009-T012 の手順を正しく記述しているか検証（SKILL.md を読んで Anicca が再現できるか目視確認）: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`
- [ ] T014 [US1] `emotion-detector` SKILL.md を生成してMac Miniに配置: `ssh anicca@100.99.82.95 "mkdir -p /Users/anicca/.openclaw/skills/emotion-detector"` ＋ SKILL.md 作成
- [ ] T015 [US1] `clawhub publish` を emotion-detector スキルディレクトリで実行＋結果の clawhub_id を記録: `ssh anicca@100.99.82.95 "cd /Users/anicca/.openclaw/skills/emotion-detector && clawhub publish"`
- [ ] T016 [US1] moltbook-interact スキルで emotion-detector の宣伝投稿を実行＋post_id を記録: `ssh anicca@100.99.82.95 "openclaw agent --message 'Use moltbook-interact to post a promotional message for emotion-detector x402 service at https://anicca-proxy-staging.up.railway.app/api/x402/emotion-detector' --deliver"`
- [ ] T017 [US1] to-agents-learning.md に emotion-detector の LearningEntry を append: `ssh anicca@100.99.82.95` で `/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md` に追記
- [ ] T018 [US1] Slack #metrics に完了報告を送信（endpoint_url + clawhub_id + moltbook_post_id）: `ssh anicca@100.99.82.95 "openclaw message send --channel slack --target 'C091G3PKHL2' --message '...'"`
- [ ] T019 [US1] SKILL.md の produce モードプロンプトを T009〜T018 の実行知識で更新（アウトカム確認後に最終化）: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`

**US1 完了基準**: quickstart.md の Step 1〜5 が全て ✅

---

## Phase 4: User Story 2 — Factory proposes next skill from catalog（Priority: P2）

**Goal**: `discover` モードで Slack #metrics に提案1件が届き、✅ 反応後に produce が走ること

**Independent Test**（quickstart.md US2 テスト参照）:
1. discover モード実行 → #metrics に提案メッセージ1件
2. エンドポイント未作成（承認前は何も作らない）
3. ✅ 反応 → produce モード自動実行

- [ ] T020 [US2] proposals.json の読み書きロジックを SKILL.md discover モードセクションに記述: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`（カタログから未着手スキルを特定、clawhub search で重複チェック、proposals.json に pending エントリ書き込み）
- [ ] T021 [P] [US2] discover モードの Slack ブロックメッセージフォーマットを SKILL.md に記述: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`（skill_name + description + rationale + ✅/❌ 説明）
- [ ] T022 [US2] discover モードのエンドツーエンド動作確認: `ssh anicca@100.99.82.95 "openclaw agent --message 'Execute to-agents-skill. mode=discover.' --deliver"`
- [ ] T023 [US2] proposals.json に pending エントリが作成されたことを確認: `ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/workspace/to-agents/proposals.json"`
- [ ] T024 [US2] Slack #metrics への提案メッセージを確認（エンドポイント未作成であることも確認）

**US2 完了基準**: Slack に提案メッセージが届き、proposals.json に pending エントリがあり、エンドポイントは存在しない

---

## Phase 5: User Story 3 — Factory improves underperforming skills（Priority: P3）

**Goal**: `measure` モードが0コールスキルを検出し、改善提案を #metrics に送信すること

**Independent Test**（quickstart.md US3 テスト参照）:
1. measure モード実行 → #metrics に改善提案メッセージ
2. 提案にスキル名と具体的な改善案が含まれる

- [ ] T025 [US3] measure モードのメトリクス計算ロジックを SKILL.md に記述: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`（to-agents-learning.md から run 記録を集計、7日MA変化率を計算）
- [ ] T026 [P] [US3] 閾値判定と改善提案フォーマットを SKILL.md に記述: `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`（MA -20%以下 → 改善提案、14日0コール → 廃止提案）
- [ ] T027 [US3] measure モードのエンドツーエンド動作確認: `ssh anicca@100.99.82.95 "openclaw agent --message 'Execute to-agents-skill. mode=measure.' --deliver"`
- [ ] T028 [US3] Slack #metrics に改善提案が届いたことを確認（スキル名と具体的な改善案が含まれること）

**US3 完了基準**: #metrics に改善提案メッセージが届く（スキル名明記）

---

## Phase 6: Polish & Cron 登録

**Purpose**: 本番稼働のための最終仕上げ

- [ ] T029 Cron ジョブを jobs.json に追加（差分追記、ファイル全体上書き禁止）: `ssh anicca@100.99.82.95 "..."` で `/Users/anicca/.openclaw/cron/jobs.json` に discover モード daily cron エントリを append（schedule: `0 1 * * *` JST）
- [ ] T030 Gateway 再起動（cron 設定反映）: `ssh anicca@100.99.82.95 "openclaw gateway restart"`
- [ ] T031 Cron エントリが有効であることを確認: `ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/cron/jobs.json | grep to-agents-skill"`
- [ ] T032 spec.md のブランチ名を `001-x402-factory` から `005-x402-factory` に修正: `specs/005-x402-factory/spec.md`（先頭の Feature Branch フィールド）
- [ ] T033 完了コミット（全成果物をステージ＆push）: `git add -A && git commit -m "feat(x402-factory): implement to-agents-skill P1〜P3 complete" && git push origin 005-x402-factory`

---

## Dependencies（完了順）

```
Phase 1（T001-T005）
  └── Phase 2（T006-T008）
        ├── Phase 3 US1（T009-T019）  ← MVP
        │     └── Phase 4 US2（T020-T024）  ← US1完了後
        │           └── Phase 5 US3（T025-T028）  ← US2完了後
        └── Phase 6 Polish（T029-T033）  ← 全US完了後
```

**並列実行可能**（[P] マーク付きタスク）:
- T021 と T020 は同一ファイルだが内容が独立 → 直列推奨
- T026 と T025 は同一ファイルだが内容が独立 → 直列推奨

---

## Implementation Strategy

| スコープ | タスク | 説明 |
|---------|--------|------|
| **MVP（推奨開始点）** | T001〜T019 | US1 のみ。1スキルを手動 produce できれば価値証明完了 |
| **Autonomous mode** | T001〜T024 | US1 + US2。discover モードで承認ゲートが機能 |
| **Full loop** | T001〜T033 | US1〜US3 + Cron。完全自律ループ |

**推奨 MVP**: T001〜T019 を完走して `emotion-detector` が live on ClawHub になれば、工場としての価値が確認できる。その後 US2（discover）→ US3（measure）と順次拡張する。

---

## Summary

| 項目 | 値 |
|------|-----|
| **総タスク数** | 33 |
| **US1（produce）** | T009〜T019（11タスク） |
| **US2（discover）** | T020〜T024（5タスク） |
| **US3（measure）** | T025〜T028（4タスク） |
| **Setup/Foundation** | T001〜T008（8タスク） |
| **Polish/Cron** | T029〜T033（5タスク） |
| **並列機会** | T021[P], T026[P]（同フェーズ内で先行タスクと独立） |
| **MVP スコープ** | T001〜T019（Phase 1〜3） |
