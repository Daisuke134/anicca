# Feature Specification: naist-events

**Feature Branch**: `004-naist-events`
**Created**: 2026-02-24
**Status**: Draft

## User Scenarios & Testing

### User Story 1 — 週次イベント自動通知 (Priority: P1)

毎週月曜日の朝、NAISTの今週開催予定のイベント（講演・研究会・説明会など）がSlackに自動投稿される。

**Why this priority**: 見逃しを防ぐ。手動でポータルを確認する手間をゼロにする。

**Independent Test**: DRY_RUN=1 でスキャンを実行し、イベント一覧がコンソールに出力されること。

**Acceptance Scenarios**:

1. **Given** 今週のNAISTイベントが存在する、**When** cronが09:20に発火する、**Then** イベント一覧がSlackに投稿される
2. **Given** 今週のイベントが0件、**When** cronが発火する、**Then** 「今週の開催予定イベントはありません」とSlackに投稿される
3. **Given** Firecrawlがタイムアウトする、**When** スキャンを実行する、**Then** エラーメッセージをSlackに投稿してexit 0

---

### User Story 2 — 手動リフレッシュ (Priority: P2)

Aniccaに「イベント確認して」と話しかけると即時にイベント情報を取得してSlackに投稿する。

**Why this priority**: 緊急確認ニーズに対応。cronを待たなくて済む。

**Independent Test**: `node scripts/scan.js` を直接実行してSlack投稿またはDRY_RUN出力が確認できること。

**Acceptance Scenarios**:

1. **Given** ユーザーが「イベント確認して」と発言する、**When** スキルが発動する、**Then** scan.jsが実行されてSlack投稿される

---

### User Story 3 — Googleカレンダー登録 (Priority: P3)

Slackに表示されたイベントに対して「カレンダーに追加して」と依頼すると、gog-calendarスキルを使ってGoogleカレンダーに登録される。

**Why this priority**: 確認だけでなく行動まで完結させる。

**Independent Test**: `node scripts/add-to-calendar.js "<イベント名>" "<日時>" "<場所>"` を実行してgog-calendarが呼ばれること。

**Acceptance Scenarios**:

1. **Given** イベント情報（タイトル・日時・場所）が明確、**When** ユーザーがカレンダー追加を依頼する、**Then** gog-calendarスキルでGoogleカレンダーに登録される
2. **Given** 日時が不明確、**When** カレンダー追加を試みる、**Then** 「日時が不明なため追加できません」と返す

---

### Edge Cases

- naist.jp/events/ にアクセス不可の場合 → エラーSlack通知してexit 0
- イベント情報のパースに失敗した場合（構造変更）→ ローフォーマットで投稿
- 同一イベントを重複投稿しない（cache.jsonで管理）

## Requirements

### Functional Requirements

- **FR-001**: システムはFirecrawl CLI（`/opt/homebrew/bin/firecrawl scrape`）を使ってnaist.jp/events/をスクレイプしなければならない
- **FR-002**: システムは今週（月〜日）開催のイベントのみを抽出しなければならない
- **FR-003**: システムはcache.jsonで通知済みイベントを管理し、重複投稿を防がなければならない
- **FR-004**: システムは毎週月曜09:20 JSTにcronで自動実行されなければならない（`20 9 * * 1`）
- **FR-005**: システムはDRY_RUN=1でSlack投稿をスキップしてコンソールに出力しなければならない
- **FR-006**: システムはエラー時にSlackにエラーメッセージを投稿してexit 0で終了しなければならない
- **FR-007**: システムはUS3のため`add-to-calendar.js`でgog-calendarスキルを呼び出せなければならない
- **FR-008**: SKILL.mdのcommandトリガーで手動実行とカレンダー追加が発動しなければならない

### Key Entities

- **NaistEvent**: title（str）、date（ISO8601）、time（str|null）、location（str|null）、url（str）、description（str|null）
- **EventCache**: `{ notified: string[], lastFetchedAt: string|null }` — notifiedはeventのIDまたはtitle+date

## Success Criteria

### Measurable Outcomes

- **SC-001**: 全テスト GREEN（fetch/notify/scan/calendar の各モジュールテスト）
- **SC-002**: DRY_RUN=1での手動実行が5秒以内に完了する
- **SC-003**: 重複投稿なし（cache.jsonが正しく機能する）
- **SC-004**: cronジョブがjobs.jsonに登録されMac Miniで週次実行される
- **SC-005**: US3のgog-calendar連携が動作する（DRY_RUN確認）

## Assumptions

- naist.jp/events/ のURLは有効で、FirecrawlでMarkdown取得可能
- gog-calendarスキルは `/Users/anicca/.openclaw/skills/gog-calendar/` に存在する
- Slack channel ID は `C091G3PKHL2`（naist-fundsと同じ）
- イベントIDとしてtitle+dateのハッシュまたは結合文字列を使用
