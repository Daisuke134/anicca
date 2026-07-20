# PLAN: context floor deep reduction (134.5k → ≤80k startup)

Executor = codex(Sol)。sandbox は workspace-write なので **repo 外のファイルは直接書くな**。
成果物 = repo 内 `floor-reduction/` に patch 群 + `apply.sh` + `verify.sh`。適用と最終検証は Fable が行う。
質問は agmsg（send.sh floor2 sol-codex fable-main '<質問>'）。完了したら同経路で DONE。

## 確定済み事実（調査済み。再調査不要）

1. `permissions.deny` の **bare tool 名**（例 `"Workflow"`）は schema を context から除去する。scoped（`Bash(rm *)`）は実行拒否のみで schema は残る。出典: code.claude.com/docs/en/permissions.md "As a deny rule, both forms remove the tool from Claude's context."
2. `includeGitInstructions: false` で built-in git instructions + git status snapshot が system prompt から消える（~2.2k）。出典: settings.md
3. `.claude/rules/*.md` に frontmatter `paths: [<glob>]` を付けると起動時ロードされず、該当ファイルを読む時のみロード。出典: memory.md "Path-scoped rules trigger when Claude reads files matching the pattern"
4. serena は `~/.serena/serena_config.yml` の `excluded_tools: []`（global 除外）で tool を削れる。`fixed_tools` は排他。出典: oraios/serena serena_config.template.yml
5. SessionStart hook の stdout は毎 session context に注入される。現在 enabled 分の安全実行実測 ~1.3k tok + cozempic/caveman 等未実測分。
6. plugin agent の完全 unload は plugin 単位 disable のみ（公式）。`Agent(name)` deny が listing から消すかは未検証 — 今回は使わない。

## 現状（実測、新session /context）

System prompt 28.9k / System tools 35.1k / MCP(serena) 10.5k / Custom agents 29.1k / Memory 22.1k / Skills 2.9k = ~128.6k + messages。

## タスク（全部 MUST。floor-reduction/ 配下に作る）

### T1. built-in tools deny リスト
`floor-reduction/settings-user-patch.json` に、~/.claude/settings.json へ merge する JSON を書く:
- `permissions.deny` へ追加する bare tool 名: `Workflow`, `DesignSync`, `CronCreate`, `CronDelete`, `CronList`, `Monitor`, `NotebookEdit`, `ReportFindings`, `ScheduleWakeup`, `LSP`, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `ReadMcpResourceDirTool`, `EnterPlanMode`, `ExitPlanMode`, `EnterWorktree`, `ExitWorktree`, `PushNotification`, `AskUserQuestion`
  - **除外（deny するな）**: Read, Write, Edit, Bash, Glob, Grep, Agent, Skill, TaskCreate/Get/List/Update/Output/Stop, SendMessage, WebSearch, WebFetch（CLAUDE.md で禁止だが harness 動作に干渉しない、触らない）
- `includeGitInstructions: false` も同 patch に含める。
- 既存 ~/.claude/settings.json を read して**既存キーを壊さない merge 手順**を apply.sh に書く（jq 使用、適用前に .bak 保存）。

### T2. serena 削減
`floor-reduction/serena-excluded-tools.yml` に excluded_tools 推奨リストを書く。残す: find_symbol, get_symbols_overview, replace_content, replace_in_files, find_referencing_symbols, replace_symbol_body, insert_after_symbol, insert_before_symbol, get_diagnostics_for_file。除外: memory系5本(list/read/write/edit/delete/rename_memory), onboarding, initial_instructions, find_declaration, find_implementations, rename_symbol, safe_delete_symbol。apply.sh に ~/.serena/serena_config.yml への適用手順（.bak + yq or python）。

### T3. CLAUDE.md 群の paths 化（削除ではなく移設）
対象と移設先（`.claude/rules/<name>.md` + frontmatter paths）:
- project CLAUDE.md: 「開発（GLVS…）」表 → rules/vcsdd-flow.md (paths: ["docs/superpowers/**"]) / 「ブランチ & デプロイ」+ iOS 節 → rules/ios-deploy.md (paths: ["aniccaios/**"]) / colony SSOT 表 → rules/colony.md (paths: ["docs/STATUS.md", "docs/superpowers/specs/*colony*", "docs/superpowers/specs/*x402*"])
- ~/.claude/CLAUDE.md はDaisの規律集 = **本文を勝手に削るな**。ただし「フロントエンド作成順序」「ツール既定表のうち低頻度行」「VCSDD token上限詳細」を `~/.claude/rules/` へ paths 付きで移す**提案 diff** を `floor-reduction/global-claude-md.diff` として作る（適用判断は Fable）。
- MEMORY.md: 「金」「ブラウザ / OS」「ツール / 統合」セクションを `memory/` 側の個別ファイル参照に落とし、索引から外す提案 diff を `floor-reduction/memory-md.diff` に作る（適用判断は Fable）。
- repo 内 rules ファイル（.claude/rules/*.md）は codex が直接作成してよい。CLAUDE.md 本文から該当節を消して「→ .claude/rules/x.md」1行に置換するのも repo 内なので直接やってよい。

### T4. SessionStart hook 痩身
`floor-reduction/hooks-audit.md`: ~/.claude/settings.json + project settings の SessionStart hook 全列挙、各 stdout 実測 tok、削減提案（静的テキストを出すだけの hook は rules/paths へ移す or 出力を1行化）。**hook設定の書き換え patch は作るが適用は Fable**。

### T5. apply.sh / verify.sh
- `floor-reduction/apply.sh`: T1/T2 の適用（.bak 必須）+ T3 repo 内変更は既に direct + T4 は printf で「manual」と出す。
- `floor-reduction/verify.sh`: `claude -p "/context" --output-format text` で合計値を取り、134.5k との差分を表示。目標 ≤80k、80k超なら残り候補を出力。
- 冪等（2回実行しても壊れない）。

## done 条件
- floor-reduction/ に上記5成果物が揃い、apply.sh が shellcheck エラーなし（`shellcheck` なければ `bash -n`）
- repo 内 T3 変更（project CLAUDE.md スリム化 + .claude/rules/*.md 新設）が完了
- python3 -m pytest は不要（テスト対象外）。JSON/YAML は `jq`/`python3 -c` で構文検証済み
- agmsg で DONE 報告
