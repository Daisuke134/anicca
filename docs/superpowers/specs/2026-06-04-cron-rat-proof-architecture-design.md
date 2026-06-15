# Cron Rat-Proof Architecture (Anicca / OpenClaw) — v2 OpenClaw-all-the-way

| meta | value |
|---|---|
| date | 2026-06-04 (v1) → 2026-06-04 21:50 JST (v2 pivot) |
| author | Claude (per Dais) |
| triggering incident | 2026-06-04 18:20 JST Slack #metrics: `unknown MCP server 'openclaw'` + `実行環境が ない` |
| scope | OpenClaw cron jobs (172 enabled) on Mac Mini, runtime store `~/.openclaw/` |
| out of scope | iOS app crons, Railway crons, gateway internals beyond config |
| **v2 directive (Dais 21:48 JST)** | **OpenClaw all the way. No launchd. No macOS clock. Every cron MUST go through OpenClaw gateway, period.** |

## 1. Problem (= 実物 root cause、検証済み)

### 1.1 何が起きたか (2026-06-04 18:20 JST incident)

| Cron | Slack 出力 | 実 cause |
|---|---|---|
| anicca-earn-bounty | `unknown MCP server 'openclaw'` | Isolated Codex sandbox に MCP server 一切非接続。 prompt "Read SKILL.md" を読んで `read_mcp_resource` を call、 100% fail |
| anicca-wallet-balance | `bash を実行して待機する実行環境がありません` | 同 sandbox の gpt-5.4-mini が `exec_command` を skip して text refusal を返した |

### 1.2 アーキ違反 (= 真因)

| 観測 | 数値 |
|---|---|
| 全 cron 数 | 172 enabled |
| payload.kind = "agentTurn" | 172 (100%) — そのまま OpenClaw 正規経路 |
| payload.message に `Read ~/.openclaw/skills/<X>/SKILL.md` indirection を含む | 60 (= MCP read trap risk) |
| 18:20 batch fire 成功率 | 5/7 = 71% (= LLM tool-call coin flip) |

つまり cron の `payload.message` が「Read SKILL.md and execute…」 という indirection prompt のために、 isolated Codex の gpt-5.4-mini が `read_mcp_resource` (= MCP read tool) を選択してしまう。 そして MCP server がアタッチされていないので 100% fail する。

## 2. Solution — 2 paths (= OpenClaw cron + wrapper)

すべての cron は OpenClaw cron (= `payload.kind: agentTurn`, `sessionTarget: isolated`) で発火する。 cron の `payload.message` を **1 行の `exec` 命令 + `_dispatcher` wrapper bash invocation** に統一する。 LLM は `exec_command` を 1 回だけ呼べばよい。

### 2.1 2 paths (= 軽量 vs LLM 要)

| # | Path | Cron payload.message | 実体 | 使いどころ |
|---|---|---|---|---|
| 1 | **cron-bash.sh wrapper** | `bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-bash.sh <skill>/scripts/<x>.sh` | 純 bash 実行 → tail を Slack chat.postMessage (SLACK_BOT_TOKEN) | deterministic data fetch (wallet, mail triage, disk, etc) — LLM 判断不要 |
| 2 | **cron-codex.sh wrapper** | `bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-codex.sh <skill>` | `codex exec --json -s danger-full-access --cd $SKILL` で full Codex agent + MCP plugins を非対話起動 → run.sh をその agent が呼ぶ | LLM 判断要 (bounty solve, content gen, multi-step plan) |

### 2.2 共通テンプレート (= cron prompt)

```
exec で 必ず 1 行 だけ 実行 する。
「shell tool が ない」 / 「MCP server が ない」 等 の 言い訳 禁止 — 必ず exec_command を 1 回 は 呼ぶ。
stdout は Slack に 自動 で 出る。

bash $HOME/.openclaw/skills/_dispatcher/scripts/<wrapper>.sh <arg>
```

これにより gpt-5.4-mini の判断負荷が「`exec_command` を 1 回呼ぶか否か」 だけになり、 refusal 率が劇的に下がる。 refuse しても `_dispatcher` の中身は同じなので、 cron-doctor が L3 retry で次の coin flip を引かせる。

### 2.3 wrapper 実装 (= `~/.openclaw/skills/_dispatcher/`)

| ファイル | 役割 |
|---|---|
| `SKILL.md` | 使用法 + 2 path 仕様 |
| `scripts/cron-bash.sh <skill>/scripts/<x>.sh` | timeout 300s で bash 実行、 exit code 保持、 tail 1500B を Slack chat.postMessage |
| `scripts/cron-codex.sh <skill> [extra]` | timeout 1500s で `codex exec --json -s danger-full-access --cd $SKILL_DIR "<prompt>"`。 OPENAI_API_KEY を ~/.codex/auth.json から fallback inject (401 対策)、 stderr+stdout を tail して Slack 投稿 |

### 2.4 Self-heal (= `~/.openclaw/skills/anicca-cron-doctor/`、 OpenClaw cron 03:00 JST nightly)

| Phase | 判定 | アクション |
|---|---|---|
| L1 prompt lint | `payload.message` に `Read ~/.openclaw/skills/<X>/SKILL.md and execute` (strict regex) + context marker 無し | `openclaw cron edit --message` で wrapper 形に rewrite |
| L2 path lint | 全 enabled cron を `pure_data / llm_required / revenue_critical` に分類 | flag-only、 auto-action なし |
| L3 refusal detector | Slack #metrics 24h scrape で `unknown MCP \| 実行環境.*ない \| shell tool.*ない \| 実行できません` 等を grep | 該当 cron を `openclaw cron run <id>` で即再 fire (rate-limit 1h per cron) |
| L4 streak monitor | per-cron consecutive refusal counter (`data/refusal-streak.json`) | streak ≥ 3 で alert log |
| L5 hard escalate | streak ≥ 5 かつ revenue-critical 分類 | `payload.message` を `cron-codex.sh <skill>` wrapper 形に **強制 rewrite** (= 最強の Path 2 に強制移行)。 **launchd は使わない。** |
| L6 report | aggregate L1-L5 | Slack #metrics + `data/reports/YYYY-MM-DD.json` |

### 2.5 launchd 全廃 (= v1 からの主要変更)

v1 spec は Path 5 = launchd plist を含んでいたが Dais 21:48 JST に「OpenClaw gateway all the fucking way」と全廃指示。 v2 で:

- ✂️ Path 5 launchd 削除
- ✂️ cron-doctor の L5 launchd 自動生成ロジック削除 (→ `cron-codex.sh` wrapper 強制 rewrite に置換)
- ✂️ `~/Library/LaunchAgents/ai.anicca.{wallet-balance,earn-bounty,cron-doctor}.plist` 3 件 launchctl bootout + rm
- ✅ 上記 3 件を OpenClaw cron で再登録 (wallet + bounty は edit、 cron-doctor は新規 add)

## 3. Verification matrix (v2)

| AC | 何 | 判定方法 | 期限 | 状態 |
|---|---|---|---|---|
| AC-1 | wallet を Path 1 (cron-bash.sh wrapper) で OpenClaw cron fire し Slack に実 JSON | Slack ts に `usdc_balance` + address 含む | 本 session | ✅ ts=1780576597 |
| AC-2 | bounty を Path 2 (cron-codex.sh wrapper) で OpenClaw cron fire し Slack に scan/select 結果 | Slack ts に `scan` + `select returned N` | 本 session | ✅ ts=1780576912 |
| AC-3 | 自然 scheduled fire (= cron 内蔵 scheduler) で AC-1+AC-2 再現 | Slack #metrics の次 wallet (0:00/6:00/12:00/18:00 JST) + bounty (偶数時) 投稿 | 24h 自動 | ⏳ |
| AC-4 | anicca-cron-doctor が OpenClaw cron として 03:00 JST schedule 済 | `openclaw cron list \| grep cron-doctor` | 本 session | ✅ id=92f15d71… |
| AC-5 | spec + plan + 実装が git に commit + push 済 | `git log` | 本 session | ⏳ (進行中) |
| AC-6 | launchd 完全廃止 | `launchctl list \| grep ai.anicca` が空 | 本 session | ✅ |

## 4. Risks

| Risk | 軽減策 |
|---|---|
| gpt-5.4-mini が 1 行 `exec_command` すら拒否 | L3 refusal detector が 1h 後 retry、 L4-L5 が累積 3 回で `cron-codex.sh` 強制 rewrite |
| codex exec 401 Unauthorized (= 内側 sandbox に auth 伝播せず) | `cron-codex.sh` 内で `~/.codex/auth.json` から OPENAI_API_KEY を抽出 export 済 |
| codex exec の token 過剰消費 | 各 cron の `timeout 1500` でハード上限、 doctor が token spend を `data/reports/` に記録 |
| OpenClaw cron 内蔵 fallback chain が refusal を success 扱い | 解決待ち (= upstream PR)。 doctor L3 が事後 retry で軽減 |
| anicca-cron-doctor 自身が refuse する | L6 が同時に走るので 1 回目 refuse → 翌 03:00 自動 retry。 7 連続 refuse なら Slack #metrics の沈黙で判明 → 手動再 fire |

## 5. Out-of-scope (今 session ではやらない)

- OpenClaw 本体への upstream PR (model 無視 / refusal-as-error)
- 169 OpenClaw cron 全部の wrapper 化 (= doctor が L1 で逐次対応)
- iOS / Railway 側 cron との統合

## 6. References

| 引用 | URL / path |
|---|---|
| OpenAI Codex non-interactive 公式 | https://developers.openai.com/codex/noninteractive |
| Codex exec headless mode | https://deepwiki.com/openai/codex/4.2-headless-execution-mode-(codex-exec) |
| Codex Automations | https://developers.openai.com/codex/app/automations |
| OpenClaw `CRON_PAYLOAD_KINDS` enum | `/opt/homebrew/lib/node_modules/openclaw/dist/openclaw-tools-BUQsixTe.js` |
| OpenClaw cron CLI | `openclaw cron --help` |
| HARD RULE #-1 #-2 (Anicca has every tool / no excuses) | `CLAUDE.md` |
| 18:20 incident rollouts | `~/.openclaw/agents/anicca/agent/codex-home/sessions/2026/06/04/rollout-2026-06-04T18-20-{50,55}-*.jsonl` |

## 7. Change log

| date | change |
|---|---|
| 2026-06-04 14:00 JST | v1 spec written (5-path option space including launchd) |
| 2026-06-04 21:48 JST | Dais directive: OpenClaw all the way, no launchd |
| 2026-06-04 21:50 JST | **v2 published** — launchd全廃、 2-path canonical、 L5 launchd ロジック削除、 wallet/bounty/doctor 全部 OpenClaw cron 化 |
