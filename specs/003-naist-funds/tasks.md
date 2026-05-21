# Tasks: naist-funds

**Input**: Design documents from `/specs/003-naist-funds/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD（/tdd-workflow）— テストを先に書き、RED確認後に実装する。

**Organization**: User Story（US1/US2/US3）ごとにフェーズを分割。各フェーズは独立してテスト可能。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可（異なるファイル、完了済みタスクへの依存なし）
- **[Story]**: 属するUser Story（US1, US2, US3）
- ファイルパスは全て絶対パス（Mac Mini上: `/Users/anicca/.openclaw/skills/naist-funds/`）

---

## Phase 1: Setup（プロジェクト初期化）

**Purpose**: スキルディレクトリとpackage.jsonのセットアップ

- [ ] T001 Mac Miniにsshしてスキルディレクトリを作成: `/Users/anicca/.openclaw/skills/naist-funds/{scripts/utils,data,tests}`
- [ ] T002 `package.json` を作成（name: naist-funds, jest設定込み）: `/Users/anicca/.openclaw/skills/naist-funds/package.json`
- [ ] T003 `npm install --save-dev jest` をMac Mini上で実行してdevDependency導入
- [ ] T004 [P] `data/cache.json` を初期化: `{"notified":[],"lastFetchedAt":null}`
- [ ] T005 [P] `data/guides.json` を初期化（学振DC1/DC2・JST さきがけ/CRESTの4件シード）: `/Users/anicca/.openclaw/skills/naist-funds/data/guides.json`

---

## Phase 2: Foundational（共通ユーティリティ）

**Purpose**: 全User Storyが依存する共通モジュール。このフェーズ完了前にUS実装不可。

**⚠️ CRITICAL**: Phase 2完了まで全User Story作業を開始しない。

- [ ] T006 [P] `tests/storage.test.js` を作成（RED）: loadCache/saveCache/loadGuidesの単体テスト（原子的書き込み含む）
- [ ] T007 [P] `tests/slack.test.js` を作成（RED）: sendMessage がexecをコールするかの単体テスト
- [ ] T008 `scripts/utils/storage.js` を実装（GREEN）: loadCache/saveCache（tmp+renameSync）/loadGuides: `/Users/anicca/.openclaw/skills/naist-funds/scripts/utils/storage.js`
- [ ] T009 `scripts/utils/slack.js` を実装（GREEN）: sendMessage → `openclaw message send` + DRY_RUN対応: `/Users/anicca/.openclaw/skills/naist-funds/scripts/utils/slack.js`
- [ ] T010 `npm test -- tests/storage.test.js tests/slack.test.js` でGREEN確認

**Checkpoint**: storage + slack ユーティリティが全テストGREEN → US実装開始可能

---

## Phase 3: User Story 1 — 週次助成金情報の自動通知 (Priority: P1) 🎯 MVP

**Goal**: cronから起動して新着助成金をSlackに投稿する。締切30日以内は⚠️強調。重複防止あり。

**Independent Test**: `DRY_RUN=1 node scripts/scan.js` を実行してstdoutに助成金一覧が出力される。

### Tests（TDD: 先に書いてREDを確認）

- [ ] T011 [P] [US1] `tests/fetch.test.js` を作成（RED）: Firecrawl CLIをexec-mockしてGrant[]が返ることをテスト: `/Users/anicca/.openclaw/skills/naist-funds/tests/fetch.test.js`
- [ ] T012 [P] [US1] `tests/notify.test.js` を作成（RED）: 新規Grant投稿・重複スキップ・⚠️マークの3シナリオ: `/Users/anicca/.openclaw/skills/naist-funds/tests/notify.test.js`
- [ ] T013 [P] [US1] `tests/scan.test.js` を作成（RED）: scan.jsがnotify.jsを呼び出しSlackに投稿することをテスト: `/Users/anicca/.openclaw/skills/naist-funds/tests/scan.test.js`

### Implementation

- [ ] T014 [US1] `scripts/fetch.js` を実装（GREEN）: Firecrawl CLIでJSPS/JST/JFUNDをスクレイピング→Grant[]→JSON stdout出力: `/Users/anicca/.openclaw/skills/naist-funds/scripts/fetch.js`
- [ ] T015 [US1] `scripts/notify.js` を実装（GREEN）: fetch→cache照合→⚠️付与→Slack投稿→cache更新: `/Users/anicca/.openclaw/skills/naist-funds/scripts/notify.js`
- [ ] T016 [US1] `scripts/scan.js` を実装（GREEN）: cronエントリポイント。notify.js実行+エラー時Slack通知: `/Users/anicca/.openclaw/skills/naist-funds/scripts/scan.js`
- [ ] T017 [US1] `npm test -- tests/fetch.test.js tests/notify.test.js tests/scan.test.js` でGREEN確認
- [ ] T018 [US1] `DRY_RUN=1 node scripts/scan.js` をMac Mini上で実行して動作確認

**Checkpoint**: US1完了 — `DRY_RUN=1 node scripts/scan.js` でGrant一覧がstdoutに出力される

---

## Phase 4: User Story 2 — 申請手順の案内 (Priority: P2)

**Goal**: 「〇〇の申請方法は？」への質問にステップ形式で回答する。

**Independent Test**: `node scripts/guide.js "学振DC1"` を実行して手順がstdoutに出力される。

### Tests（TDD: 先に書いてREDを確認）

- [ ] T019 [P] [US2] `tests/guide.test.js` を作成（RED）: キーワードHIT→steps返却 / MISS→officialUrl案内の2シナリオ: `/Users/anicca/.openclaw/skills/naist-funds/tests/guide.test.js`

### Implementation

- [ ] T020 [US2] `scripts/guide.js` を実装（GREEN）: argv[2]→guides.jsonキーワード照合→HIT/MISS分岐→stdout出力: `/Users/anicca/.openclaw/skills/naist-funds/scripts/guide.js`
- [ ] T021 [US2] `npm test -- tests/guide.test.js` でGREEN確認
- [ ] T022 [US2] `node scripts/guide.js "学振DC1"` をMac Mini上で実行して手順が表示されることを確認

**Checkpoint**: US2完了 — guide.jsがキーワード検索でステップ回答を返す

---

## Phase 5: User Story 3 — 手動リフレッシュ (Priority: P3)

**Goal**: 「助成金情報を更新して」の指示でscan.jsを即時実行できる。

**Independent Test**: Mac Miniで `node scripts/scan.js` が正常に完了し、Slackに投稿される。

### Implementation

- [ ] T023 [US3] `SKILL.md` の `commands:` セクションに `refresh` コマンドを追加: `/Users/anicca/.openclaw/skills/naist-funds/SKILL.md`
- [ ] T024 [US3] Mac Mini上で `node scripts/scan.js` を実行してSlack実投稿を確認

**Checkpoint**: US3完了 — Slackから手動でscan.jsを起動できる

---

## Phase 6: SKILL.md + Cron 登録

**Purpose**: OpenClawにスキルとして統合し、週2回自動実行を有効化する。

- [ ] T025 `SKILL.md` を作成（YAML frontmatter + 実行手順 + commandsセクション）: `/Users/anicca/.openclaw/skills/naist-funds/SKILL.md`
- [ ] T026 Mac Mini上の `jobs.json` にcronジョブを追加: `15 9 * * 1,4` で `node scripts/scan.js` を実行
- [ ] T027 `openclaw gateway restart` でcronを有効化
- [ ] T028 `node scripts/scan.js` を本番（DRY_RUN未設定）で実行してSlack実投稿を確認

---

## Phase 7: Polish & Cross-Cutting

- [ ] T029 [P] `npm test` で全テスト（6ファイル）が全てGREENであることを最終確認
- [ ] T030 [P] quickstart.md の手順が全て通ることを確認: `/Users/anicca/.openclaw/skills/naist-funds/`
- [ ] T031 SKILL.mdのdescriptionがOpenClaw自動発動条件を満たすことを確認（tool-usage.md照合）

---

## Dependencies & Execution Order

### Phase Dependencies

| フェーズ | 依存 | ブロック |
|---------|------|---------|
| Phase 1: Setup | なし | Phase 2 |
| Phase 2: Foundational | Phase 1 | Phase 3, 4, 5 |
| Phase 3: US1 | Phase 2 | Phase 6 |
| Phase 4: US2 | Phase 2 | Phase 6 |
| Phase 5: US3 | Phase 2 | Phase 6 |
| Phase 6: SKILL.md+Cron | Phase 3 | Phase 7 |
| Phase 7: Polish | Phase 6 | なし |

### Parallel Opportunities

```bash
# Phase 1: T004, T005 は同時実行可
# Phase 2: T006, T007（テスト作成）は同時実行可
# Phase 3: T011, T012, T013（テスト作成）は同時実行可
# Phase 3: T014完了後 T015, T016 は順次
# Phase 4: Phase 2完了後、Phase 3と並行実行可
```

---

## Implementation Strategy

### MVP（US1のみ）

1. Phase 1: Setup 完了
2. Phase 2: Foundational 完了（全テストGREEN）
3. Phase 3: US1 完了（DRY_RUNで動作確認）
4. **STOP & VALIDATE**: `DRY_RUN=1 node scripts/scan.js` で出力確認
5. Phase 6: cron登録して自動化

### 完全実装（US1+2+3）

1. Phase 1 → 2 → 3（MVP）
2. Phase 4（US2）→ Phase 5（US3）
3. Phase 6（SKILL.md+cron）→ Phase 7（Polish）

---

## Notes

- TDD必須: テスト作成→`npm test`でRED確認→実装→GREEN確認の順を守る
- 全コマンドは `export PATH=/opt/homebrew/bin:$PATH` を付けてMac Mini上で実行
- DRY_RUN=1 でSlack投稿をスキップして動作確認
- commitはPhase単位で実行

---

## 実装完了記録（2026-02-24）

| フェーズ | 状態 | テスト |
|---------|------|--------|
| Phase 1: Setup | ✅ 完了 | - |
| Phase 2: Foundational | ✅ 完了 | 8/8 GREEN |
| Phase 3: US1（週次通知） | ✅ 完了 | 8/8 GREEN |
| Phase 4: US2（申請手順案内） | ✅ 完了 | 4/4 GREEN |
| Phase 5: US3（手動リフレッシュ） | ✅ 完了 | - |
| Phase 6: SKILL.md + Cron | ✅ 完了 | DRY_RUN確認済 |
| Phase 7: Polish | ✅ 完了 | 全20テスト GREEN |

Mac Mini実装パス: `/Users/anicca/.openclaw/skills/naist-funds/`
