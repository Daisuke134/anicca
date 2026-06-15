# Article #4 — Agent Eval / Observability / Self-Improvement Design Spec

- **Date**: 2026-06-15
- **Series**: AI-entities (parent SSOT = `docs/superpowers/specs/2026-06-10-ai-entity-content-engine-design.md`)
- **Status**: DRAFT — research workflow pending, hamburger structure to be confirmed by Dais
- **Editor / co-author**: Daisuke (human-in-loop, block-by-block) + Claude Code
- **Subject**: How an autonomous AI agent **evaluates itself, monitors itself, and improves itself end-to-end** so a human is not needed in the loop. The reader's core confusion to dissolve: **「agent eval」と「agent monitoring / observability」は同じ領域か、別か?** Then: what is the BP today, install + use it now on (a) **anicca** (the autonomous earn agent that has to self-improve), (b) **aniccaios** (the affirmation app that has to evaluate its own slideshow output).
- **Why this slot (in the series)**:
  - #1 Automaton: established the no-human-in-loop thesis (the mechanism exists).
  - #2 Frank/BlockRun: the agent has a wallet, can pay, can act (the body exists).
  - #3 Self-Verification: each turn's output is not a lie (the per-turn truth check exists).
  - #4 Agent Eval (this): the agent **knows whether it is getting better or worse over time** and can self-correct. Without this, #1-#3 still drift. This is the feedback loop that closes the system.
- **Anti-rule**: NEVER self-promotion. Write for a stranger who runs an agent and wants it to improve itself overnight without a human grading the output. Anicca + aniccaios are the demo, not the subject.

## 1. The core question to answer (this piece exists to answer it)

「agent eval (= モデル/プロンプト/エージェントを多数のテストケースで採点する) と agent observability / monitoring (= 走っている agent の挙動・コスト・エラーをログから観測する) は **同じ領域か、別領域か**」 そして 「**self-improvement loop (= agent が自分のログを見て自分を直す)** は どちらの 道具 で 作るのか」

Pre-research hypothesis (to verify in workflow §6):

- **3 つの 別工程、 ただし 1つ の loop を 作る ピース**:
  - **Eval (オフライン採点)** = batch、 ベンチ的、 ground-truth or LLM-as-judge を 全件比較、 CI で regression catch。 promptfoo / Anthropic Inspect / Vercel agent-eval / Braintrust / LangSmith / RAGAS / DeepEval / OpenAI Evals。
  - **Observability / Monitoring (オンライン記録)** = 走っている agent の trace / span / token / cost / latency / error / tool-call を OpenTelemetry 標準 で 記録、 ダッシュボード で 見る。 Langfuse / AgentOps / Phoenix (Arize) / Helicone / OpenLLMetry / LangSmith (両刀) / Datadog LLM Observability / Netdata。
  - **Self-improvement loop** = ①observability で ログ取る → ②eval で 採点 (= regression / 退化検知) → ③agent 自身 が 失敗 case を 見て プロンプト or skill を書き換える → ④再 eval。 LangSmith / Phoenix / AgentOps の 「production trace → dataset → eval → annotate」 機能 + Voyager / Reflexion 系 self-improving agent paper。
  - 関係: eval = 「良くなっているか」、 observability = 「いま 何が 起きているか」、 self-improvement = 「観測→採点→直す」 を agent が 自分で 回す。 3つ 揃わないと no-human-in-loop は 必ず 止まる。
- Conclusion shape: **一つの記事 (3 つ を 別々に 書くと 読者 は 関係 を 見失う)、 ただし 軸 は self-improvement loop、 eval と observability は その 2 部品 として 提示**。

## 2. Primary sources (locked, must all be read in full — no summaries)

Dais 渡し 8 件 + 周辺 必須 を 並べる。 Phase A FETCH 対象 = この §2 + workflow が 自動補完。

| # | URL | Role |
|---|---|---|
| 1 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Dais 指定 BP: Anthropic 公式 "agent eval 入門" (eval が何で何でないかの定義) |
| 2 | https://github.com/vercel-labs/agent-eval | Dais 指定 BP: Vercel 公式 agent-eval (新しい landscape の 一角) |
| 3 | https://zenn.dev/ttks/articles/0d2b16606b59f9 | Dais 指定 BP: 日本語 で 「agent eval を実装」 した 実装記 |
| 4 | https://github.com/Vvkmnn/awesome-ai-eval | Dais 指定 BP: ecosystem の地図 (全 eval/observability tool 一覧) |
| 5 | https://zenn.dev/edash_tech_blog/articles/84f0cd8567646b | Dais 指定 BP: 日本語 で 「agent eval/observability の使い分け」 系 |
| 6 | https://zenn.dev/gaogaoasia/articles/65db07864e31b8 | Dais 指定 BP: "Claude Code — 長時間エージェント の 道具" (article 3 でも引用、 self-improvement の 文脈) |
| 7 | https://github.com/netdata/netdata | Dais 指定 BP: agent observability の native infra 系 |
| 8 | https://github.com/agentops-ai/agentops | Dais 指定 BP: agent 専用 observability + replay + cost (Python first) |
| 9 | https://github.com/langfuse/langfuse | LLM observability + eval (両刀) の OSS デファクト、 self-hostable |
| 10 | https://docs.smith.langchain.com / https://github.com/langchain-ai/langsmith-docs | LangSmith — production trace → dataset → eval loop の代表 |
| 11 | https://github.com/Arize-ai/phoenix | Phoenix (Arize) — OSS observability + eval、 OpenInference |
| 12 | https://github.com/anthropics/inspect_ai | Anthropic 公式 eval framework (article 3 と共通) |
| 13 | https://github.com/promptfoo/promptfoo | デファクト eval/red-team CLI (article 3 と共通) |
| 14 | https://github.com/braintrustdata/autoevals + braintrust.dev | LLM-judge eval (article 3 と共通) |
| 15 | https://github.com/traceloop/openllmetry | OpenTelemetry for LLM (vendor neutrality の 旗) |
| 16 | https://github.com/Helicone/helicone | Proxy 型 observability (5 min 導入) |
| 17 | https://docs.datadoghq.com/llm_observability/ | Datadog LLM Observability (enterprise 軸) |
| 18 | "Reflexion" (Shinn 2023) / "Voyager" (Wang 2023) / "STaR" / "Self-Refine" 原典 | self-improving agent の 理論的支柱 |
| 19 | "Agent as Judge" (Zhuge 2024) / "G-Eval" / "MT-Bench" | LLM-as-judge の境界線 |
| 20 | Anthropic "Building effective agents" (2024-12) / OpenAI "A Practical Guide to Building Agents" (2025) | 公式 agent design BP (eval が core 章) |

Adjacent: superpowers `verification-before-completion` / `fact-checker` (article 3 と継続)、 OpenTelemetry GenAI semantic conventions、 OpenInference spec。

## 3. Reader / verdict (block [0] target)

- **Reader**: Claude Code / OpenClaw / LangGraph / CrewAI / autogen 等 で すでに agent を 動かしている人。 「とりあえず 動いた」 から 先 に 進めない。 production で 静かに 退化する 恐怖、 cost が 月 末 に 跳ねる 恐怖、 ユーザー の cancel が 増えた 時 に 「どこ が 悪いか」 が ログ から 言えない 恐怖 を 抱えている。
- **Pre-research hypothesis (to verify in workflow + WE-RAN-IT)**:
  - ✓ **eval ≠ observability** だが、 **同じ loop の 2 部品**。 まず observability (= log 取る) を 入れる、 次 eval (= 採点 する)、 次 self-improvement (= agent が 自分で 直す) の 順 が 現実的。
  - ✓ TODAY 入れるべき 最小セット = ① OpenTelemetry / OpenLLMetry で trace 出す ② Langfuse or Phoenix を 自前 host で trace 受け ③ promptfoo or Inspect で CI に eval gate ④ agent 自身 に 「失敗 trace を pick → 原因 を 言語化 → skill / prompt を 書き換える → 再 eval」 の cron。
  - ✓ AgentOps = Python agent (CrewAI / autogen / LangGraph) を 既に 使っている人 に 一番 速い ($0 free tier、 1 line decorator)。
  - ? 「LLM-as-judge」 の バイアス (Position / Verbosity / Self-preference) が **self-improvement loop の 駆動源 と して 信用 できるか** = 記事 の 山場。

## 4. Hamburger (PRE-RESEARCH skeleton — replaced after §6 workflow)

| Block | Working title | Notes |
|---|---|---|
| [0] | Verdict (text) | use-if / skip-if + 早見表 (cost / risk / install 時間 / 効果 / 誰向け) |
| [1] | Hook | 「agent が 静かに 退化していた」 具体例 (e.g. プロンプト 1 行 変えた、 出力品質 が 落ちた、 気づかず 1 週間 配信、 ユーザー churn)。 観測なき 自律 = ハルシネーション工場 |
| [2] | これは何の話か (everyone) | "eval" と "observability" と "self-improvement loop" を 1 図で。 3 つは 別物、 ただし 1 つ の 改善 ループ の 部品 |
| [3] | 風景 (landscape) | eval 側 (Inspect / promptfoo / Vercel agent-eval / Braintrust / RAGAS / DeepEval / OpenAI Evals) + observability 側 (Langfuse / AgentOps / Phoenix / Helicone / Datadog / OpenLLMetry / Netdata) + 両刀 (LangSmith) を 並べ、 どの 問題 に どっち、 を 表 に |
| [4] | しくみ (engine) | self-improvement 4-step loop (observe → score → diagnose → patch + re-score) を 図 で、 LLM-as-judge の 限界 (Position / Verbosity / Self-preference bias) と Ground-truth dataset の 作り方 を 正直 に |
| [5] | WE RAN IT — anicca (= 自律 earn エージェント の 自己改善) | observability (Langfuse OSS or AgentOps) を anicca に 配線 + Inspect で daily eval cron + 失敗 trace を agent 自身 が pick して spec / skill を patch する loop を 1 週間 走らせ、 (a) 検知した退化 (b) 自動 patch 成功率 (c) cost を 計測 |
| [6] | WE RAN IT — aniccaios (= iOS slideshow 出力 評価) | slideshow の hook / demo / caption / audio を LLM-as-judge + 人手 ground-truth で eval、 promptfoo or Inspect で CI gate、 退化 検知 で TestFlight ブロック まで 配線 |
| [7] | 結論 (verdict expanded) | 入れるべき 順序 (observability → eval → self-improvement)、 入れなくていい 人、 開発者 の 脳内モデル |
| [8] | シリーズ次回予告 + 出典 | 次 = ? + brand manifesto closing |

Apply parent SSOT §11 PLAYBOOK verbatim (no em-dash 30, natural JP 31, define-on-first-use 39/54, gradations 42, cite everything 25, 出典 list, full block in review 44).

## 5. WE-RAN-IT protocol

### 5.1 Anicca (autonomous earn agent — self-improvement loop)

| Step | Action | Receipt |
|---|---|---|
| 1 | Pick one anicca instance (Hermes ~/.hermes or OpenClaw ~/.openclaw — choose lower-risk per article-3 same logic) | path + commit |
| 2 | Wire OpenLLMetry decorator OR AgentOps 1-line decorator on agent entrypoint | grep installed + 1 sample trace JSON |
| 3 | Self-host Langfuse OR Phoenix (docker compose up); point traces at it | dashboard URL screenshot, trace count |
| 4 | Define 10-row eval dataset (= 10 of anicca's repeating tasks: post, reply, scrape, fund-apply, draft-mail, etc.) with ground-truth or `Agent-as-Judge` rubric | dataset YAML + scoring script |
| 5 | Schedule daily Inspect / promptfoo run on dataset → write score to Langfuse → if regression > threshold, open self-issue | cron entry, 1 sample fail report |
| 6 | Write self-improvement skill: pick worst-N traces → ask agent "why did this fail?" → produce skill / prompt diff PR → run eval on the diff → merge if improves | skill code + 1 sample PR |
| 7 | Run 7 days; capture (a) detected regressions (b) auto-patches merged (c) net token cost (d) human override count | jsonl event log + 1-page write-up |

### 5.2 Aniccaios (iOS affirmation / slideshow output eval)

| Step | Action | Receipt |
|---|---|---|
| 1 | Build 20-row eval dataset of slideshow outputs (hook, demo, caption, audio, image) with both Dais-rated ground-truth and LLM-judge rubric | dataset CSV |
| 2 | Wire promptfoo or Inspect eval against slideshow generator pipeline (model + prompt + post-process) | CI yaml |
| 3 | Add Maestro-based runtime quality probe (= post-launch, render 1 slide, screenshot, judge by LLM) | flow file + sample judgement |
| 4 | Wire regression gate = if avg score drops > 5%, block TestFlight upload (= per HARD 0.27, publish gate stays Dais's OK, but eval gate fires before that) | gate script + 1 sample block |
| 5 | Document the unavoidable human gates (Apple ID for IAP, App Store review) per `feedback_fastlane_cannot_test_paywall` | list with reasons |

Total spend cap: 0 USD (no infra), only Claude token spend during research workflow. Receipts → `docs/articles/research/2026-06-15-agent-eval-receipts.md`.

## 6. Research workflow (Dynamic Workflow — fan-out → adversarial verify → synthesize)

Built per parent SSOT §11 Playbook + 2026-06-14 BP article rules. Foreground, structured-output, 1 run.

- **Phase A — FETCH (fan-out, Haiku-class)**: one agent per primary source row in §2 (≈20 sources). Each uses `firecrawl scrape <url> markdown` (HARD 0.23) + `gh api repos/<o>/<r>/contents/...` for repo files. Returns `{thesis, definition_of_eval, definition_of_observability, definition_of_self_improvement, install_steps, code_signature_or_cli, founder_or_author_quote, primary_url, concrete_numbers}`.
- **Phase B — TRICHOTOMY (1 Opus agent)**: synthesize a clean **"eval vs observability vs self-improvement loop"** distinction from all FETCH outputs. Output must include: (i) one-paragraph definition each, (ii) Venn / matrix, (iii) when-to-use rules, (iv) named tools per side, (v) the 1 sentence Dais asked for (= "同じか別か")、 (vi) **the bridging loop** that ties all 3.
- **Phase C — ADVERSARIAL VERIFY (3 verifiers per non-trivial claim)**: each verifier instructed to **REFUTE**. Vote ≥ 2/3 confirms. Drops shaky claims. Specially harsh on LLM-as-judge bias claims and "self-improvement" feasibility claims.
- **Phase D — HAMBURGER ASSEMBLY (1 Opus agent)**: produce final 9-block plan with paragraph-level guidance, 🎨V# image spots, cited 出典, 3 JP title candidates ≤ 30 chars.
- **Phase E — SKILL PATCH LIST**: produce a diff-shaped PR for `~/.openclaw/skills/ai-entity-article-writer/SKILL.md` (= new playbook rules learned from this piece — generalize 3-stage trichotomy pattern, don't hard-code "eval").
- **Token budget**: target ≤ ~100k output tokens (eval/observability landscape is broader than article 3's verify).
- **Quarantine**: every Fetch agent is read-only; no agent writes to disk; main loop writes spec § 7 + § 8 from return values.

## 7. Workflow output (§7 filled by workflow return)

_Filled after first workflow run. Will contain: trichotomy paragraph, 9-block hamburger, image list, title candidates, sources._

## 8. Skill patch list (§8 filled by workflow return)

_Filled after first workflow run. Will contain proposed appends to `ai-entity-article-writer/SKILL.md` PLAYBOOK._

## 9. Open items (resolve during execution)

- Is **Vercel agent-eval** a general-purpose framework or AI SDK-locked? (decides whether to put it center stage or label as "AI SDK 派").
- Does **netdata** truly cover LLM agent traces, or is it host metrics only? (= decides whether it's in §3 landscape table or removed).
- **LangSmith** = closed-source SaaS, but the "production trace → dataset → eval" loop is the cleanest exemplar. How do we present it honestly without endorsing lock-in.
- Is **Agent-as-Judge** (Zhuge 2024) sufficient evidence to claim self-improvement is feasible TODAY, or do we have to gate it as "experimental, still needs human ground-truth alongside"?
- Choose anicca instance for WE-RAN-IT: Hermes (~/.hermes) or OpenClaw (~/.openclaw) — lowest blast radius wins, same as article 3.
- aniccaios slideshow eval: which 20 outputs to pick as the dataset? (likely the most recent 20 posted to socials, with Dais's like/dislike as silver-standard).

## 10. Sources for the parent series (carry over)

- Parent SSOT 2026-06-10 §11 (PLAYBOOK 1-54)
- Article #1 (Automaton) `docs/articles/2026-06-11-automaton-jp.md` — voice sample
- Article #2 (Frank) `docs/articles/2026-06-15-frank-jp.md` — voice sample (early)
- Article #3 (Self-Verification) `docs/superpowers/specs/2026-06-15-article3-self-verification-design.md` — adjacent (verify-loop = per-turn truth; eval-loop = long-term direction; the 2 together close no-human-in-loop)
