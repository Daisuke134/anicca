# Tasks: naist-events

**Feature**: NAISTイベント週次通知 + カレンダー登録スキル
**Branch**: `004-naist-events`
**Total Tasks**: 26
**TDD Style**: RED (test first) → GREEN (implement) → REFACTOR

---

## Phase 1: Setup

*プロジェクト初期化。全Phaseの前提。*

- [ ] T001 Mac Mini上にディレクトリ構造作成: `mkdir -p /Users/anicca/.openclaw/skills/naist-events/{scripts/utils,tests,data}`
- [ ] T002 `package.json` 作成（jest設定含む）: `/Users/anicca/.openclaw/skills/naist-events/package.json`
- [ ] T003 npm install: `/Users/anicca/.openclaw/skills/naist-events/` で `npm install --save-dev jest`

---

## Phase 2: Foundational (utils)

*全User Storyが依存するutilsモジュール。Phase 1完了後に実行。*

- [ ] T004 [RED] `storage.test.js` 作成（loadCache/saveCache: 空ファイル/正常/atomic write）: `/Users/anicca/.openclaw/skills/naist-events/tests/storage.test.js`
- [ ] T005 [GREEN] `utils/storage.js` 実装（loadCache/saveCache, NAIST_EVENTS_DATA_DIR対応）: `/Users/anicca/.openclaw/skills/naist-events/scripts/utils/storage.js`
- [ ] T006 [RED] `slack.test.js` 作成（DRY_RUN/通常投稿/エラー）: `/Users/anicca/.openclaw/skills/naist-events/tests/slack.test.js`
- [ ] T007 [GREEN] `utils/slack.js` 実装（DRY_RUN, SLACK_CHANNEL_ID, openclaw message send）: `/Users/anicca/.openclaw/skills/naist-events/scripts/utils/slack.js`

**Independent Test**: `npx jest tests/storage.test.js tests/slack.test.js` → 全件GREEN

---

## Phase 3: US1 — 週次イベント自動通知

*毎週月曜09:20 JSTのcron自動実行。Phase 2完了後に実行。*

### P1 Story Goal
cronが月曜朝に自動実行され、今週のNAISTイベントをSlackに投稿する。

### Independent Test Criteria
`DRY_RUN=1 node scripts/scan.js` → `[naist-events] スキャン完了: 新着N件 / スキップN件`

### Tasks

- [ ] T008 [RED] [US1] `fetch.test.js` 作成（Firecrawl mockで今週イベント返却/空配列/エラー）: `/Users/anicca/.openclaw/skills/naist-events/tests/fetch.test.js`
- [ ] T009 [GREEN] [US1] `fetch.js` 実装（Firecrawl CLI呼び出し → NaistEvent[] 今週フィルタ）: `/Users/anicca/.openclaw/skills/naist-events/scripts/fetch.js`
- [ ] T010 [RED] [US1] `notify.test.js` 作成（新規投稿/重複スキップ/0件メッセージ）: `/Users/anicca/.openclaw/skills/naist-events/tests/notify.test.js`
- [ ] T011 [GREEN] [US1] `notify.js` 実装（cache dedup → Slack投稿フォーマット → cache更新）: `/Users/anicca/.openclaw/skills/naist-events/scripts/notify.js`
- [ ] T012 [RED] [US1] `scan.test.js` 作成（fetch+notify呼び出し/エラーSlack通知）: `/Users/anicca/.openclaw/skills/naist-events/tests/scan.test.js`
- [ ] T013 [GREEN] [US1] `scan.js` 実装（loadEnv/fetchEvents/notifyEvents/エラー処理）: `/Users/anicca/.openclaw/skills/naist-events/scripts/scan.js`

---

## Phase 4: US3 — Googleカレンダー登録

*gog CLIでカレンダー追加。Phase 2完了後に実行（Phase 3と並列可）。*

### P3 Story Goal
`add-to-calendar.js <title> <date> <startTime> [endTime] [location]` でGoogleカレンダーに登録。

### Independent Test Criteria
`DRY_RUN=1 node scripts/add-to-calendar.js "テスト" "2026-03-02" "14:00" "15:00" "D207"` → `[DRY_RUN] カレンダー追加スキップ`

### Tasks

- [ ] T014 [P] [RED] [US3] `calendar.test.js` 作成（gog CLI呼び出し/DRY_RUN/日時バリデーション/endTime自動計算）: `/Users/anicca/.openclaw/skills/naist-events/tests/calendar.test.js`
- [ ] T015 [P] [GREEN] [US3] `add-to-calendar.js` 実装（gog calendar events add / DRY_RUN / +1h endTime）: `/Users/anicca/.openclaw/skills/naist-events/scripts/add-to-calendar.js`

---

## Phase 5: SKILL.md + Cron登録

*Phase 3, 4完了後に実行。OpenClaw発動とcron登録。*

- [ ] T016 SKILL.md作成（YAML frontmatter: name/description/commands）: `/Users/anicca/.openclaw/skills/naist-events/SKILL.md`
- [ ] T017 cron jobs.jsonに `naist-events-scan` 追加（`20 9 * * 1`, tz: Asia/Tokyo）: `/Users/anicca/.openclaw/cron/jobs.json`

---

## Phase 6: 統合テスト & 検証

*全実装完了後。Mac Mini上で実行確認。*

- [ ] T018 全テスト実行 GREEN確認: `npx jest --no-coverage` on Mac Mini
- [ ] T019 DRY_RUN=1でscan.js手動実行確認: `DRY_RUN=1 node scripts/scan.js`
- [ ] T020 DRY_RUN=1でadd-to-calendar.js手動実行確認: `DRY_RUN=1 node scripts/add-to-calendar.js "test" "2026-03-02" "14:00"`
- [ ] T021 cronジョブ登録確認: `cat /Users/anicca/.openclaw/cron/jobs.json | python3 -m json.tool | grep naist-events`

---

## Dependencies

```
Phase 1 (T001-T003)
  └── Phase 2 (T004-T007)
        ├── Phase 3 (T008-T013)  [US1]
        └── Phase 4 (T014-T015)  [US3, Phase 3と並列可]
              └── Phase 5 (T016-T017)
                    └── Phase 6 (T018-T021)
```

## Parallel Execution Examples

```bash
# Phase 3 & Phase 4 は独立してるので並列実行可能
# エージェント1: Phase 3 (fetch/notify/scan)
# エージェント2: Phase 4 (add-to-calendar)

# Phase 2のutilsが完了後、同時起動:
# Agent1: T008→T009→T010→T011→T012→T013
# Agent2: T014→T015
```

## Implementation Strategy

| スコープ | タスク | 価値 |
|---------|--------|------|
| **MVP** | Phase 1-3 + T016-T017 | 週次Slack通知が動く |
| **Full** | MVP + Phase 4 | カレンダー登録まで完結 |

---

## Format Validation

| 項目 | 確認 |
|------|------|
| 全タスクに `- [ ]` checkbox | ✅ |
| 全タスクに TaskID (T001-T021) | ✅ |
| US phaseに [USN] ラベル | ✅ |
| 並列可能タスクに [P] | ✅ T014, T015 |
| 全タスクにファイルパス | ✅ |
