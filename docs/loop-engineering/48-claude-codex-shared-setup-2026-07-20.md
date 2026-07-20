# Claude/Codex 設定共有 + cloud 移行調査（2026-07-20）

## 確定事実（出典付き）

| 事実 | 出典 |
|---|---|
| Claude Code は AGENTS.md を読まない。CLAUDE.md に `@AGENTS.md` import か symlink が公式手 | code.claude.com/docs/en/memory#agents-md "Claude Code reads CLAUDE.md, not AGENTS.md" |
| Codex は global→repo root→CWD の AGENTS.md を連結、近い階層が後勝ち | learn.chatgpt.com/docs/agent-configuration/agents-md |
| **Codex はネイティブ Skills 対応**（Agent Skills open standard、SKILL.md 共通）。Codex=`.agents/skills`/`~/.agents/skills`、Claude=`.claude/skills`/`~/.claude/skills`、両方 symlink 追跡 | learn.chatgpt.com/docs/build-skills + code.claude.com/docs/en/skills |
| 実例: HF Transformers は正本 `.ai/skills` から両方へ symlink | github.com/huggingface/transformers Makefile L76-84 |
| Rulesync (dyoshikawa/rulesync, 1,246★, v14.1.0, 当日更新): `.rulesync/` 正本から rules/MCP/commands/subagents/skills/hooks/permissions を Claude+Codex 両形式へ generate/import | github.com/dyoshikawa/rulesync |
| Ruler (intellectronica/ruler, 2,811★): 単純だが skills experimental、hooks/permissions 変換なし | github.com/intellectronica/ruler |
| Claude Code on the web: GitHub App 接続、fresh clone VM (4vCPU/16GB)、repo 内 CLAUDE/rules/skills/.mcp のみ移送。iOS アプリの Code タブから開始・steer 可 | code.claude.com/docs/en/claude-code-on-the-web |
| Codex cloud: GitHub 接続、secrets は setup 時のみ、agent phase の internet 既定 OFF | learn.chatgpt.com/docs/cloud |

## 裁定（Fable）

**Rulesync 採用、段階導入**:
- Phase 1（今）: `rulesync import --targets claudecode` で既存資産を `.rulesync/` に取り込み、**generate は codexcli target のみ**（AGENTS.md / .codex/config.toml / .agents/skills）。手練りの CLAUDE.md 群は上書きさせない（claudecode generate は diff gate を整備してから）。
- Phase 2: 生成物 diff gate + version pin で claudecode 側も一正本化。
- skills 共有は symlink（`~/.agents/skills` → `~/.claude/skills`）が最速。Codex ネイティブ対応済みなので AGENTS.md への焼き込み不要。
- Codex が WebSearch に流れる問題: AGENTS.md に「ツール既定表」（firecrawl CLI / ctx7 / x-search-cdp / gh）を焼く。これが今回の主目的。

## firecrawl 復活（2026-07-20 実測）
`firecrawl scrape https://example.com` 成功（v1.6.2, /opt/homebrew/bin/firecrawl）。credit 切れ解消 → web 取得の既定を firecrawl に戻す（crwl は fallback）。

## 実施済み（2026-07-20 実測）
- repo AGENTS.md 作成（ツール既定: firecrawl/ctx7/x-search-cdp/gh、WebSearch禁止）+ push 済み。
- `~/.codex/AGENTS.md`（global）にも同内容適用（setup-parity.sh、冪等確認済み）。
- `~/.agents/skills` へ Claude user skills 9個を symlink（計66 skill が Codex から可視）。
- ~/.openclaw 資産 push 完了（private repo anicca-dais）。**secrets 掃除実施**: browser/ profile 全体・auth-state.json×2・playwright Cookies/Login Data×8 を untrack + .gitignore 恒久化（ファイルはローカル残存、gitleaks 0 leaks 確認）。

## Round 2 研究（articles + repo 深掘り、2026-07-20）
- 記事の多数派: AGENTS.md を正本にし CLAUDE.md は `@AGENTS.md` import か symlink（AGYN / SSW / RuleSell。公式 memory docs も同手を明記）。
- HF Transformers 実例: root AGENTS.md/CLAUDE.md 両方が `.ai/AGENTS.md` への symlink、skills は Makefile 生成。
- **裁定 = rulesync@14.1.0 固定導入**。理由: import で既存 CLAUDE.md/.claude/rules/.claude/skills/.mcp.json を取り込め、Codex 側 AGENTS.md/.agents/skills/.codex/config.toml まで生成できる唯一の tool。Ruler(2,811★) は import 無し・global 生成不向きで棄却（ただし低churn は魅力）。
- リスク: rulesync は高速 major churn（30日で 25 releases、breaking 6）+ **無確認上書き** → version pin + 一時 HOME で dry-run diff → 本適用、の gate 必須。
- 自分が間違う最有力筋: 共有対象が rules+skills だけなら HF 型 symlink の方が総コスト小。MCP/paths 変換が要らなくなったら symlink へ後退してよい。
- 健全性実測: rulesync 1,246★/584 commits(30d)/25 releases、ruler 2,811★/67 commits/2 releases。

## cloud 移行の含意
- mobile 操作: Claude iOS Code タブ（cloud sandbox）が既に使える。repo に CLAUDE.md/rules/skills が push されていれば cloud session でも同じ規律で動く = **STEP 2（GitHub に全部上げる）が cloud 移行の実体**。
- Mac Mini へは Tailscale SSH が phone からも可能。loops は当面 Mac Mini 常駐で問題なし。
