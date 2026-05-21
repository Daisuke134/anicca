# Implementation Plan: naist-events

**Branch**: `004-naist-events`
**Feature**: NAISTイベント週次通知 + カレンダー登録スキル
**Target**: Mac Mini `/Users/anicca/.openclaw/skills/naist-events/`

## Technical Context

| 項目 | 値 |
|------|-----|
| Runtime | Node.js 18+ (Mac Mini) |
| スクレイピング | Firecrawl CLI (`/opt/homebrew/bin/firecrawl scrape`) |
| スクレイピング対象 | `https://www.naist.jp/event/` |
| カレンダー | `gog calendar events add primary` (naist-calendarと同じ) |
| Slack | `openclaw message send` + `utils/slack.js` |
| テスト | Jest |
| cron | `20 9 * * 1` (月曜09:20 JST) |
| データ | `data/cache.json` (atomic write) |

## Constitution Check

プロジェクトのconstitution.mdは未設定（テンプレート状態）のため、CLAUDE.mdのルールを適用:

| ルール | チェック |
|--------|---------|
| TDD必須 (tests FIRST) | ✅ 各フェーズでテスト先行 |
| DRY_RUN対応 | ✅ slack.jsにDRY_RUN実装 |
| Firecrawl CLI使用 | ✅ fetch.jsで使用 |
| Mac Miniで実装 | ✅ SSH経由で全操作 |
| atomic write | ✅ tmp + renameSync |
| エラー時exit 0 | ✅ scan.jsのtry-catch |

## Phase 1: Setup

```
T001: ディレクトリ構造作成 (scripts/, tests/, data/)
T002: package.json + npm install (jest, @jest/globals)
```

## Phase 2: Foundational (utils)

```
T003: [RED] storage.test.js - loadCache/saveCache/loadGuides
T004: [GREEN] utils/storage.js 実装
T005: [RED] slack.test.js - DRY_RUN/通常投稿
T006: [GREEN] utils/slack.js 実装
```

## Phase 3: US1 (週次通知)

```
T007: [RED] fetch.test.js - Firecrawl mock, NaistEvent[]返却, エラー
T008: [GREEN] scripts/fetch.js 実装
T009: [RED] notify.test.js - 新規投稿/重複スキップ/0件
T010: [GREEN] scripts/notify.js 実装
T011: [RED] scan.test.js - scan()の呼び出し確認, エラーSlack通知
T012: [GREEN] scripts/scan.js 実装
```

## Phase 4: US3 (カレンダー登録)

```
T013: [RED] calendar.test.js - gog CLI呼び出し, DRY_RUN, 時刻バリデーション
T014: [GREEN] scripts/add-to-calendar.js 実装
```

## Phase 5: SKILL.md + cron

```
T015: SKILL.md作成 (YAML frontmatter + コマンドトリガー)
T016: cron jobs.jsonに naist-events-scan 追加 (Mac Mini)
```

## Phase 6: 統合テスト

```
T017: 全テスト GREEN確認 (npx jest)
T018: DRY_RUN=1 でscan.js手動実行確認
T019: DRY_RUN=1 でadd-to-calendar.js手動実行確認
```

## Dependencies

- Phase 2 → Phase 1 完了後
- Phase 3 → Phase 2 完了後
- Phase 4 → Phase 2 完了後 (Phaseに3と並列可)
- Phase 5 → Phase 3, 4 完了後
- Phase 6 → Phase 5 完了後

## Artifacts Generated

| ファイル | ステータス |
|---------|-----------|
| spec.md | ✅ 完了 |
| research.md | ✅ 完了 |
| data-model.md | ✅ 完了 |
| contracts/skill-interface.md | ✅ 完了 |
| quickstart.md | ✅ 完了 |
| plan.md | ✅ 完了 |
| tasks.md | 次ステップ |
