# Tasks: NAIST Deadline Management

**Input**: Design documents from `/specs/002-naist-deadline/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: TDD スタイル（ダイスの指示）— テストを先に書いてREDを確認してから実装

**Deploy先**: `/Users/anicca/.openclaw/skills/naist-deadline/`

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: プロジェクト初期化・ディレクトリ構造作成

- [ ] T001 Mac Mini上にディレクトリ構造を作成: `/Users/anicca/.openclaw/skills/naist-deadline/scripts/utils/`, `/data/`, `/tests/`
- [ ] T002 `package.json` を作成（dependencies: `@slack/web-api`, `chrono-node`, `uuid`; devDependencies: `jest`）in `/Users/anicca/.openclaw/skills/naist-deadline/package.json`
- [ ] T003 `npm install` を実行して依存関係をインストール
- [ ] T004 `data/deadlines.json` の初期ファイルを作成（空のスキーマ `{"schemaVersion":1,"deadlines":[]}`）in `/Users/anicca/.openclaw/skills/naist-deadline/data/deadlines.json`

---

## Phase 2: Foundational（全Storyに共通）

**Purpose**: 全スクリプトが依存するユーティリティ層

**⚠️ CRITICAL**: この phase が完了するまでどのUser Storyも実装できない

- [ ] T005 [P] **[RED]** `storage.js` のテストを書く（read/write/atomic-write の全ケース）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/storage.test.js`
- [ ] T006 [P] **[RED]** `date.js` のテストを書く（自然言語パース: "明日", "来週月曜", "3月10日"）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/date.test.js`
- [ ] T007 `jest --testPathPattern=storage` を実行してテストが **RED** であることを確認
- [ ] T008 `jest --testPathPattern=date` を実行してテストが **RED** であることを確認
- [ ] T009 [P] **[GREEN]** `utils/storage.js` を実装（JSON読み書き、原子的書き込み: tmp→rename）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/utils/storage.js`
- [ ] T010 [P] **[GREEN]** `utils/date.js` を実装（chrono-nodeで自然言語→ISO8601変換）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/utils/date.js`
- [ ] T011 `jest --testPathPattern="storage|date"` を実行して全テストが **GREEN** であることを確認

**Checkpoint**: storage + date ユーティリティ完成 → User Story実装開始可能

---

## Phase 3: User Story 1 - 締切一覧を確認する (Priority: P1) 🎯 MVP

**Goal**: 「締切確認して」でSlackに一覧が返る

**Independent Test**: `node scripts/list.js` を実行してコンソールに一覧が出力される

### Tests for User Story 1 ⚠️ テストを先に書く

> **RED を確認してから実装に進む**

- [ ] T012 [P] [US1] **[RED]** `list.js` のテストを書く（空/1件/複数件の一覧、done除外、直近順ソート）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/list.test.js`
- [ ] T013 `jest --testPathPattern=list` を実行してテストが **RED** であることを確認

### Implementation for User Story 1

- [ ] T014 [US1] **[GREEN]** `scripts/list.js` を実装（deadlines.json読み込み→done:false絞り込み→直近順ソート→Slack形式出力）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/list.js`
- [ ] T015 [US1] `jest --testPathPattern=list` で全テスト **GREEN** 確認
- [ ] T016 [US1] `node scripts/list.js` を実際に実行してコンソール出力を確認（Mac Mini上）

**Checkpoint**: User Story 1 完成 — 「締切確認して」が機能する

---

## Phase 4: User Story 2 - 新しい締切を登録する (Priority: P2)

**Goal**: 「〇〇を△日まで追加して」でJSONに保存されSlackに確認が返る

**Independent Test**: `node scripts/register.js "テストレポート" "2026-03-10"` を実行してJSONに追加される

### Tests for User Story 2

- [ ] T017 [P] [US2] **[RED]** `register.js` のテストを書く（正常登録、自然言語日付、重複確認、過去日付警告）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/register.test.js`
- [ ] T018 `jest --testPathPattern=register` を実行してテストが **RED** であることを確認

### Implementation for User Story 2

- [ ] T019 [US2] **[GREEN]** `scripts/register.js` を実装（引数受け取り→date.jsでパース→UUID生成→storage.jsで保存→Slack形式確認メッセージ出力）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/register.js`
- [ ] T020 [US2] `jest --testPathPattern=register` で全テスト **GREEN** 確認
- [ ] T021 [US2] `node scripts/register.js "機械学習レポート" "2026-03-10"` を実際に実行してdata/deadlines.jsonに追加されることを確認（Mac Mini上）
- [ ] T022 [US2] `node scripts/list.js` を実行して登録した締切が一覧に出ることを確認

**Checkpoint**: User Stories 1 + 2 完成 — 登録・確認が機能する

---

## Phase 5: User Story 4 - 完了した締切を消す (Priority: P4 → P3より先に実装)

**Goal**: 「〇〇、完了にして」でdone:trueになり一覧から消える

**Why P4 before P3**: scan.js（US3）はdone:trueの除外処理が必要なため、complete.jsが先にある方が安全

**Independent Test**: `node scripts/complete.js "機械学習レポート"` でdone:trueになりlist.jsから消える

### Tests for User Story 4

- [ ] T023 [P] [US4] **[RED]** `complete.js` のテストを書く（正常完了、タイトル部分一致、同名複数の警告、存在しない課題）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/complete.test.js`
- [ ] T024 `jest --testPathPattern=complete` を実行してテストが **RED** であることを確認

### Implementation for User Story 4

- [ ] T025 [US4] **[GREEN]** `scripts/complete.js` を実装（タイトル部分一致検索→done:true更新→storage.jsで保存→次の締切表示）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/complete.js`
- [ ] T026 [US4] `jest --testPathPattern=complete` で全テスト **GREEN** 確認
- [ ] T027 [US4] end-to-endテスト: register → list → complete → list の順で実際に実行して動作確認（Mac Mini上）

---

## Phase 6: User Story 3 - 自動リマインド (Priority: P3)

**Goal**: cronから呼ばれてSlackに期限通知が届く

**Independent Test**: `node scripts/scan.js` を実行してSlackに通知が届く（締切が近いテストデータ使用）

### Tests for User Story 3

- [ ] T028 [P] [US3] **[RED]** `scan.js` のテストを書く（1時間前検出、前日検出、当日ダイジェスト、remindedAt重複防止）in `/Users/anicca/.openclaw/skills/naist-deadline/tests/scan.test.js`
- [ ] T029 `jest --testPathPattern=scan` を実行してテストが **RED** であることを確認

### Implementation for User Story 3

- [ ] T030 [US3] **[GREEN]** `scripts/scan.js` を実装（deadlines.json読み込み→残り時間計算→リマインド判定→Slack送信→remindedAt更新）in `/Users/anicca/.openclaw/skills/naist-deadline/scripts/scan.js`
- [ ] T031 [US3] `jest --testPathPattern=scan` で全テスト **GREEN** 確認
- [ ] T032 [US3] テスト用の締切（1時間後）をJSONに直接書き込んで `node scripts/scan.js` を実行し、Slackに通知が届くことを確認（Mac Mini上 — live test）

---

## Phase 7: SKILL.md + Cron 登録

**Purpose**: OpenClawスキルとして登録・cronジョブ設定

- [ ] T033 `SKILL.md` を作成（frontmatter: name/description/triggers、実行手順を日本語で記載）in `/Users/anicca/.openclaw/skills/naist-deadline/SKILL.md`
- [ ] T034 Mac Mini上で `openclaw cron add --job-id naist-deadline-scanner --schedule "0 * * * *" --tz Asia/Tokyo --message "Check NAIST deadlines for reminders"` を実行
- [ ] T035 Mac Mini上で `openclaw cron add --job-id naist-deadline-digest --schedule "0 8 * * *" --tz Asia/Tokyo --message "Send NAIST daily deadline digest"` を実行
- [ ] T036 `openclaw cron list` でcronジョブが登録されていることを確認

---

## Phase 8: Polish & Full Integration Test

- [ ] T037 Slackから「締切追加して：機械学習レポート、3月10日」を送信してAniccaが登録することを確認（Slack経由 live test）
- [ ] T038 Slackから「締切確認して」を送信して一覧が返ることを確認
- [ ] T039 Slackから「機械学習レポート、完了にして」を送信して完了処理が動くことを確認
- [ ] T040 全テストを一括実行 `jest` してCIグリーン確認
- [ ] T041 git commit & push（`feat(naist-deadline): add deadline management skill`）

---

## Dependencies & Execution Order

| フェーズ | 依存 |
|---------|------|
| Phase 1 (Setup) | なし |
| Phase 2 (Foundational) | Phase 1 完了後 |
| Phase 3 (US1: list) | Phase 2 完了後 |
| Phase 4 (US2: register) | Phase 2 完了後（Phase 3と並列可） |
| Phase 5 (US4: complete) | Phase 4 完了後 |
| Phase 6 (US3: scan) | Phase 5 完了後 |
| Phase 7 (SKILL.md + cron) | Phase 6 完了後 |
| Phase 8 (full test) | Phase 7 完了後 |

## TDD 原則（各実装タスクで必須）

| ステップ | 内容 |
|---------|------|
| RED | テストを書く → `jest` で失敗を確認 |
| GREEN | 最小限のコードで通す |
| REFACTOR | コードをきれいにする（テストは通ったまま） |
