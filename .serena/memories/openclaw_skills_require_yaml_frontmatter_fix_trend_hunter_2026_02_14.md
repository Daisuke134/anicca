# OpenClaw スキルには YAML frontmatter が必須

**日付**: 2026-02-14

## ルール

OpenClaw skill discovery は `SKILL.md` に **YAML frontmatter**（最低 `name` と `description`）が必要。frontmatter がないとディレクトリは存在してもインデックスされず、モデルがスキル指示を受け取れない。

## 過去の症状

- `openclaw skills list` にスキルが表示されない
- エージェントが `./run_trend_hunter.sh` を間違ったcwdから実行しようとして失敗

## 対処

- 全スキルの `SKILL.md` に YAML frontmatter（`name`, `description`, `metadata` as single-line JSON）を追加
- `{baseDir}` を相対パス実行時に使用

## 参照

OpenClaw docs: Skills require YAML frontmatter; metadata must be single-line JSON; `{baseDir}` can be used in instructions.
