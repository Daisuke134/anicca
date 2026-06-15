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

## 7. Workflow output (§7 filled by workflow return)

_Filled after first workflow run. Will contain: dichotomy paragraph, 9-block hamburger, image list, title candidates, sources._

## 8. Skill patch list (§8 filled by workflow return)

_Filled after first workflow run. Will contain proposed appends to `ai-entity-article-writer/SKILL.md` PLAYBOOK._

## 9. Open items (resolve during execution)

- Is the zenn.dev article (Yuki Hattori / gaogaoasia) about "**verify**" or about "**long-running session ergonomics**"? Need to read to decide whether it's central or adjacent.
- Decide whether to run anicca verify wiring on Hermes (~/.hermes) or OpenClaw (~/.openclaw) — lowest blast radius wins.
- aniccaios paywall E2E = honestly write "Apple ID 必須 = human gate" per HARD `feedback_fastlane_cannot_test_paywall`. Don't fake it.

## 10. Sources for the parent series (carry over)
- Parent SSOT 2026-06-10 §11 (PLAYBOOK 1-54)
- Article #1 (Automaton) `docs/articles/2026-06-11-automaton-jp.md` — voice sample
- Article #2 (Frank) `docs/articles/2026-06-15-frank-jp.md` — voice sample (early)
