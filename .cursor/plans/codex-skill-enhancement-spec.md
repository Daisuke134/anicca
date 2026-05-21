# Codex スキル拡張 & skill-authoring 警告追記スペック

## 概要（What & Why）

Nenene01 の Zenn 記事シリーズから得た知見を2点導入する:

1. **汎用 `/codex` スキル新規作成**: 現在の `codex-review` はレビューゲート専用（反復修正ループ付き）。それとは別に、Codex CLI を「セカンドオピニオン」として汎用的に使える `/codex` スキルを作成する。設計相談・バグ調査・文章校閲など、read-only で気軽に聞ける用途。
2. **skill-authoring.md に description 禁止表現を追記**: 「プロアクティブに使用」と description に書くとプロセス増殖を招く。Nenene01 が実際に Mac フリーズを経験した教訓。

## 受け入れ条件

| # | 条件 | テスト方法 |
|---|------|-----------|
| 1 | `/codex` スキルが存在し、`codex exec --sandbox read-only` を実行する | ファイル存在確認 + SKILL.md 内容確認 |
| 2 | `/codex` は `codex-review` と別スキル（共存する） | 両方のディレクトリが存在 |
| 3 | `/codex` の description が skill-authoring.md のフォーマットに準拠 | description フォーマット確認 |
| 4 | `/codex` は4モード対応（レビュー / 設計相談 / バグ調査 / 校閲） | SKILL.md 内容確認 |
| 5 | skill-authoring.md に「description 禁止表現」セクションが追記されている | ファイル内容確認 |
| 6 | 禁止表現に「プロアクティブに使用」「自動的に使用」が含まれている | ファイル内容確認 |
| 7 | tool-usage.md のスキル自動適用テーブルに `/codex` が追加されている | ファイル内容確認 |

## As-Is / To-Be

### As-Is

| 項目 | 現状 |
|------|------|
| Codex スキル | `codex-review` のみ（レビューゲート専用、反復修正ループ付き） |
| 汎用 Codex 相談 | 手動で `codex exec` を実行するしかない |
| skill-authoring.md | description 禁止表現の記載なし |

### To-Be

| 項目 | 変更後 |
|------|--------|
| Codex スキル | `codex-review`（レビューゲート）+ `codex`（汎用セカンドオピニオン） |
| 汎用 Codex 相談 | `/codex <相談内容>` で即実行 |
| skill-authoring.md | description 禁止表現セクション追加（プロセス増殖防止） |

## テストマトリックス

| # | To-Be | テスト名 | 検証方法 |
|---|-------|----------|----------|
| 1 | `/codex` スキル存在 | ファイル確認 | `.claude/skills/codex/SKILL.md` の存在 |
| 2 | description フォーマット準拠 | 目視 | 三人称 + Use when + trigger キーワード |
| 3 | 4モード記載 | 目視 | レビュー / 設計相談 / バグ調査 / 校閲 |
| 4 | `codex-review` と共存 | ファイル確認 | 両ディレクトリ存在 |
| 5 | skill-authoring.md 禁止表現 | 目視 | セクション存在 + 具体例 |
| 6 | tool-usage.md 更新 | 目視 | `/codex` 行追加 |

## 境界

| やること | やらないこと |
|---------|-------------|
| `/codex` スキル新規作成 | `codex-review` の変更 |
| skill-authoring.md 追記 | 既存スキルの description 書き換え |
| tool-usage.md テーブル追記 | CLAUDE.md の変更 |

## 実行手順

```bash
# 確認
ls .claude/skills/codex/SKILL.md
ls .claude/skills/codex-review/SKILL.md
cat .claude/rules/skill-authoring.md | grep "プロアクティブ"
cat .claude/rules/tool-usage.md | grep "/codex"
```

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 結論 | Maestro E2E不要（設定ファイルの追加・編集のみ） |
