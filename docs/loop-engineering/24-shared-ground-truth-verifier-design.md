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
