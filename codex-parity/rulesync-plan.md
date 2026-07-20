# Rulesync Phase 1 plan

Rulesync は `14.1.0` に完全固定する。Phase 1 では既存 Claude Code 資産を `.rulesync/` に import し、生成先は Codex CLI のみに限定する。Claude Code 側は生成しない。

## 根拠

- ソース: [Rulesync CLI Commands](https://rulesync.dyoshikawa.com/reference/cli-commands.html) / 核心の引用: “Import existing configurations (to .rulesync/rules/ by default)”
- ソース: [Rulesync CLI Commands](https://rulesync.dyoshikawa.com/reference/cli-commands.html) / 核心の引用: “Dry run: show changes without writing files”
- ソース: [Rulesync CLI Commands](https://rulesync.dyoshikawa.com/reference/cli-commands.html) / 核心の引用: “Check if files are up to date (for CI/CD pipelines)”

## Phase 1 手順（今回は実行しない）

1. clean worktree または専用 branch で開始し、`npx --yes rulesync@14.1.0 --version` が 14.1.0 であることを記録する。
2. 既存設定のスナップショットを取り、`npx --yes rulesync@14.1.0 import --targets claudecode` を実行する。
3. `.rulesync/` の import 差分を review し、秘密情報・生成物・欠落がないことを確認して commit する。
4. 書込み前に `npx --yes rulesync@14.1.0 generate --dry-run --targets codexcli` を保存・review する。
5. 許可パスを `AGENTS.md`、`.codex/`、`.agents/` に限定して `npx --yes rulesync@14.1.0 generate --targets codexcli` を実行する。
6. 下記 diff gate を通過させ、生成物だけを commit する。`generate --targets claudecode` は Phase 2 まで禁止する。

## Diff gate

生成前に `git status --porcelain` を保存し、生成後は次をすべて満たさなければ失敗とする。

1. `git diff --name-only` の全パスが allowlist（`AGENTS.md`, `.codex/**`, `.agents/**`）内である。
2. `CLAUDE.md`, `.claude/**`, secrets、hooks、permissions に変更がない。
3. `git diff --check` が成功し、人間が `git diff -- AGENTS.md .codex .agents` を review する。
4. 同じ pin と引数で `npx --yes rulesync@14.1.0 generate --check --targets codexcli` が成功する。
5. もう一度 generate して `git diff` が変化しない（冪等性）。

CI 化する場合も version range や `latest` は使わず、`rulesync@14.1.0` と `generate --check --targets codexcli` を固定する。Phase 2 で Claude Code 側を対象に加える前に、同じ allowlist を明示的に拡張して review する。
