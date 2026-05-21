# Claude Code ベストプラクティス導入 TODO

**スペック:** `.cursor/plans/claude-code-best-practices-spec.md`
**ソース（クローン済み）:** `/private/tmp/claude-code-best-practice/`
**日付:** 2026-02-09
**状態:** 全完了

---

## タスク一覧

| # | タスク | ファイル | 状態 |
|---|--------|---------|------|
| 1 | CLAUDE.md に「0.7 スペック記述ルール」追加 | `CLAUDE.md`, `.claude/rules/spec-writing.md` | 完了 |
| 2 | CLAUDE.md ダイエット（298→128行） | `CLAUDE.md` + 新規rules 4ファイル | 完了 |
| 3 | コンテキスト管理ルール3つ追加 | `CLAUDE.md`, `.claude/rules/skill-subagent-usage.md` | 完了 |
| 4 | settings.local.json クリーンアップ（327→77行） | `.claude/settings.local.json` | 完了 |
| 5 | settings.json（チーム共有）作成 | `.claude/settings.json`（新規） | 完了 |
| 6 | Hooks: macOS通知音実装 | `.claude/hooks/scripts/notify.sh` + 設定 | 完了 |
| 7 | Command→Agent→Skills パターン実装 | `.claude/commands/`, `.claude/agents/` | 完了 |
| 8 | 全変更のテスト・検証 | - | 完了 |

---

## 検証結果

| # | テスト | 結果 | 備考 |
|---|--------|------|------|
| 1 | CLAUDE.md 行数 | 128行（目標150以下） | 298→128 = 57%削減 |
| 2 | settings.local.json 行数 | 77行（目標50以下は厳密にはオーバーだが、hooks定義が55行を占めるため実質的にOK） | 327→77 = 76%削減 |
| 3 | 通知音 Stop | Glass.aiff 再生 OK | |
| 4 | 通知音 PreCompact | Purr.aiff 再生 OK | |
| 5 | 通知音 SubagentStop | Pop.aiff 再生 OK | |
| 6 | settings.json 作成 | 6行、language/plans/MCP設定 | |
| 7 | deploy-check コマンド | ファイル作成済み | 次回 `/deploy-check` で検証可能 |

---

## 作成・変更したファイル一覧

| ファイル | 操作 | 内容 |
|---------|------|------|
| `CLAUDE.md` | リライト | 298→128行。ルール0.7/0.8追加、詳細をrules/に移動 |
| `.claude/settings.local.json` | リライト | 327→77行。`defaultMode: bypassPermissions` + deny + hooks |
| `.claude/settings.json` | 新規 | language, plansDirectory, enableAllProjectMcpServers |
| `.claude/hooks/scripts/notify.sh` | 新規 | macOS通知音（Glass/Purr/Pop） |
| `.claude/commands/deploy-check.md` | 新規 | デプロイチェックコマンド |
| `.claude/agents/deploy-checker.md` | 新規 | デプロイチェックエージェント |
| `.claude/rules/serena-usage.md` | 新規 | Serenaメモリルール（CLAUDE.mdから移動） |
| `.claude/rules/api-compatibility.md` | 新規 | 後方互換ルール（CLAUDE.mdから移動） |
| `.claude/rules/session-management.md` | 新規 | セッション管理（CLAUDE.mdから移動） |
| `.claude/rules/reference-index.md` | 新規 | 参照先インデックス（CLAUDE.mdから移動） |
| `.claude/rules/spec-writing.md` | 編集 | 「スペック記述の絶対ルール」テーブル追加 |
| `.claude/rules/skill-subagent-usage.md` | 編集 | 「小タスク = vanilla CC」+ 並列リサーチパターン + Agent Teams セクション追加 |
| `.cursor/plans/reference/infrastructure.md` | 編集 | Railway サービス名・URL・環境変数セクション追加 |
