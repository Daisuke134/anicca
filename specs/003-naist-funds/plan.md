# Implementation Plan: naist-funds

**Branch**: `003-naist-funds` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-naist-funds/spec.md`

## Summary

JSPS・JST・JFUNDから助成金情報をFirecrawlで取得し、週2回（月・木09:15 JST）Slackに新着通知するOpenClawスキル。
重複防止キャッシュ・申請手順ナレッジ・手動実行・Slack投稿を含む。Node.js + Jest + Firecrawl CLI。

## Technical Context

**Language/Version**: Node.js 18+
**Primary Dependencies**: Jest（devDependency）、Firecrawl CLI（外部コマンド、Mac Mini既存）
**Storage**: JSONファイル（`data/cache.json`, `data/guides.json`）
**Testing**: Jest（`jest.fn()`でFirecrawl CLI・Slack送信をモック）
**Target Platform**: Mac Mini（OpenClaw）
**Project Type**: CLI スキル（OpenClaw skill）
**Performance Goals**: Slack投稿完了まで30秒以内（FR-007・SC-005）
**Constraints**: Firecrawl CLI必須、DRY_RUN環境変数でSlack投稿スキップ可能
**Scale/Scope**: 週2回実行、想定Grant件数 10〜30件/実行

## Constitution Check

| ゲート | 判定 | 備考 |
|--------|------|------|
| Node.js統一 | ✅ PASS | 既存スキルと同じ言語 |
| TDD必須 | ✅ PASS | Jest、RED→GREEN→REFACTORで実装 |
| JSONファイルストレージ | ✅ PASS | 単一エージェント環境に適切 |
| Firecrawl CLI使用 | ✅ PASS | tool-usage.mdに従う |
| exec + openclaw message send | ✅ PASS | 既存パターン踏襲 |

違反なし。Complexity Trackingは不要。

## Project Structure

### Documentation (this feature)

```text
specs/003-naist-funds/
├── plan.md              # This file
├── research.md          # Phase 0 出力
├── data-model.md        # Phase 1 出力
├── quickstart.md        # Phase 1 出力
├── contracts/
│   └── skill-interface.md
└── tasks.md             # Phase 2 出力 (/speckit.tasks)
```

### Source Code（Mac Mini）

```text
/Users/anicca/.openclaw/skills/naist-funds/
├── SKILL.md
├── package.json
├── scripts/
│   ├── fetch.js         # Firecrawl → Grant[]
│   ├── notify.js        # Grant[] → Slack投稿（重複フィルタ込み）
│   ├── guide.js         # 申請手順検索・回答
│   ├── scan.js          # cronエントリポイント
│   └── utils/
│       ├── storage.js   # JSON読み書き（原子的）
│       └── slack.js     # openclaw message send ラッパー
├── data/
│   ├── cache.json       # 通知済みGrantキャッシュ
│   └── guides.json      # 申請手順ナレッジ
└── tests/
    ├── fetch.test.js
    ├── notify.test.js
    ├── guide.test.js
    ├── scan.test.js
    ├── storage.test.js
    └── slack.test.js
```
