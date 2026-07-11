# 全 loop 共通 Ground-Truth Verifier — 設計（OSS 調査に基づく copy+tweak）2026-07-11

## 目的
全 loop（profitable-claude CEO 系 + Franklin/anicca agent 経済系）の self-healer に、**report を読まず実 side-effect を見に行く**同一の verifier を配る。「真実を知らねば直せない」＝ verifier は self-healer の中核。出典地図 → `README.md`、原則 → `23-anicca-loop-architecture-redesign.md` §0。

## OSS 調査結論（車輪の再発明回避、subagent `ac1f4d37` 実査）
**単一の"勝者"OSS は存在しない**（browser+on-chain+exec を横断し fresh-context で PASS/FAIL する完成品は無い）。証拠収集ツールと判定パターンに分かれる → **NEVER COMBINE 違反ではなく「agent = LLM + tools」構成（Anthropic 公式推奨）で道具を持たせる**のが正解。

| repo | 役割 | 実side-effect | License | 採否 |
|---|---|---|---|---|
| **AmElmo/proofshot** | 実ブラウザで録画+スクショ+console/serverログを bundle。Claude Code native skill 配布 | ○(見に行く・判定はしない) | MIT 840★ | ★採用（browser 証拠収集） |
| **vercel-labs/agent-browser** | proofshot 下敷きの headless browser CLI（既存 skill） | ○ | Vercel OSS | ★採用（primitive） |
| anthropics/claude-cookbooks evaluator_optimizer | 生成/評価分離 PASS/FAIL+feedback loop の正本 | ×(LLM判断) | Anthropic公式 | ★採用（判定型） |
| sierra-research/tau-bench | 「trajectory でなく final system state を突合」原則 | ○(設計原則) | MIT 1319★ | ★採用（原則） |
| ERC-8004 | 独立 validator が on-chain で再検証する信頼標準 | ○(on-chain) | EIP標準 | ★採用（on-chain原則） |

核心引用:
- ProofShot README: "ProofShot closes the loop … test in a real browser, record video proof, collect errors" — 実ブラウザで見る証拠収集（判定は足す）。
- Anthropic building-effective-agents: "one LLM call generates a response while another provides evaluation and feedback in a loop."
- tau-bench: "an agent succeeds only if its sequence of actions produces the correct final system state." ← 求める原則そのもの。
- ERC-8004: "establish trust through reputation and validation" — 独立 validator による on-chain 再検証。

## 採用する構成（= 全 loop 共通 verifier subagent 定義）
`general-purpose / fresh Opus` を adversary pattern で回し、以下を **tool として持たせる**:
| ドメイン | tool | 見るもの |
|---|---|---|
| browser | `agent-browser` + `proofshot`(MIT skill install) | logged-out DOM 本文/動画/BAN、投稿URL、gig各action、gcal readback |
| on-chain | `mcp__claude_ai_Base_MCP__get_transaction_history` / `chain_rpc_request`（既接続） | 実 tx/残高増（seed を earn と偽らない）。ERC-8004 思想 |
| exec | `Bash` | exit code / ledger 実増 / state file 実体 |
| 判定型 | prompt に evaluator-optimizer + tau-bench「final state を見る」を明文化 | report 禁止・binary verdict・findings のみ |

## 配布（Dais 明示: "put it everywhere — Franklin, main loop"）
1. **vcsdd-adversary を「見に行く」版に差し替え**: 現状 tools=Read/Write/Edit/Grep/Glob（Bash無・browser無=静的、`memory feedback_vcsdd_adversary_is_static...` 参照）→ Bash + agent-browser/proofshot + chain_rpc を付与。
2. **profitable-claude CEO 系**（gig/capafy/article/LM/affiliate/bounty/connector）の healthcheck/self-fix がこの verifier を呼ぶ。
3. **anicca/Franklin agent 経済系**（clip/video/reddit/sol/pm/founder）にも同一定義を配る。
4. 雛形 = connector の `connector_streak_verify.py`（一次情報を独立再検証、唯一 BP 準拠だったもの）を「browser+on-chain 版」に一般化。

## Done（この verifier 自体の検証）
実際に clip(投稿停止)/reddit(BAN)/founder($9.02 on-chain)/connector(gcal readback) を**この verifier に食わせて、report と乖離した真実を返せた**時のみ working。＝ 2026-07-11 に手動でやった検証を verifier に焼き込む。

---

## ★ v3 — 深掘り再調査(13候補)の最終決定（採用framework確定）2026-07-11

**採用 = Claude Code subagent primitive を verifier に（新 framework は入れない）。名前 `reality-verifier`（agent 定義）。** verifier は **shell file でなくモデル(tool を持つ Claude subagent)**＝Dais の指摘が正。

**なぜこれ（NEVER COMBINE、1つ）**:
- 新規依存ゼロ。我々は既に fresh subagent を毎日 spawn してる（agent 実行=満たす / headless cron 起動=満たす）。**欠けてるのは framework でなく「tool + prompt discipline」だけ。**
- Inspect AI 一式を入れると、既にある subagent-spawn 機構を Inspect の Task/Solver/Scorer 抽象で**再発明**する＝車輪の再発明禁止に抵触。
- 出典 = Anthropic "Building Effective Agents"（augmented LLM / orchestrator-worker 公式パターン）。

**tweak（既存 agent 定義に足すだけ）**:
1. tool 権限: **agent-browser + Base MCP(chain_rpc/get_transaction_history) + Bash(curl/exec)** を付与（現状 vcsdd-adversary は Read系のみ=盲目）。
2. prompt に3つの引用原則を明記:
   - **agent-as-a-judge**（metauto-ai/agent-as-a-judge, MIT 795★）= LLM judge が tool を能動的に呼び **claim 単位で証拠を引用**して判定。
   - **tau-bench / attest** = trace/narrative でなく **receipts/最終 state** を見る。
   - **Gaming the Judge**（Khalifa et al. 2026, arXiv:2601.14691）★外部証明★ = 「agent の行動はそのままに reasoning だけ書き換えると AI judge の false-positive が最大90%上がる」＝ **narrative/report ベース判定は騙される**。我々の脳外科ルールの正しさを裏付ける。
3. 直前 agent の report/log を ground truth として**読ませない**（毎回自分で tool を呼ばせる）。

**具体 action**: `.claude/agents/reality-verifier.md` を新規作成（or vcsdd-adversary を拡張）。loop からは fresh subagent として spawn（既存 self-fix.sh の spawn を、report を読ませず reality-verifier を呼ぶ形にする）。

**却下**: DeepEval/Ragas/TruLens/promptfoo/Langfuse/Phoenix/OpenAI evals = **テキスト/trace 採点のみ、現実を tool で見ない**（要件不適合）。attest = agent 自身が記録した tool 出力ログを信じる（source 汚染に弱い）。tau2-bench = 決定論 benchmark で任意 loop に差し込めない。metauto agent-as-a-judge = 良い architecture だが tool が code-workspace 専用（browser/on-chain 無）→原則だけ借用。

---

## v2 — verifier は「全ツール」を持つ（Dais 2026-07-11 明示、怒り）

★ 原則: verifier は **every tool** を持たねばならない。ツールが足りない verifier は truth を見られず＝無意味。★ 現状の vcsdd-adversary(Read/Write/Edit/Grep/Glob = Bash無・browser無・on-chain無) も vcsdd-verifier(Bash はあるが browser無・on-chain MCP無・役割は formal code hardening) も**不足**。

### 必須ツール一覧（verifier が持つべき全部）
| ドメイン | tool | 見る truth |
|---|---|---|
| shell/exec | **Bash** | 実コマンド・test 再実行・log raw tail・プロセス確認 |
| browser（自分の目で見る） | **agent-browser / playwright-cli / CloakBrowser :9222** | aniccaai.com/dashboard を実際に開く・logged-out DOM 本文・BAN/shadow-filter・UI が本当に動くか |
| on-chain | **mcp__claude_ai_Base_MCP__* / chain_rpc_request / blockrun_rpc / blockrun_wallet** | 実 tx・残高増・external:true（seed を earn と偽らない、ERC-8004 独立再検証） |
| web/API | **firecrawl / WebFetch / 直接 curl** | 実サイトの掲載状態・実 API レスポンス |
| file/search | Read/Grep/Glob | spec・ledger・state（ただし ledger 自己申告は truth でなく参照） |
| screenshot 証跡 | **proofshot / screenshot** | 見たものを証拠として残す |

= Anthropic 公式「agent = LLM + tools」。verifier は全 tool を持ち、**report/ledger の自己申告を信じず、実 side-effect を自分の目（browser DOM / on-chain tx / 実ログ）で見て binary verdict**。

### 判定原則（変えない）
1. executor と別の fresh context（自己採点禁止）
2. report でなく state/outcome（実 side-effect）を見る
3. done = 決定的（on-chain tx / DOM 本文 / exit code）、LLM テキスト不可
4. 「稼いだ」= external:true 実 tx を on-chain で自分が確認した時のみ
5. fake を疑う: label（"PUBLISHED"/"EARNING"）と実 side-effect を必ず突き合わせ、乖離を findings に

### 配布
- プロジェクト版 agent `ground-truth-verifier`（全 tool 付き）を `.claude/agents/` に置く（marketplace plugin は update で消えるので直接編集しない）。
- vcsdd の Phase 3/1c review と、各 daily loop の healthcheck / self-fix verify 段の両方でこの1つを使う。
- 雛形 = connector_streak_verify.py（一次情報の独立再検証）を「browser+on-chain+全tool」版に一般化。

### Done（この verifier 自体の検証）
clip(投稿停止)/reddit(BAN)/founder($9.02 on-chain)/connector(gcal readback)/pm($4.95凍結)/Franklin(external:true=$0) を実際に食わせ、**report と乖離した真実を browser/on-chain で自分の目で返せた**時のみ working。
