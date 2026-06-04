# Cron Rat-Proof Architecture (Anicca / OpenClaw)

| meta | value |
|---|---|
| date | 2026-06-04 JST |
| author | Claude (per Dais) |
| triggering incident | 2026-06-04 18:20 JST Slack #metrics: `unknown MCP server 'openclaw'` + `実行環境が ない` |
| scope | OpenClaw cron jobs (234) on Mac Mini, runtime store `~/.openclaw/` |
| out of scope | iOS app crons, Railway crons, gateway internals beyond config |

## 1. Problem (= 実物 root cause、検証済み)

### 1.1 何が起きたか

| Cron | Slack 出力 | 実 cause |
|---|---|---|
| anicca-earn-bounty (1730c972…) | `resources/read failed: unknown MCP server 'openclaw'` | Isolated Codex sandbox に MCP server 一切非接続。 prompt "Read SKILL.md" を読んで `read_mcp_resource` を call、 100% fail |
| anicca-wallet-balance (d4036615…) | `このセッションでは bash を実行して待機するための実行環境がありません` | 同 sandbox の gpt-5.4-mini が `exec_command` を skip して text refusal を返した (hallucination) |

### 1.2 アーキ違反 (= 真因)

| 観測 | 数値 |
|---|---|
| 全 cron 数 | 234 |
| payload.kind = "agentTurn" | 234 (100%) |
| payload.kind = "systemEvent" | 0 |
| sessionTarget = "isolated" | 234 |
| sessionTarget = "main" | 0 |
| `Read ~/.openclaw/skills/<X>/SKILL.md and execute` 形 message | 64 (= MCP read trap) |
| 18:20 batch fire 成功率 | 5/7 = 71% (= coin flip) |

つまり Anicca が持つ **5 つ の cron 実行 path のうち最弱 1 つ** に 234 cron 全部押し込んでいる。

### 1.3 5-path 全 inventory (= 検証済 capability)

| # | Path | 実体 | LLM 関与 | 既存 cron で 使用 | 検証 source |
|---|---|---|---|---|---|
| 1 | OpenClaw cron `kind="systemEvent"` → main session | `~/.openclaw/skills/_dispatcher/*` + main session の MCP plugin (filesystem, serena, codegraph, gmail, slack, agentmail, computer-use, linear) | yes、 main session 重 LLM | 0 件 | `dist/server-cron-i5IplaUe.js` の `enqueueSystemEvent` + `runHeartbeatOnce`、 `dist/openclaw-tools-BUQsixTe.js` の `CRON_PAYLOAD_KINDS` |
| 2 | OpenClaw cron `agentTurn` (現状) + `codex exec` wrapper | `agentTurn` prompt が `codex exec --json --skip-git-repo-check -s danger-full-access "<task>"` を bash で起動。 codex exec は `~/.codex/config.toml::mcp_servers` 全部 attach した非対話 agent | yes、 ただし full agent | 0 件 | `codex exec --help` + OpenAI 公式 [Non-interactive mode](https://developers.openai.com/codex/noninteractive) |
| 3 | Slack tail → cron re-fire | `slack_search_public` + `openclaw cron run <id>` | refusal 検出時のみ | 0 件 | `dist/cron-cli--jnvaeLg.js`、 Slack MCP `slack_search_public` |
| 4 | 別 model 直 API curl | `curl POST api.anthropic.com/v1/messages` + `curl POST api.deepseek.com/v1/chat/completions` (key in `~/.openclaw/.env`) | yes、 model 切替 | 0 件 | Anthropic / DeepSeek 公式 API |
| 5 | macOS launchd plist | `~/Library/LaunchAgents/ai.anicca.<cron>.plist` + bash + Slack webhook curl | **no** | 既存 (gateway / agentmail-replier 等の services 用) | `ps aux | grep launchctl`、 `~/.openclaw/services/*` 既存 plist |

## 2. Target Architecture

### 2.1 Path-selection matrix (= どの cron がどの path を使うか)

| Cron 性質 | Default path | 理由 | Fallback chain |
|---|---|---|---|
| 軽量 deterministic bash (= wallet-balance, fuel-broker, disk-janitor, mail-triage 等) | **Path 1 systemEvent** | main session 経由で full tool stack 使える + bash 1 行で済む | Path 2 → Path 5 |
| 重 multi-step LLM 判断 (= earn-bounty solve, content-creator, analytics-interpretation 等) | **Path 2 codex exec wrapper** | full Codex agent + all MCP plugins、 model robust | Path 4 (Anthropic 直) → Path 5 |
| revenue-critical (= 着金、 入金、 PR open、 商談) | **Path 1 + auto Path 5** | systemEvent 失敗時に launchd 自動切替で 0 抜け | — |
| pure data fetch (no LLM 判断不要) | **Path 5** (launchd 直) | LLM coin flip 排除、 確定実行 | — |

### 2.2 Self-heal (= anicca-cron-doctor、 nightly 03:00 JST)

| Phase | 判定 | アクション |
|---|---|---|
| L1 prompt lint | jobs.json に `Read ~/.openclaw/skills/.../SKILL.md` pattern 残存 | direct-bash 形に auto-rewrite → commit → push |
| L2 path lint | jobs.json に `Path 1-5 mapping` に違反する cron | 該当 cron の kind / sessionTarget を canonical 化 |
| L3 refusal detector | Slack #metrics 24h で refusal string (`unknown MCP`, `実行環境が ない`, `shell tool が ない`, `実行できません`) 検出 | `openclaw cron run <id>` で即再 fire (Path 3) |
| L4 streak monitor | 同 cron が L3 で 3 連続 refuse | Path 4 (= 別 model 直 API) に bash 化 |
| L5 hard escalate | 同 cron が L4 で 5 連続 refuse OR revenue-critical 分類 | Path 5 launchd plist 自動生成 + OpenClaw cron disable |
| L6 daily report | 全 phase 結果 | Slack #metrics に table `fixed=N retried=M migrated=K` |

## 3. Verification Matrix (= acceptance criteria、 5 条全 MUST)

| AC# | 何 | 判定方法 | 期限 |
|---|---|---|---|
| AC-1 | anicca-wallet-balance を Path 1 (systemEvent) で fire し Slack #metrics に実 JSON (address + usdc_balance) が来る | `openclaw cron run d4036615… --wait --expect-final` の summary に `"usdc_balance"` 含む | 本 session |
| AC-2 | anicca-earn-bounty を Path 1 で fire し Slack に heartbeat scan 結果 (= "scan / select / solve" のどれか出力) が来る | 同上、 summary に `scan` 含む or scripts/scan.sh 出力 | 本 session |
| AC-3 | 24h 監視で AC-1 と AC-2 が **少なくとも 1 自然 fire で再現** | Slack #metrics の scheduled fire の Slack 出力 | next session (= 24h 後 verify) |
| AC-4 | anicca-cron-doctor cron が 03:00 JST に登録され、 1 回目の fire で `fixed=0 retried=0 migrated=0` (= baseline OK) を post | `openclaw cron list \| grep anicca-cron-doctor` + Slack 出力 | 次 session |
| AC-5 | spec & plan が `docs/superpowers/specs/` + `docs/superpowers/plans/` に commit + push 済 | `git log --oneline docs/superpowers/` | 本 session |

## 4. Risks

| Risk | 軽減策 |
|---|---|
| systemEvent が main session の budget を食い潰す (= heartbeat と競合) | timeoutSeconds を低 (= 60-300) + payload.message を 100 字以下に圧縮 |
| launchd 化した cron が openclaw cron list に出ず重複 fire | jobs.json で該当 cron を `enabled: false` に set、 anicca-cron-doctor が verify |
| `codex exec` の Anthropic key を main process env に残すと leak | `~/.openclaw/.env` を `set -a; . ~/.openclaw/.env; set +a; codex exec ...; unset ANTHROPIC_API_KEY` で subshell スコープ |
| 234 cron 全部 path migrate で main session が詰まる | 段階展開: 本 session で 2 cron のみ、 24h verify、 batch 化 |

## 5. Out-of-scope (今 session ではやらない)

- OpenClaw 本体への PR (model field honor / refusal-as-error 分類変更)
- 残り 232 cron の自動 path migrate (= anicca-cron-doctor 経由で 1 週間かけて)
- iOS / Railway 側 cron との統合

## 6. References

| 引用 | URL / path |
|---|---|
| OpenAI Codex non-interactive 公式 | https://developers.openai.com/codex/noninteractive |
| Codex exec headless mode | https://deepwiki.com/openai/codex/4.2-headless-execution-mode-(codex-exec) |
| Codex Automations | https://developers.openai.com/codex/app/automations |
| OpenClaw `CRON_PAYLOAD_KINDS` enum | `/opt/homebrew/lib/node_modules/openclaw/dist/openclaw-tools-BUQsixTe.js` |
| OpenClaw systemEvent → main session routing | `/opt/homebrew/lib/node_modules/openclaw/dist/server-cron-i5IplaUe.js` (`enqueueSystemEvent`) |
| HARD RULE #-1 (試行先、 refuse 後) | `CLAUDE.md` |
| HARD RULE #0 (SDD mandatory) | `CLAUDE.md` |
| 18:20 incident rollouts | `~/.openclaw/agents/anicca/agent/codex-home/sessions/2026/06/04/rollout-2026-06-04T18-20-{50,55}-*.jsonl` |
