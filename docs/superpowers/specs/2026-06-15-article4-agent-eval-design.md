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

## 7. Workflow output (filled 2026-06-15, run wf_c826dcbe-963)

Workflow stats: 20/20 sources fetched, 30/30 claims survived adversarial verify (0 refuted), 113 agents, 9.48M subagent tokens, 320 tool uses, 635s wall-clock.

### Trichotomy answer (Dais's core question)

「eval と observability/monitoring は **重なる部分はありますが別の領域** で、 self-improvement loop は observability で集めた本番ログを eval の採点台に乗せて、 その差分を fix にまわす形で **両方を橋渡しする運用** として作ります」 (anthropic_eval, langsmith, helicone)。

3 つを 1 行ずつ:
- **eval (採点)** = AI 用の unit test、 20-50 個のお題に対して code grader / LLM-as-judge / human grader の 3 種で 0-1 スコア (anthropic_eval, zenn_ttks)
- **observability (観測)** = 本番リクエストを span ツリー で 全部録画、 合否は出さない (langsmith, langfuse, openllmetry)
- **self-improvement loop (自己改善)** = ①観測 → ②採点 → ③診断 → ④修正 + 再採点、 ④を LLM 自身がやり始めた瞬間に成立 (reflexion, anthropic_agents)

### Title candidates (3, Japanese, ≤ 30 chars)

1. 観測なき agent は静かに腐る
2. 採点と観測と自己改善の地図
3. agent を退化させない3点セット

### Blocks (9-block hamburger)

| ID | Working title | Image | Sources |
|---|---|---|---|
| 0 | 結論早見表 | — | anthropic_eval, langsmith, helicone |
| 1 | 気づかないうちに劣化していた agent | 🎨V1 | zenn_edash, anthropic_eval |
| 2 | 観測と採点と自己改善の見取り図 | 🎨V2 | anthropic_eval, zenn_ttks, langsmith, langfuse, openllmetry, reflexion |
| 3 | ツール地図と問題別の選び方 | 🎨V3 | vercel_agent_eval, zenn_edash, inspect_ai, promptfoo, braintrust, helicone, openllmetry, datadog_llm, agentops, netdata, langfuse, langsmith, phoenix, reflexion, anthropic_agents |
| 4 | 観測 → 採点 → 診断 → 修正 の 4 ステップ | 🎨V4 | langfuse, langsmith, helicone, openllmetry, vercel_agent_eval, inspect_ai, braintrust, anthropic_eval, zenn_ttks, zenn_gaogao, reflexion, anthropic_agents |
| 5 | WE RAN IT: Anicca 本体に loop を仕込む | 🎨V5 | langfuse, inspect_ai, zenn_gaogao, anthropic_eval, langsmith |
| 6 | WE RAN IT: aniccaios スライドショーを毎リリース採点 | — | promptfoo, anthropic_eval, zenn_ttks, zenn_edash, vercel_agent_eval |
| 7 | 結論: 観測 → 採点 → 自己改善 の順で入れる | 🎨V6 | langsmith, langfuse, helicone, anthropic_eval, zenn_ttks, reflexion, anthropic_agents, netdata |
| 8 | 出典一覧 | — | all 20 |

Per-block guidance (verbatim from workflow synthesis) lives in workflow output `/private/tmp/claude-501/.../tasks/whiks1utt.output`. Each block enforces: em-dash 禁止 / Anicca 名 [0]-[4] [7] 禁止 (allowed only [5] [6]) / aggregation of one source 禁止 / meta-label 禁止 / first-use term definitions (英 + 日 + 一言定義) / verbatim founder quotes / article 3 への橋渡しは [3] 末尾 1 文のみ (内容反復禁止).

### Image spots (6)

| # | Block | Description |
|---|---|---|
| 🎨V1 | [1] | 14歳の机の上のノートPCに「先週まで動いていたのに今日壊れた」と赤く点滅する通知、 隣のグラフが 8/10 → 2/10 に下がる水彩風 |
| 🎨V2 | [2] | 3つの円のベン図、 左 = 観測 observability、 右 = 採点 eval、 下から上に貫く矢印 = 自己改善 self-improvement loop、 重なり領域に Langfuse/LangSmith/Phoenix のロゴ |
| 🎨V3 | [3] | 東京の地下鉄路線図風、 左半分 = eval 線 (Vercel agent-eval / Inspect / promptfoo / Autoevals 駅)、 右半分 = observability 線 (Helicone / OpenLLMetry / Datadog / AgentOps / Netdata 駅)、 中央乗換駅 = Langfuse / LangSmith / Phoenix |
| 🎨V4 | [4] | 回転する4ステップサイクル、 ①観測 (録画カメラ) ②採点 (赤ペンの先生) ③診断 (虫めがね) ④修正 (レンチ)、 矢印に「LLM-as-judge」「pass^k」「transcript 読み」「Regression 卒業」 |
| 🎨V5 | [5] | Anicca の自画像ロボット、 自分の額に貼られた CLAUDE.md ルール 1 枚を Langfuse trace ビュー を見ながら右手のレンチで書き換え、 左手で Inspect cron グラフを見る断面図 |
| 🎨V6 | [7] | 3層ピラミッド、 土台 = observability、 中段 = eval、 頂上 = self-improvement loop、 各段に Helicone / Inspect / Reflexion のシンボル、 左横に「この順で積むこと」 |

### Sources (20, in body order)

1. zenn_edash — https://zenn.dev/edash_tech_blog/articles/84f0cd8567646b (CLAUDE.md eval 実験)
2. anthropic_eval — https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (Anthropic 公式 eval 入門)
3. zenn_ttks — https://zenn.dev/ttks/articles/0d2b16606b59f9 (JP agent eval 実装)
4. langsmith — https://docs.smith.langchain.com (trace → dataset → eval)
5. langfuse — https://github.com/langfuse/langfuse (OSS observability + eval)
6. openllmetry — https://github.com/traceloop/openllmetry (OpenTelemetry for LLM)
7. reflexion — https://arxiv.org/abs/2303.11366 (Reflexion 論文)
8. vercel_agent_eval — https://github.com/vercel-labs/agent-eval (Docker + vitest)
9. inspect_ai — https://github.com/anthropics/inspect_ai (UK AISI + Meridian Labs)
10. promptfoo — https://github.com/promptfoo/promptfoo (100% local CLI)
11. braintrust — https://github.com/braintrustdata/autoevals (Autoevals)
12. helicone — https://github.com/Helicone/helicone (Gateway 経由 1行)
13. datadog_llm — https://docs.datadoghq.com/llm_observability/ (Agent Observability 改名)
14. agentops — https://github.com/agentops-ai/agentops (session replay + cost)
15. netdata — https://github.com/netdata/netdata (LLM span 非対応)
16. phoenix — https://github.com/Arize-ai/phoenix (OpenInference)
17. zenn_gaogao — https://zenn.dev/gaogaoasia/articles/65db07864e31b8 (Verifiable Unit + Auditor)
18. anthropic_agents — https://www.anthropic.com/engineering/building-effective-agents (evaluator-optimizer)
19. openai_agents — https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
20. awesome_ai_eval — https://github.com/Vvkmnn/awesome-ai-eval (ecosystem 地図)

### Surprising findings (散りばめる候補、 10件)

1. Anthropic Opus 4.5 は CORE-Bench で最初 42% → grader バグ修正 + scaffold 緩和だけで **95%** に跳躍 (anthropic_eval)。 公開ベンチ数字は実力を取り違える。
2. Anthropic 推奨: 「ツールの呼び出し手順 (path) は採点するな、 最終成果物だけを採点しろ」 — 手順を縛ると創造性を不当に罰する (anthropic_eval, zenn_ttks)。
3. 成功率 75% の agent を 10 回連続成功させる確率 (pass^k) は約 **6%** — 1 回の高成功率は全試行成功にはほぼ寄与しない (anthropic_eval, zenn_ttks)。
4. Vercel agent-eval で **CLAUDE.md ルールを足しただけ** で Next.js eval のパス率 **2/10 → 8/10** に 4 倍改善 (zenn_edash)。
5. Anthropic gaogao のサプライヤー順位付け agent は system prompt を **402 行 → 15 行** に削った方が **71% → 92%** に上昇 (zenn_gaogao)。 短いほうが良いこともある。
6. Reflexion は **重みを 1 ミリも更新せず**、 「失敗を言葉で書いてメモする」 だけで GPT-4 baseline (HumanEval 80%) を **91%** で上回った (reflexion)。 self-improvement は fine-tuning より prompt + memory が先。
7. Inspect は名前から Anthropic 製と誤解されがちだが、 実際は **UK AI Security Institute + Meridian Labs** 製、 Anthropic は対応モデル提供者に過ぎない (inspect_ai)。
8. promptfoo は **OpenAI 傘下** になっても **MIT で 100% local 実行**、 プロンプトを外に出さない設計を維持 (promptfoo)。
9. Netdata は LLM 観測の文脈で名前が挙がるが、 README 時点 (2026 年 6 月) で OpenTelemetry 対応は **「soon」 のまま**、 LLM span を取り込めない (netdata)。
10. Datadog は製品名を **「LLM Observability」 → 「Agent Observability」** に寄せ、 prompt injection 検出と安全性チェックを観測性に統合 (datadog_llm)。 eval / safety / observability の境界が現場では溶け始めている。

## 8. Skill patch list (filled by workflow Phase E)

Proposed appends to `~/.openclaw/skills/ai-entity-article-writer/SKILL.md` PLAYBOOK (rules 55-61, general — not eval-specific):

55. **Trichotomy diagramming**: When the topic is a trichotomy (3 concepts confused as one), open the explainer block with a Venn or quadrant diagram that names each cell, defines each term once on first use (英 + 日 + 一言定義), and explicitly marks which cell each named tool lives in, so the reader can never re-collapse the three.
56. **Landscape table seeding**: When the article needs a tool-landscape block, present it as a single dense markdown table (tool name / cell / one-line trait / license-cost) followed by an 'if you want X, use Y' selector list, and seed 2-3 surprising findings (mislabeled vendor, false reputation, dated capability claim) inside the same table to break the 'list of logos' boredom.
57. **Pre-run WE-RAN-IT receipt slots**: When a WE-RAN-IT block must be written before the actual run, structure it as 'protocol + receipt slots' (designed pipeline + expected-trap list + empty result table with run id / score / diff / cost columns) rather than narrative placeholder, so the post-run author only fills cells and never rewrites prose.
58. **Sibling article bridging**: When two adjacent articles in the series touch overlapping territory (e.g., per-turn verify vs time-series eval), include exactly one bridging sentence near the end of the relevant block that names the sibling article and forbids content repetition, never a full recap.
59. **Dual-ended order assertion**: When the article makes ordering claims ('do A before B before C'), the verdict block must state the order in sentence 1 and the closing block must restate it with one paragraph per step explaining why reversal fails, so the order is asserted at both ends of the article and cannot be skimmed away.
60. **Surprise + number pairing**: When a concept is anti-intuitive but load-bearing (pass^k collapse, shorter-prompt-wins, weight-free self-improvement), pair each surprise with a single named number from a cited source in the same sentence, so the reader cannot dismiss it as opinion.
61. **Block-level brand scoping**: When the article has a brand-name anti-rule (mention product only in specific blocks), declare the allowed and forbidden block ids explicitly in editor_notes and repeat the constraint inside each block's guidance, so block-level writers cannot drift.

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
