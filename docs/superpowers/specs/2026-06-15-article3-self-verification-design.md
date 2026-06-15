# Article #3 — AI Self-Verification (Verify vs Eval) Design Spec

- **Date**: 2026-06-15
- **Series**: AI-entities (parent SSOT = `docs/superpowers/specs/2026-06-10-ai-entity-content-engine-design.md`)
- **Status**: DRAFT — research workflow pending, hamburger structure to be confirmed by Dais
- **Editor / co-author**: Daisuke (human-in-loop, block-by-block) + Claude Code
- **Subject**: How an AI **verifies its own work end-to-end** so a human is not needed in the loop. The reader's core confusion to dissolve: **「verification (E2E自己検証)」と「agent eval」は同じか、別か?** Then: what is the BP today, install + use it now on (a) an autonomous earner like **anicca** (OpenClaw / Hermes), (b) a real iOS app like **aniccaios** (affirmation app, Maestro-tested).
- **Why this slot**: #1 Automaton + #2 Frank surfaced the gap — "the mechanism exists, the money/quality doesn't arrive automatically because nobody verifies the agent's output". Verification *is* the bottleneck of no-human-in-loop. This piece names + dissolves it.
- **Anti-rule**: NEVER as a self-promotion piece. Write for a stranger who wants to make their agent / their app self-verifying TODAY. Anicca + aniccaios are the demo, not the subject.

## 1. The core question to answer (this piece exists to answer it)

「self-verification (= AI が自分の成果を E2E で確かめる) と agent eval (= モデル/プロンプト/エージェントを多数のテストケースで採点する) は **同じものか、別物か**」

Pre-research hypothesis (to verify in workflow §6):
- **Different stages of the same loop, not synonyms.**
  - **Eval (オフライン採点)** = batch、ベンチ的、ground-truth or LLM-as-judge を全件比較、CI で regression catch、 promptfoo / LangSmith / Braintrust / Inspect / RAGAS / OpenAI Evals / AnthropicEval。
  - **Verification (オンライン1件検証)** = 個別の成果物が「本当に動いた / 嘘ついてない」を**その実行で**確かめる。verification-before-completion 5-step、 fact-checker subagent、 PostToolUse hook、 E2E (Maestro / Playwright)、 type-check、 unit smoke、 production canary、 self-test。
  - 関係: eval は「プロンプト/モデル/フローを良くする」、verification は「この turn の成果物を信じてよいかを決める」。両方無いと no-human-in-loop は壊れる。
- Conclusion shape: **一つの記事 (片方だけ書くと不完全)、ただし軸は verification、 eval は対比として最小限**。

## 2. Primary sources (locked, must all be read in full — no summaries)

| # | URL | Role |
|---|---|---|
| 1 | https://zenn.dev/gaogaoasia/articles/65db07864e31b8 | Dais 指定 BP: "Claude Code — 長時間エージェントと付き合う3つの道具" (検証道具の文脈) |
| 2 | https://github.com/anthropics/cwc-workshops | Dais 指定 BP: Anthropic 公式 "Claude with Code" ワークショップ (eval / verify の公式やり方) |
| 3 | https://docs.claude.com/en/docs/agents-and-tools/agent-skills | superpowers の verification-before-completion / fact-checker / systematic-debugging の現行版 |
| 4 | https://docs.anthropic.com/en/docs/agents-and-tools/computer-use 周辺 (Eval cookbook) | Anthropic agent eval 公式 |
| 5 | https://github.com/anthropics/inspect_ai | Anthropic 公式 eval framework |
| 6 | https://github.com/promptfoo/promptfoo | デファクト eval/red-team CLI |
| 7 | https://github.com/langfuse/langfuse + https://github.com/langchain-ai/langsmith | observability + eval |
| 8 | https://github.com/braintrustdata/autoevals + braintrust.dev | LLM-judge eval |
| 9 | https://github.com/explodinggradients/ragas | RAG eval (反例として軽く) |
| 10 | https://github.com/confident-ai/deepeval | OSS eval |
| 11 | https://maestro.dev/ + GitHub | iOS/Android E2E |
| 12 | https://playwright.dev/ + agent eval mode | web E2E、 LLM judge mode |
| 13 | https://github.com/anthropics/claude-code 公式 hooks docs | PostToolUse / Stop hook で verify を強制する公式手法 |
| 14 | "Agent as Judge" / "Self-consistency" / "Reflexion" 原典論文 | self-verify の理論的支柱 |
| 15 | xAI / OpenAI o1 deliberation, DeepSeek self-verification papers (2025-26) | 最新 |

Adjacent: Felix / Automaton / Frank の WE-RAN-IT logs (記事 #1 #2 の流用)。

## 3. Reader / verdict (block [0] target)

- **Reader**: Claude Code / Cursor / OpenClaw を毎日使っていて、 AI に「テスト通った」「ビルド OK」「実装完了」と言われて何度か裏切られた人。「人間が確認しないと信じられない」を解消したい。
- **Pre-research hypothesis (to verify in WE-RAN-IT)**:
  - ✓ **verify ≠ eval** ですが、 両方要ります。 まず verify (= この1件) を入れる、 落ち着いたら eval (= 全体傾向) を入れる、 が現実的順序。
  - ✓ TODAY 入れるべき最小セット = ① superpowers `verification-before-completion` + `fact-checker` subagent ② PostToolUse hook (tsc / pyright / swiftc -parse) ③ Stop hook で「言ったこと裏取り」 ④ E2E (Web=Playwright / iOS=Maestro / agent=goldens)。
  - ✓ eval は CI 段階で promptfoo or Inspect。 30 分で入る。
  - ? agent-as-judge は「LLM が LLM を裁く」 — 何を信じてよいかの境界線が記事の山場。

## 4. Hamburger (PRE-RESEARCH skeleton — replaced after §6 workflow)

| Block | Working title | Notes |
|---|---|---|
| [0] | Verdict (text) | use-if / skip-if + 早見表 (cost / risk / install 時間 / 効果) |
| [1] | Hook | 「Claude が『テスト通りました』と言ったので merge したら、本番で落ちた」具体例。 自己検証なき自律 = ハルシネーション配信 |
| [2] | これは何の話か (everyone) | "verify"と"eval"は別物だが両方要る、 を 1 図で |
| [3] | 風景 (landscape) | verify 側 (verification-before-completion / fact-checker / hooks / Maestro / Playwright agent-mode) と eval 側 (promptfoo / Inspect / Braintrust / LangSmith / Ragas / DeepEval) を並べ、 どの問題にどっち、を表に |
| [4] | しくみ (engine) | verify ループ (IDENTIFY→RUN→READ→VERIFY→CLAIM) + hook 配線 + agent-as-judge の限界 + ground-truth の作り方 |
| [5] | WE RAN IT — anicca (= 自律 earn エージェント) | superpowers + fact-checker + PostToolUse hook + Stop hook を 1 instance に入れて 1 週間動かし、 嘘 (fake / mock / dry-run) を何件 catch したか、 reflex を何件減らしたか |
| [6] | WE RAN IT — aniccaios (= iOS affirmation アプリ) | Maestro flow + snapshot + accessibility audit + paywall E2E (Apple ID 必須は人間ゲートとして正直に書く) |
| [7] | 結論 (verdict expanded) | 入れるべきは誰、入れなくていいのは誰、 開発者の脳内モデル (= まず verify、 育ったら eval) |
| [8] | シリーズ次回予告 + 出典 | 次 = ? + brand manifesto |

Apply parent SSOT §11 PLAYBOOK verbatim (no em-dash 30, natural JP 31, define-on-first-use 39/54, gradations 42, cite everything 25, 出典 list, full block in review 44).

## 5. WE-RAN-IT protocol

### 5.1 Anicca (autonomous earn agent)
| Step | Action | Receipt |
|---|---|---|
| 1 | Pick one anicca instance (Hermes ~/.hermes or OpenClaw ~/.openclaw — choose lower-risk) | path + commit |
| 2 | Wire superpowers `verification-before-completion` + fact-checker subagent (already present, audit usage) | grep frequency in last 7-day logs |
| 3 | Add PostToolUse hook = tsc / pyright / swiftc -parse / node --check / cargo check / jq / bash -n per file extension | hook script path + 1 sample fire log |
| 4 | Add Stop hook = re-run all hooks on files edited in last 5 minutes + 5-claim audit | hook script + 1 sample fire |
| 5 | Run for 7 days; count (a) hallucinated symbol catches (b) fake test/build claims caught (c) net token cost increase | jsonl event log |

### 5.2 Aniccaios (iOS affirmation app)
| Step | Action | Receipt |
|---|---|---|
| 1 | Use existing Maestro flows in `aniccaios/` | flow paths |
| 2 | Run on simulator UDID-pinned (platform-gotchas) | xcrun command + first pass result |
| 3 | Add accessibility audit + snapshot diff via Maestro studio | flow file + diff sample |
| 4 | Document the unavoidable human gates (Apple ID sandbox tester for IAP, App Store review) — write them honestly | list with reasons (per HARD `feedback_fastlane_cannot_test_paywall`) |

Total spend cap: 0 USD (no infra), only Claude token spend during research workflow. Receipts → `docs/articles/research/2026-06-15-self-verification-receipts.md`.

## 6. Research workflow (Dynamic Workflow — fan-out → adversarial verify → synthesize)

Built per parent SSOT §11 Playbook + 2026-06-14 BP article rules. Foreground, structured-output, 1 run.

- **Phase A — FETCH (fan-out, Haiku-class)**: one agent per primary source row in §2 (≈15 sources). Each uses `firecrawl scrape <url> markdown` (HARD 0.23) + `gh api repos/<o>/<r>/contents/...` for repo files. Returns `{thesis, definition_of_verify, definition_of_eval, install_steps, code_signature_or_cli, founder_or_author_quote, primary_url}`.
- **Phase B — DICHOTOMY (1 Opus agent)**: synthesize a clean **"verify vs eval"** distinction from all FETCH outputs. Output must include: (i) one-paragraph definition each, (ii) Venn / matrix, (iii) when-to-use rules, (iv) named tools per side, (v) the 1 sentence Dais asked for (= "同じか別か").
- **Phase C — ADVERSARIAL VERIFY (3 verifiers per non-trivial claim)**: each verifier instructed to **REFUTE**. Vote ≥ 2/3 confirms. Drops shaky claims.
- **Phase D — HAMBURGER ASSEMBLY (1 Opus agent)**: produce final 9-block plan with paragraph-level guidance, 🎨V# image spots, cited 出典, 3 JP title candidates ≤ 30 chars.
- **Phase E — SKILL PATCH LIST**: produce a diff-shaped PR for `~/.openclaw/skills/ai-entity-article-writer/SKILL.md` (= new playbook rules learned from this piece — generalize, don't hard-code "verification").
- **Token budget**: target ≤ ~80k output tokens (more than #2 because eval landscape is broad).
- **Quarantine**: every Fetch agent is read-only; no agent writes to disk; main loop writes spec § 7 + § 8 from return values.

## 7. Workflow output — run `wf_936ea57e-264` (2026-06-15)

Workflow stats: **15/15 sources fetched / 12 claims posed / 11/12 (91.7%) survived adversarial 3-refuter verify**. Survival cutoff: 2-of-3 refuters fail to refute = claim stands. Single refuted claim: cwc-workshops eval-driven-agent-development variant names (the synthesizer fabricated `visual/typography/palette/density` — repo actually has `00-naive / 01-polish / 02-diagram / 03-qa-loop / 04-model-swap` and **5 tasks not 10**). Two-layer grader (programmatic + LLM-judge) was correct. **Treat the variant names + task count as the ground truth from the verifier**, not the synthesizer.

Full raw output preserved at workflow transcript dir; key fields below.

### 7.1 Dichotomy paragraph (the answer Dais asked for — verbatim)

> **verify と eval は「同じループの異なる段階」であり、no-human-in-loop を成立させるには両方が必須です。** 仮説どおり、両者は対立概念ではなく直交する役割を持ちます。**verify** は単一の実行に対して「今この成果物が本当に動いたか」を決定論的に確かめる per-execution の関門であり、Claude Code hooks (PostToolUse/Stop exit 2)、Playwright の healer エージェント、Maestro の `assertVisible`、Reflexion の外部 reward 信号がこの極にあります。一方 **eval** は多数のケース・モデル・プロンプトを横断して「平均的にどれだけ良いか」を測る offline scoring であり、Inspect AI の `Task(dataset, solver, scorer)`、Promptfoo、Autoevals、Ragas、DeepEval、Langfuse、OpenAI Evals がこの極にあります。Anthropic 公式の cwc-workshops は両者を明示的に橋渡しし「**evals で先に何が良いかを決め、verify で各実行が本当にそれを満たしたかを毎回確かめる**」二段構えを取り、Agent-as-a-Judge は両者を同一プリミティブ（trajectory を判定するエージェント）として統合可能であることを示しています。ですから「どちらか」ではなく「**eval で目標を定義し、verify で毎回それを強制する**」のが唯一の正解で、verify を捨てると幻覚が出口で止まらず、eval を捨てると何が良いかの定義そのものが消えます。

**One-sentence definitions:**
- **verify**: エージェントが今この瞬間に生成した単一の成果物が、実際に動いたか・要件を満たしたかを、決定論的なシグナル（compile/test/assertion/live UI/外部 reward）で per-execution に確かめ、失敗時にはその場で修復ループに戻す関門。
- **eval**: モデル・プロンプト・エージェント構成を、ラベル付きデータセットや多数のテストケース全体に対してオフラインで採点 (programmatic / LLM-as-judge / human) し、baseline からの delta を見て「どの構成が平均的に良いか」を意思決定する harness。

### 7.2 When-to-use matrix (sampled)

| 状況 | 使うもの | なぜ |
|---|---|---|
| コード/設定を1行 edit した直後 | verify | PostToolUse hook で tsc/lint を即時実行し、幻覚 import を出口で止める |
| エージェントが「完了」と宣言しようとした瞬間 | verify | Stop hook exit 2 で fresh evidence なしの完了宣言を物理的に拒否 |
| iOS/Android アプリの画面が本当に出るか確認 | verify | Maestro `assertVisible` / Playwright healer が live UI で実地確認 |
| プロンプト A と B のどちらが平均的に良いか決める | eval | Promptfoo/Inspect AI で test matrix を回し baseline 比較が必要 |
| 新モデルを既存パイプに差し替えて良いか判断 | eval | OpenAI Evals/Langfuse Datasets で多数ケースの delta を見ないと回帰が見えない |
| RAG/agent の品質回帰を CI で防ぐ | eval | DeepEval/Ragas が Pytest 風に閾値で gate でき再現性がある |
| spec 駆動で新 skill を作る最初の30秒 | both | cwc-workshops 流に先に eval を書き、実装後 verify で各実行を毎回確認 |
| 長時間自律エージェントを no-human-in-loop で運用 | both | eval で目標を固定し、verify で各 turn の幻覚と回帰を実行時に遮断 |

### 7.3 Tools by side (verified)

- **verify tools**: Claude Code hooks (PostToolUse/Stop exit 2) · Claude Code subagents (fact-checker/code-reviewer, read-only) · Maestro (`assertVisible`, YAML flow) · Playwright test-agents (planner/generator/healer) · Reflexion (external reward + verbal self-reflection) · cwc-workshops Phase 3 (`data-verify-*` / `window.__verify` DOM contract)
- **eval tools**: Inspect AI (Task/dataset/solver/scorer, UK AISI製) · Promptfoo (`promptfoo eval` / `redteam`) · Autoevals (Factuality LLM-as-judge) · Ragas (DiscreteMetric / `rag_eval`) · DeepEval (`deepeval test run`, G-Eval) · Langfuse (Datasets + LLM-as-a-judge + Code evaluators) · OpenAI Evals (`oaieval`, registry YAML — custom code 非受付) · cwc-workshops eval-driven-agent-development (`npm run eval -- --all --baseline`, 5 variants × 5 tasks 確認済) · Agent-as-a-Judge (DevAI 55 tasks / 365 hierarchical requirements)

### 7.4 Title candidates (JP, ≤ 30 chars, 3)

1. AIが「テスト通った」と嘘をつく夜に効く道具
2. verifyとevalは別物、両方ないと死ぬ
3. Claude Code hooksで「完了」を物理停止

### 7.5 Verdict box (block [0] target)

- **One-line**: verify と eval は別物ですが、no-human-in-loop を成立させるには両方が必須です: eval で何が良いかを定義し、verify で毎回それを強制します。
- **Who for**: Claude Code/Cursor/OpenClaw で自律エージェントを動かしていて、AI が「テスト通りました」「ビルド OK です」と嘘をつくのに焼かれた経験がある AI ビルダー。
- **Who not for**: プロンプトを手で 1 回ずつ叩いて目視で確認する単発利用者、または「LLM に自己採点させれば十分」と信じている人（外部 reward なしの self-eval は罠です）。

| label | value |
|---|---|
| verify 側コスト (Claude Code hooks) | 0円・即時。settings.json に PostToolUse+Stop hook を書き exit 2 を返すだけで「Prevents Claude from stopping」が公式に効く |
| verify 側コスト (Maestro/Playwright) | OSS 無料。Maestro=YAML 5 行 / Playwright=`npx playwright init-agents --loop=claude` 一発 |
| eval 側コスト (Promptfoo/Inspect AI/DeepEval) | OSS 無料 + 判定 LLM の API 代 + CI 時間。Promptfoo=Node ^20.20.0 ‖ >=22.22.0、DeepEval=Python>=3.9 |
| リスク: self-eval だけ | Reflexion 91% は外部 reward (compiler/unit test) 込みの数字、内部 LLM 単独だと幻覚を踏む |
| リスク: Agent-as-a-Judge | human baseline 並みの信頼性は DevAI 365 hierarchical requirements 付きの話、自家ベンチでは要件定義が必須 |
| 推奨 install 順序 | ① Claude Code hooks → ② Maestro/Playwright healer → ③ Promptfoo or Inspect AI → ④ DeepEval (CI gate) → ⑤ cwc-workshops 流 baseline 運用 |

### 7.6 9-block hamburger (one-line each — full guidance in workflow output)

| ID | Title | Sources |
|---|---|---|
| [0] | 結論（最初の1文） | cc-hooks, cwc-workshops, inspect-ai, promptfoo |
| [1] | 「テスト通りました」が嘘だった夜 | cc-hooks, zenn-gaogaoasia |
| [2] | この記事で溶かす誤解 | cwc-workshops, reflexion, cc-hooks |
| [3] | 地図: verify 側と eval 側の道具を全部置く | 全 14 sources |
| [4] | 心臓部: hook + fact-checker + Maestro + agent-as-judge の罠 | cc-hooks, cc-subagents, maestro, playwright-agents, reflexion, agent-as-judge |
| [5] | WE RAN IT: anicca (Node/api) で 1 日試した記録 | cc-hooks, cc-subagents, promptfoo, inspect-ai |
| [6] | WE RAN IT: aniccaios (Swift/iOS) で Maestro+DeepEval+人手の三段 | maestro, cc-hooks, deepeval, agent-as-judge |
| [7] | 結論: verify と eval は同じループの別工程です | cwc-workshops, reflexion, agent-as-judge, cc-hooks, maestro |
| [8] | 次回予告と出典一覧 | 全 15 sources |

### 7.7 Image spots

- `[IMG_HOOK]` — terminal: 「All tests pass. Build OK. Done!」直下に Xcode のビルドエラー赤バー「Cannot find 'AniccaLoginViewModel' in scope」が並ぶ二段レイアウト
- `[IMG_MAP]` — verify/eval ランドスケープ地図 (左=verify 側 / 右=eval 側 / 中央 cwc-workshops を橋として)
- `[IMG_ENGINE]` — settings.json hooks のコード + stderr → Claude context フローチャート
- `[IMG_ANICCAIOS_MAESTRO]` — iOS sim 画面と Maestro YAML を左右に並べ、`assertVisible` から該当テキストへ緑矢印
- `[IMG_LOOP]` — eval → 実装 → verify ループ 3 円図、中央「no-human-in-loop」

### 7.8 Series relationship (resolved 2026-06-15)

Article #3 (this) and Article #4 (`2026-06-15-article4-agent-eval-design.md`, Dais's other-instance spec) are **complementary, not overlapping**:
- **#3 = per-turn truth gate** (verify side): does THIS execution's output match what it claims? Hooks / Maestro / Playwright healer / fact-checker subagent.
- **#4 = long-term drift loop** (eval + observability + self-improvement side): is the agent getting better or worse over weeks? Langfuse / AgentOps / Promptfoo / Inspect AI / self-improvement loop.

The bridge: cwc-workshops "先に eval を書き、verify で毎回確認する" — #3 owns the right half of that sentence, #4 owns the left half. Article #3 in turn surfaces the eval landscape briefly (block [3]) so readers can navigate to #4.

## 8. Skill patch list (from workflow output)

Append to `~/.openclaw/skills/ai-entity-article-writer/SKILL.md` PLAYBOOK (current rules 1-15) as rules 16-21. Generalized; do NOT hard-code "verification".

### 8.1 PLAYBOOK appends (rules 16-21)

16. **Define each tool by its physical action** (exact CLI / SDK method / function signature), not by category. "eval framework" is useless; "Inspect AI: `Task(dataset, solver, scorer)` → `inspect eval task.py`" is testable. If you cannot show the verb-form (one shell call or one line of code) of a tool, you do not understand it yet — keep researching before mentioning it.
17. **When two concepts are commonly confused (X vs Y), TAKE A STANCE in paragraph 1** and defend it for the rest of the article. "It depends" / "both are valid" / "context-dependent" = automatic fail — rewrite until one declarative sentence answers "so which is it?". Allowed stances include "they are orthogonal axes of the same loop" or "X is a strict subset of Y".
18. **Adversarial-verify every numeric / named claim against its primary URL**: refute-by-default, confirm only on 2-of-3 independent source vote (primary repo + official docs + third independent mention). Numbers without citation get deleted. Track survival rate per article; <80% = research pass too shallow, redo. Article #3 baseline = 11/12.
19. **The hamburger has TWO 'WE RAN IT' blocks, not one**: one for a Node/web/api stack and one for a Swift/iOS/mobile stack (or the two most distant stacks for the topic). One stack alone is anecdote; two stacks across language + runtime is evidence of generality. If genuinely impossible, state that limitation in block [0].
20. **Open with a CONCRETE FAILURE NIGHT** (one block titled with a real moment, e.g.「テスト通りました」が嘘だった夜), not an abstract definition. Failure must be a real event from your own run (timestamp + what broke + what you believed vs what was true). No invented anecdotes — if you don't have one, you haven't run the topic enough yet.
21. **Include a 「この記事で溶かす誤解」 (misconceptions-dissolved) block** listing 3-5 specific wrong beliefs the reader probably holds, each one line as "X だと思っていた → 実は Y". Forces the writer to identify actual confusion (not just present information) and gives the reader a checkable promise.

### 8.2 Process changes

- **Step 2 (Deep research)**: add 'physical-action pass' — for every tool/library/concept you plan to name, write its one-line CLI/SDK verb-form BEFORE drafting. If you can't write it, keep researching.
- **Step 2 (Deep research)**: add 'misconception harvest' — collect 3-5 wrong-but-common beliefs via firecrawl on top hits + HN/Reddit/X threads. These feed the 誤解を溶かす block (rule 21).
- **Step 3 (Run it)**: require TWO distinct stacks per article (e.g. Node/api + Swift/iOS), not one. Capture receipts for both.
- **Step 4 (Draft)**: new block ordering — [0] verdict → [1] concrete failure night → [2] 誤解を溶かす → [3] landscape → [4] mechanism → [5a] WE RAN IT stack A → [5b] WE RAN IT stack B → [6] dichotomy/stance paragraph → [7] verdict expanded → [8] series hook + 出典.
- **Step 6 (Gate)**: add adversarial-verify pass — refute-by-default, ≥80% survival rate required, record in `state/article-NN-verify.json`.
- **Step 9 (Learn)**: when appending a PLAYBOOK rule, also record the article + block where the lesson was forged (e.g. 'rule 17 ← Article #3 dichotomy paragraph').

### 8.3 Description-field change (frontmatter)

Append after 'hamburger template': "Every piece commits to a STANCE on the field's central confusion (no it-depends), opens with a concrete failure moment, dissolves 3-5 named misconceptions, and earns its claims by running the topic end-to-end in TWO distant stacks (e.g. Node/api + Swift/iOS) with adversarial-verified primary-source citations (refute-by-default, ≥80% survival). Tools are named by their physical action (CLI/SDK verb-form), never by category alone."

## 9. Open items (resolve during execution)

- Is the zenn.dev article (Yuki Hattori / gaogaoasia) about "**verify**" or about "**long-running session ergonomics**"? Need to read to decide whether it's central or adjacent.
- Decide whether to run anicca verify wiring on Hermes (~/.hermes) or OpenClaw (~/.openclaw) — lowest blast radius wins.
- aniccaios paywall E2E = honestly write "Apple ID 必須 = human gate" per HARD `feedback_fastlane_cannot_test_paywall`. Don't fake it.

## 10. Sources for the parent series (carry over)
- Parent SSOT 2026-06-10 §11 (PLAYBOOK 1-54)
- Article #1 (Automaton) `docs/articles/2026-06-11-automaton-jp.md` — voice sample
- Article #2 (Frank) `docs/articles/2026-06-15-frank-jp.md` — voice sample (early)
