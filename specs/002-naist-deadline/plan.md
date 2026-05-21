# Implementation Plan: NAIST Deadline Management

**Branch**: `002-naist-deadline` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)

## Summary

NAISTの課題・締切をJSON永続ストレージで管理し、Slackで登録・確認・完了・自動リマインドを行うOpenClawスキル。Node.js + `@slack/web-api` + cronジョブで実装。既存のnaistスキル群（naist-calendar、naist-papers）と同一パターンを踏襲する。

## Technical Context

| 項目 | 値 |
|------|-----|
| **Language/Version** | Node.js 18+ |
| **Primary Dependencies** | `@slack/web-api`, `chrono-node`（自然言語日付パース）, `uuid` |
| **Storage** | JSON file（`/Users/anicca/.openclaw/skills/naist-deadline/data/deadlines.json`） |
| **Testing** | Jest |
| **Target Platform** | Mac Mini（anicca-mac-mini-1, macOS） |
| **Project Type** | OpenClaw agent skill（CLI スクリプト群） |
| **Performance Goals** | 各コマンド3秒以内に応答 |
| **Constraints** | 単一エージェント実行（ファイルロック不要）、Keychain不要（データは非機密） |
| **Scale/Scope** | 1ユーザー、最大数百件の締切 |

## Constitution Check

プロジェクトのconstitution.mdは未設定（テンプレートのまま）。CLAUDE.mdの絶対ルールを適用:

| ルール | チェック |
|--------|---------|
| ベストプラクティスに従う（オリジナル禁止） | ✅ 既存naistスキルパターンを踏襲 |
| TDDスタイル（テストファースト） | ✅ Jestテストを先に書く |
| 実際に実行して確認するまで完了禁止 | ✅ Mac Mini上でlive testを実施 |

## Project Structure

### Documentation (this feature)

```text
specs/002-naist-deadline/
├── spec.md              ✅ 完了
├── plan.md              ✅ このファイル
├── research.md          ✅ 完了
├── data-model.md        ✅ 完了
├── contracts/
│   └── skill-interface.md  ✅ 完了
├── checklists/
│   └── requirements.md  ✅ 完了
└── tasks.md             → /speckit.tasks で生成
```

### Source Code (Mac Mini 上のデプロイ先)

```text
/Users/anicca/.openclaw/skills/naist-deadline/
├── SKILL.md                    # OpenClaw スキル定義
├── package.json
├── scripts/
│   ├── register.js             # 締切を追加する
│   ├── list.js                 # 締切一覧を表示する
│   ├── complete.js             # 締切を完了にする
│   ├── scan.js                 # cronから呼ばれるリマインドスキャン
│   └── utils/
│       ├── storage.js          # JSON読み書き（原子的書き込み）
│       └── date.js             # 自然言語日付パース（chrono-node）
├── data/
│   └── deadlines.json          # 永続ストレージ
└── tests/
    ├── storage.test.js
    ├── date.test.js
    ├── register.test.js
    ├── list.test.js
    ├── complete.test.js
    └── scan.test.js
```

**Structure Decision**: Option 1（Single project）。OpenClawスキルはシングルNode.jsパッケージ。既存naistスキルのディレクトリ構造と統一。

## Phase 0: Research ✅

完了。詳細は [research.md](./research.md) 参照。

主要決定:
- Node.js + Jest + chrono-node
- JSON file storage（原子的書き込み）
- Cron: `0 * * * *`（毎時）+ `0 8 * * *`（朝8時ダイジェスト）

## Phase 1: Design ✅

完了。

- [data-model.md](./data-model.md): Deadline エンティティ、JSONスキーマ、リマインド判定ロジック
- [contracts/skill-interface.md](./contracts/skill-interface.md): 全スクリプトの入出力インターフェース

## Phase 2: TDD Implementation（/speckit.tasks → /speckit.implement）

```
SKILL.md（スキル定義）
    ↓
tests/ を先に書く（RED）
    ↓
scripts/ を実装して全テストGREEN
    ↓
Mac Mini にデプロイ
    ↓
Slackで実際にテスト（live test）
    ↓
cronジョブ登録
    ↓
完了 ✅
```

## 依存関係

| 依存 | 理由 |
|------|------|
| `@slack/web-api` | Slack投稿（既存スキルと同じ） |
| `chrono-node` | 「明日」「来週月曜日」等の自然言語日付パース |
| `uuid` | Deadline IDの生成 |
| `jest` | テストフレームワーク |
