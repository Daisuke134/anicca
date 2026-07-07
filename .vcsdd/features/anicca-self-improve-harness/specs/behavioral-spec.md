---
feature: anicca-self-improve-harness
phase: 1b
mode: strict
sources:
  - algorithmicsuperintelligence/openevolve (github.com/algorithmicsuperintelligence/openevolve, 6.6k★, Apache-2.0) — the self-improve MECHANISM (EVOLVE-BLOCK markers, evaluate()/EvaluationResult, cascade stage1/stage2, config.yaml, run_evolution)
  - HKUDS/ClawWork (github.com/HKUDS/ClawWork, 8.2k★) — TrackedProvider real-cost, economic_tracker.get_net_worth()/is_bankrupt() survival-ledger concept
  - benchflow-ai/awesome-evals (github.com/benchflow-ai/awesome-evals, 685★) — Verifier's Law ("a verifiable reward is a rubric function that runs real code against ground truth")
  - Jason Wei, "Asymmetry of Verification and Verifier's Law" — https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law
  - Marcos Lopez de Prado, "The Three Types of Backtests" — https://www.hillsdaleinv.com/uploads/The_Three_Types_of_Backtests.pdf
  - Freqtrade docs, Backtesting — https://www.freqtrade.io/en/stable/backtesting/ ("backtesting will never replace running a strategy in dry-run mode")
  - Sutton & Barto, Reinforcement Learning — An Introduction, 2nd ed., §2.4 — https://web.stanford.edu/class/psych209/Readings/SuttonBartoIPRLBook2ndEd.pdf ("appropriate in a stationary environment, but not if the bandit is changing over time") — used ONLY for REQ-GR4's recency-weighting citation; NOT used to justify `num_islands` (see openevolve configs/README.md below — corrected per iteration-1 spec-review GROUNDING finding #2)
  - algorithmicsuperintelligence/openevolve `configs/README.md` (cloned + read directly, this worktree/scratchpad) — "Island-Based Evolution Parameters... proper evolutionary diversity... num_islands — 3-10 for most problems (more = more diversity)"; `README.md` — "Island-Based Architecture — Multiple populations prevent premature convergence" / "Diversity maintenance — MAP-Elites prevents convergence" — openevolve's OWN, correctly-fit rationale for `database.num_islands`
  - algorithmicsuperintelligence/openevolve `openevolve/controller.py`, `openevolve/prompt/templates.py`, `openevolve/process_parallel.py`, `openevolve/utils/code_utils.py` (cloned + read directly) — verified — `_load_initial_program()` reads the WHOLE file (`f.read()`); the LLM prompt shows the ENTIRE `current_program`; `apply_diff()` SEARCH/REPLACEs against the whole `parent.code`; full-rewrite mode sets `child_code = new_code` (the whole file); `parse_evolve_blocks()` exists but is never called — EVOLVE-BLOCK markers provide NO structural enforcement in real openevolve
  - Lilian Weng, "Reward Hacking in Reinforcement Learning" — https://lilianweng.github.io/posts/2024-11-28-reward-hacking/
  - Anthropic, "Sycophancy to Subterfuge — Investigating Reward-Tampering in Large Language Models" — https://arxiv.org/abs/2406.10162
  - anicca-project/docs/loop-engineering/06-harness-engineering-weng.md — "① STOP の cautionary result" — "STOP improved performance with GPT-4 but DEGRADED with weaker models (GPT-3.5, Mixtral)... The base model must be capable enough" — the weak-improver-model risk this feature's REQ-OE4 (free-tier LLM) creates, and Weng's own prescribed mitigation ("Evaluator/permission should sit OUTSIDE the loop that evolves harness")
  - anicca-project/docs/loop-engineering/08-evidence-eval-driven-earning-verdict.md — external-citation audit (misattribution findings, BP-5-layer architecture, copy+tweak recommendation)
  - anicca-project/docs/loop-engineering/09-cobus-adoption-no-human-and-my-exit.md — human-zero gate replacement design (P-observe/P-branch/P-live staging); §4's LOOP 1 diagram ("Schedule→self-Triage→...→自merge→Monitor→Seed") — LOOP 1 vs LOOP 2 disambiguation for /goal condition (5)
  - anicca-project/.claude/rules/git-workflow.md — "マージ — 検証（adversary PASS + E2E green）後に agent が実行...人間の承認待ちなし" — the standing human-zero self-merge process LOOP 1 (this feature's own dev cycle) already follows
integration:
  supersedes:
    - eval-driven-earning/specs/behavioral-spec.md Group DA (`decideActivity` Beta-bandit) — MISATTRIBUTED to ClawWork (repo has no bandit/epsilon code, gh search hits = 0); NOT carried into this feature
    - eval-driven-earning/specs/behavioral-spec.md Group EV5 (`calibrationDrift` Pearson-correlation) — MISATTRIBUTED to awesome-evals (term appears, algorithm does not); NOT carried into this feature
  does_not_replace_or_modify:
    - skills/earn/lib/genome.mjs / skills/earn/lib/evolve.mjs (the existing #19-EVOLVE JS prototype — random single/dual-knob mutation of pm-trade's MIN_EDGE/MIN_CONF/etc. + evaluatePromotion chain-verified gate). This prototype PRE-DATES the ch08 openevolve discovery, is NOT openevolve, and is OUT OF SCOPE to migrate or delete here (avoid scope creep). It IS cited as internal grounding for Group RH's promotion-gate design (its `evaluatePromotion` absolute-net-positive-floor + verified-only-counting pattern, and `stripForbidden`/FORBIDDEN_CAP_KEYS pattern).
    - skills/earn/polymarket-trade/pick.py — read-only DESIGN reference only (the numeric-threshold SHAPE of MIN_EDGE/MIN_CONF/RESOLVE_HORIZON_DAYS/MAX_CANDIDATES informs the seed strategy's scoring formula). pick.py itself is NEVER the evolvable file, is NEVER imported/invoked by evaluator.py, and is not modified by this feature — see "Architecture Decision" section below (pick.py is a live multi-model-consensus + network-fetching script, not a pure backtestable function; it also contains wallet/order-adjacent imports in the same file, which this feature's design keeps away from the evolving LLM entirely by not using pick.py as the evolvable unit)
    - skills/_shared/lib/ledger.mjs (isProfitable/appendLedger/readLedger/deriveLine) — read-only dependency, never edited by this feature
    - .vcsdd/features/anicca-agent-economy/** — NEVER edited by this feature (separate feature's ownership)
  integrates_at:
    - skills/_shared/lib/ledger.mjs::readLedger / isProfitable — the evaluator's historical-fitness bootstrap reads (never writes) earn-ledger.jsonl through this exact module; no parallel ledger reader is introduced
    - skills/earn/sol-trade/run.sh (SOL_TRADE_MAX_SPEND, default $0.25) — this feature's evaluation/evolution runs MUST NOT invoke this script; it only ever runs FROM the existing live sol-trade loop, never from openevolve
  out_of_scope_this_phase:
    - Integrating the LIVE skills/earn/polymarket-trade/pick.py (multi-model-consensus + live market-data fetch) as the evolvable unit. This requires a cached-historical-consensus replay design (recording pick.py's real consensus outputs over time into a fixture the evaluator can replay deterministically) that is NOT specified or built by this feature. Deferred to a later phase. This phase's evolvable unit is instead a NEW, self-contained, pure, backtestable strategy program over historical data — see "Architecture Decision" below. This phase still satisfies /goal condition (3) (≥1 accepted bounded edit beats baseline on backtest/paper) because the self-contained program is a real, runnable artifact evaluated on real/realistic historical data, not a mock.
---

# Behavioral Specification — anicca-self-improve-harness (Phase 1a/1b)

## Purpose

Build LOOP 2's self-improve mechanism (09-cobus-adoption §P2, execution-notes-self-improve.md P1)
using **openevolve as the sole evolution engine** — not a hand-rolled bandit, not a hand-rolled
mutation loop. This corrects the ch08-audited failure of the prior `eval-driven-earning` design
(Group DA / Group EV5 = misattributed invention) by building on openevolve's REAL, verified
interface (`# EVOLVE-BLOCK-START/END`, `evaluate()→EvaluationResult`, cascade stage1/stage2,
`config.yaml`) and grounding fitness in on-chain/backtest realized USD (Verifier's Law), never an
LLM judge score.

This phase is **paper/backtest only**. No live order execution is introduced or invoked by this
feature. Promotion to live capital is a LATER phase (09 §2, "P-live") gated on this phase's
evidence (≥1 accepted edit that beats baseline on held-out data) plus a fresh adversary PASS.

### /goal condition (5) disambiguation — LOOP 1 vs LOOP 2 (this feature is LOOP 2's mechanism only)

"LOOP 1's one human-zero cycle self-merges" refers to a DIFFERENT loop than the one this feature
builds. Per docs/loop-engineering/09 §4's diagram: **LOOP 1** = claude-p's own dev cycle
(Schedule → self-Triage → worktree Implementer → fresh adversary → 自merge → Monitor → Seed) —
i.e. THIS FEATURE'S OWN branch, built and self-merged the standard project way. **LOOP 2** =
Franklin's/the earn-engine's self-improve mechanism, which is what this spec's REQ-OE*/EV*/DL*/RH*
groups actually build. Condition (5) is resolved as follows (see new REQ-OE7):
(a) this feature's OWN branch self-merges per the STANDING project process (`.claude/rules/
git-workflow.md`: adversary PASS + E2E green → agent merges, `gh pr merge --merge
--delete-branch`, no human approval wait) — that is LOOP 1's one human-zero cycle, already
satisfied by following normal project process, not a new mechanism this feature must build; (b)
SEPARATELY, LOOP 2's recurring trigger (what causes `run_evolve.sh` to run again and again with
zero human) is a real requirement of THIS feature and previously had no REQ — REQ-OE7 below fixes
that gap explicitly.

## Architecture Decision — the evolvable unit is NOT `pick.py`

`skills/earn/polymarket-trade/pick.py`, read directly from the worktree, is a **live,
multi-model-consensus, network-fetching script** ("NOTHING about WHICH market or WHICH side is
hardcoded here... The MODEL decides" via `AIAnalyzer.consensus_analysis` — 3 live BlockRun model
calls — plus `fetch_active_markets`/`get_smart_money_summary`, both live network calls). It is
**not** a pure `score_candidate(candidate, market_features, config) -> float` over pre-fetched
features; its core judgment IS a live LLM-consensus call. Making it openevolve-evolvable and
backtestable as-is would require either (a) caching/replaying historical consensus outputs per
candidate window, or (b) redefining the evolvable unit to exclude the consensus call — neither is
specified here, and specifying (a) is a nontrivial data-pipeline project of its own.

**Decision for this phase:** the evolvable unit is a **NEW, self-contained, deterministic Python
strategy program**, `skills/earn/self-improve/strategies/pm_backtest_strategy.py`, that is NOT
`pick.py` and NEVER imports or invokes it. Its EVOLVE-BLOCK contains a PURE decision function —

```python
# EVOLVE-BLOCK-START
def score_candidate(candidate, market_features, config) -> float:
    ...  # entry/exit thresholds, sizing, timing — the ONLY thing openevolve may rewrite
# EVOLVE-BLOCK-END
```

— operating ONLY on historical market/outcome features the evaluator itself loads as a read-only
fixture (REQ-EV1/EV7); no network call, no LLM call, no I/O of any kind is reachable from inside
the EVOLVE-BLOCK. The numeric-threshold SHAPE of `pick.py`'s existing knobs (`MIN_EDGE`,
`MIN_CONF`, `RESOLVE_HORIZON_DAYS`, `MAX_CANDIDATES`, per `skills/earn/baseline-genome.json`)
informs the seed function's initial scoring formula as a design analogy only — this is a NEW
artifact, not a copy of or wrapper around `pick.py`. Integrating the LIVE `pick.py` is explicitly
OUT OF SCOPE this phase (see frontmatter `out_of_scope_this_phase`); `sol-trade` and `hl-trade`
equivalents are also out of scope for phase 1.

This design has a second benefit beyond backtestability: because the new strategy file contains
NO wallet/order-execution-adjacent imports at all (unlike `pick.py`, which combines judgment logic
with `AGENT_HOME`-based wallet/execution-adjacent `src.*` modules in the very same file that would
otherwise be shown whole to the free-tier improver LLM every generation — see REQ-OE4's STOP-risk
discussion), the free-tier LLM is never shown wallet-adjacent code to begin with.

## Scope of "the strategy program" this phase covers

The evolvable unit (per the Architecture Decision above) is the self-contained
`pm_backtest_strategy.py` file. It has exactly one evolvable region — the `score_candidate`
function shown above. Everything else in the file (historical-fixture loading declarations, the
harness that calls this file) is FIXED.

**openevolve itself provides NO structural enforcement of this boundary.** Verified directly
against the real algorithmicsuperintelligence/openevolve source: `controller.py`'s
`_load_initial_program()` reads the WHOLE file (`with open(...) as f: return f.read()`), not just
the marked region; `prompt/templates.py`'s `DIFF_USER_TEMPLATE` shows the LLM the ENTIRE
`current_program` with no instruction to respect the markers at all ("Focus on making targeted
changes" is the only guidance given); `process_parallel.py`'s diff-based path calls
`apply_diff(parent.code, llm_response, ...)`, a SEARCH/REPLACE match against the ENTIRE
`parent.code`, not scoped to marker line-ranges; and the full-rewrite path
(`diff_based_evolution: false`, a real documented config option) does `child_code = new_code` — a
literal whole-file replacement with zero scoping. `parse_evolve_blocks()` exists in
`utils/code_utils.py` and is exported, but is NEVER called from `process_parallel.py`,
`controller.py`, or `api.py`'s main iteration path — it is dead code with respect to enforcement.
`# EVOLVE-BLOCK-START`/`END` are an **LLM-facing prompt convention only**, not a technical
boundary. **100% of the actual enforcement is this feature's own `scope_guard.py` wrapper**
(REQ-DL2–DL5 below), which operates on the ACTUAL resulting candidate file text (`child_code`,
regardless of whether openevolve used diff-based or full-rewrite mode) compared against the frozen
baseline file — never on openevolve's own marker/diff machinery, which is not trusted for this at
all.

## Grounded Interface (verified, not invented)

| openevolve concept | verified shape | our use |
|---|---|---|
| Evolvable region | `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` in the program file | strategy decision logic lives here; ledger/wallet/execution code never does. **NOTE**: openevolve itself does not enforce this boundary (markers are an LLM-facing prompt convention only, verified against real source — see "Scope of the strategy program" below); enforcement is entirely this feature's own `scope_guard.py` |
| Evaluator | `def evaluate(program_path) -> EvaluationResult(metrics={"combined_score": float, ...}, artifacts={...})` | `combined_score` = backtested net USD; `artifacts` carries adversary verdict text back to the LLM prompt |
| Cascade | `evaluate_stage1(program_path)`, `evaluate_stage2(program_path)`, `evaluator.cascade_thresholds` in config | stage1 = quick small-window backtest (cheap filter); stage2 = walk-forward on held-out windows |
| Runner | `python openevolve-run.py <initial_program.py> <evaluator.py> --config config.yaml --iterations N` or `from openevolve import run_evolution` | invoked by a wrapper script under `skills/earn/self-improve/`; never invoked ad hoc |
| Config | `max_iterations`, `llm.{primary_model,api_base}`, `database.{population_size,num_islands}`, `evaluator.{timeout,cascade_thresholds}` | `llm.api_base` MUST point at a no-human-credential endpoint (ClawRouter free tier or equivalent); `database.num_islands` ≥ 2 for MAP-Elites diversity |

## EARS-Format Functional Requirements

### Group OE — openevolve integration

- **REQ-OE1** THE SYSTEM SHALL use openevolve (`openevolve-run.py` / `run_evolution`) as the ONLY
  mechanism that proposes strategy edits. No new hand-written mutation/promotion code path SHALL
  be added as a substitute (rationale: ch08 finding — a hand-rolled Beta-bandit was invented and
  falsely attributed to ClawWork; the fix is copy+tweak of a real, star-verified engine, not a
  second bespoke one). Source: docs/loop-engineering/08 §C; github.com/algorithmicsuperintelligence/openevolve.

- **REQ-OE2** WHEN the self-contained strategy program file (`pm_backtest_strategy.py`, per the
  Architecture Decision above — NOT `pick.py`) is created for evolution, THE SYSTEM SHALL mark
  exactly one evolvable region with `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END`, and openevolve
  configuration SHALL be the unmodified upstream scoping behavior (no monkey-patch of openevolve's
  own diff-application code). Source: openevolve verified interface (see table above). These
  markers are a prompt convention for the LLM only (see "Scope..." above) — REQ-DL2/DL5's
  `scope_guard.py` is what actually enforces the boundary.

- **REQ-OE3** THE EVOLVE-BLOCK content SHALL contain ONLY strategy decision logic (candidate
  scoring / entry-exit thresholds / position sizing / timing) analogous IN SHAPE to the existing
  `genome.mjs::KNOB_KEYS` concept (MIN_EDGE, MIN_CONF, RESOLVE_HORIZON_DAYS, MAX_CANDIDATES) but
  expressed as evolvable CODE, not just numeric knobs — openevolve can propose logic changes
  (e.g. new features, different combination formulas), not only parameter nudges. This is a design
  analogy only; the EVOLVE-BLOCK lives in the NEW `pm_backtest_strategy.py` file, never in
  `pick.py` itself (Architecture Decision above).

- **REQ-OE4** `config.yaml`'s `llm.api_base` SHALL point at a no-human-credential OpenAI-compatible
  endpoint (ClawRouter free-tier model or equivalent per-instance-funded endpoint). It SHALL NEVER
  be set to a human's personal API key or subscription (project-wide invariant, memory
  `feedback_earn_accounts_use_ai_own_email_not_dais_google` / colony no-human-loop mandate).
  **BP-conformance rationale (Weng STOP warning):** pointing the IMPROVER LLM at a free/cheap
  endpoint is exactly the "weaker model" regime Lilian Weng's STOP finding warns degrades
  self-improvement quality — "STOP improved performance with GPT-4 but DEGRADED with weaker models
  (GPT-3.5, Mixtral)... The base model must be capable enough" (docs/loop-engineering/
  06-harness-engineering-weng.md, "① STOP の cautionary result"). This feature's mitigation
  follows Weng's own prescribed fix ("Evaluator/permission should sit OUTSIDE the loop that
  evolves harness"): the EVALUATOR is fully deterministic and NEVER an LLM judge (REQ-EV1,
  Verifier's Law), and the PROMOTION gate (REQ-RH4 step 3) is a strong model (Sonnet 5, per this
  project's model-assignment table — cheaper than Opus at equivalent adversarial performance,
  memory `feedback_adversary_sonnet5_and_ai_self_explore_repos`) sitting entirely outside the
  evolving loop. The weak improver LLM only ever PROPOSES candidates; it never scores or approves
  its own work — matching Weng's "evaluator/permission outside the loop" prescription exactly.

- **REQ-OE5** `database.population_size` and `database.num_islands` SHALL be configured to
  maintain ≥2 islands / diverse candidates (MAP-Elites), not collapse to a single running best.
  Rationale: this is openevolve's OWN, correctly-fit rationale for islands — "Island-Based
  Architecture: Multiple populations prevent premature convergence" / "Diversity maintenance:
  MAP-Elites prevents convergence" (openevolve README.md), and `configs/README.md`'s own parameter
  guideline ("num_islands: 3-10 for most problems (more = more diversity)") — anti-premature-
  convergence diversity maintenance for evolutionary search, NOT a non-stationarity fix. The
  actual answer to non-stationary market conditions (ch08 deviation (a)) is REQ-EV3/RH5's
  rotated walk-forward windows (Lopez de Prado), not the islands mechanism — islands are kept
  because openevolve's own docs recommend them for search-diversity, a separate, real benefit.

- **REQ-OE6** WHEN the openevolve process crashes, times out, or is killed mid-run, THE SYSTEM
  SHALL treat the run as inconclusive: no candidate from that run is promoted, and the
  last-known-good baseline strategy file (outside any run's working directory) is left untouched.

- **REQ-OE7** (resolves /goal condition (5), "LOOP 1's one human-zero cycle self-merges" — see
  the disambiguation note under Purpose) THE recurring invocation of `run_evolve.sh` (LOOP 2's
  mechanism) SHALL be triggered with ZERO human action, concretely: a launchd job — a plist under
  `skills/earn/self-improve/launchd/ai.anicca.self-improve-evolve.plist`, following this repo's
  existing launchd pattern (e.g. `skills/self/reddit-loop/launchd/*.plist`,
  `skills/earn/clip/launchd/*.plist`), loaded via `launchctl bootstrap`/`load` — with a
  `StartInterval` or `StartCalendarInterval` key that invokes `run_evolve.sh` directly, on a
  recurring schedule, with no manual/human invocation step anywhere in the path. THE SYSTEM SHALL
  NOT depend on a human manually running `run_evolve.sh`. This is DISTINCT from LOOP 1's
  self-merge (this feature's own dev branch, merged via the standing project process —
  `.claude/rules/git-workflow.md`, no new mechanism needed): REQ-OE7 covers LOOP 2's run trigger,
  which had no REQ before this revision.

### Group EV — Evaluator (backtest realized $, cascade, walk-forward)

- **REQ-EV1** `evaluate(program_path)` SHALL return `EvaluationResult.metrics["combined_score"]`
  equal to backtested net USD = gross_usd − cost_usd, computed ONLY from historical data the
  evaluator itself loads as a read-only fixture. `combined_score` SHALL NEVER be an LLM judge's
  subjective score. Source: Jason Wei, Verifier's Law (objective/fast/scalable/low-noise/
  continuous) — https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law;
  benchflow-ai/awesome-evals README ("a verifiable reward is a rubric function that runs real
  code against ground truth").

- **REQ-EV2** `evaluate_stage1(program_path)` SHALL run a quick backtest over a small historical
  window and reject (score below `evaluator.cascade_thresholds[0]`) candidates that are clearly
  unprofitable before any expensive stage2 run — the standard openevolve cascade pattern.

- **REQ-EV3** `evaluate_stage2(program_path)` SHALL run walk-forward validation: fit/select on
  window W_i, score on the immediately-following OUT-OF-SAMPLE window W_{i+1}, repeated across
  ≥3 non-overlapping window pairs drawn from history, and the reported `combined_score` for
  promotion purposes SHALL be the aggregate (e.g. mean) of the out-of-sample scores only — never
  the in-sample fit score. Source: Lopez de Prado, "The Three Types of Backtests" ("walk-forward
  testing... only a single path is tested... risk of overfitting" if done naively) —
  https://www.hillsdaleinv.com/uploads/The_Three_Types_of_Backtests.pdf.

- **REQ-EV4** A candidate that passes `evaluate_stage1` alone (no stage2 run yet, or stage2
  below `cascade_thresholds[1]`) SHALL NOT be eligible for promotion — stage1 is a cheap filter,
  not a promotion gate.

- **REQ-EV5** `EvaluationResult.artifacts` SHALL include the fresh vcsdd-adversary verdict text
  (PASS/FAIL + findings) for the prior generation's best candidate, so the NEXT generation's LLM
  prompt is steered by adversary feedback in addition to `combined_score` (this is exactly
  openevolve's documented `artifacts` side-channel use — ch08 agent3 finding).

- **REQ-EV6** WHEN historical data for a requested window is missing or fails to parse, THE
  SYSTEM SHALL return a fail-sentinel `combined_score` (e.g. `-inf` or a documented minimum) for
  that stage rather than raising an unhandled exception — openevolve must never crash mid-run on
  one bad data window.

- **REQ-EV7** The evaluator's historical-data loader SHALL be read-only: no code path inside
  `evaluate`/`evaluate_stage1`/`evaluate_stage2` SHALL write to `earn-ledger.jsonl` or any other
  live-system state file. Fitness computation and ledger mutation are structurally different code
  paths (this is also the Group RH sandboxing requirement, restated here as a data-boundary rule).

### Group DL — Denylist enforced structurally by our OWN `scope_guard.py` wrapper (NOT by openevolve)

- **REQ-DL1** THE following SHALL NEVER be inside an EVOLVE-BLOCK region, nor otherwise editable
  by an openevolve-proposed diff, under any strategy program file this feature creates:
  - wallet private keys and key files: `ANICCA_SOLANA_PRIVATE_KEY` / `ANICCA_EVM_PRIVATE_KEY` env
    vars, `~/.automaton/wallet.json`, `~/.automaton/solana.json`, `~/.blockrun/.solana-session`
    (per `skills/earn/lib/resolve-identity.mjs`'s documented resolution order)
  - any `.env` file
  - `skills/_shared/lib/ledger.mjs` (`isProfitable`, `appendLedger`, `readLedger`, `deriveLine`)
    and any equivalent ledger-write path
  - spend caps: `SOL_TRADE_MAX_SPEND` and any other money-safety constant (mirrors
    `genome.mjs::FORBIDDEN_CAP_KEYS` — `MAX_BET_SIZE`, `MAX_PASS_SPEND`, `POLY_MIN_ORDER`)
  - the harness/runner itself: `openevolve-run.py` invocation wrapper, `config.yaml`, the
    evaluator's I/O shell (as opposed to its pure scoring math)
  - `.vcsdd/features/anicca-agent-economy/**` (a separate feature's ownership; never touched by
    this feature's tooling, human or automated)

- **REQ-DL2** WHEN a candidate's resulting program file (`child_code` — the ACTUAL file text after
  openevolve applies its change, whether via diff-based `apply_diff()` or full-rewrite
  `child_code = new_code`; NOT the LLM's raw diff/SEARCH-REPLACE text, which does not even exist
  as a line-scoped object in full-rewrite mode) differs from the frozen baseline file ANYWHERE
  outside the exact byte range originally bounded by `# EVOLVE-BLOCK-START`/`END` in the baseline,
  THE SYSTEM SHALL reject the candidate BEFORE evaluation. **This wrapper check (`scope_guard.py`)
  IS the entire enforcement mechanism, not a defensive second check on top of an openevolve
  guarantee** — openevolve provides no enforcement of its own (verified: see "Scope of the
  strategy program" above). `scope_guard.py`'s comparison logic mirrors the `stripForbidden()`
  pattern already proven in `genome.mjs` (defensive stripping regardless of what a maliciously or
  accidentally crafted candidate contains), but operates on whole-file text diffing, not on a
  parsed knob list.

- **REQ-DL3** THE fixed (non-EVOLVE) region of each strategy program file SHALL be checksummed
  before and after every generation; a checksum mismatch SHALL abort the run immediately and
  route the offending candidate + diff to adversary review rather than silently discarding it.
  (This is a fast pre-check using a hash of the same fixed-region text REQ-DL2 diffs in full; both
  operate on the actual resulting file, never on openevolve's diff/marker machinery.)

- **REQ-DL4** WHEN a candidate's EVOLVE-BLOCK content (verified in-scope by REQ-DL2) adds an
  import of a denylisted module (e.g. `import ledger`, `from skills._shared.lib import ledger`,
  any wallet/key-file module, any live order-execution module such as
  `place_order`/`execute_swap`), THE SYSTEM SHALL reject the candidate via a static import-scan
  gate before evaluation (mirrors eval-driven-earning's NFR-ED1 AST-import-scan pattern, applied
  here to the strategy file's EVOLVE-BLOCK rather than to a pure-function module).

- **REQ-DL5** `evaluate_stage1(program_path)` SHALL invoke `scope_guard.py`'s full check chain
  (REQ-DL2 diff-scope, REQ-DL3 checksum, REQ-DL4 import-scan) as the FIRST operation, before any
  backtest computation runs. WHEN `scope_guard.py` rejects a candidate for ANY reason, THE SYSTEM
  SHALL immediately return `EvaluationResult.metrics["combined_score"]` set to a fail-sentinel
  (consistent with REQ-EV6's fail-sentinel convention — e.g. `0.0` or a documented minimum, never
  a value that could beat baseline) and SHALL NOT proceed to backtest scoring or
  `evaluate_stage2` for that candidate; the rejection reason SHALL be recorded in
  `EvaluationResult.artifacts["scope_guard_verdict"]`. This is the concrete wiring that makes
  `scope_guard.py` openevolve's actual gate, not a separate out-of-band check that could be
  bypassed by a run configuration that skips it.

### Group RH — Reward-hacking defenses

- **REQ-RH1** `combined_score` SHALL be capped at a fixed ceiling per generation (reward
  capping) so a single implausible outlier candidate cannot dominate selection. Source: Lilian
  Weng, "Reward Hacking in Reinforcement Learning" (Amodei et al.'s defenses, incl. reward
  capping) — https://lilianweng.github.io/posts/2024-11-28-reward-hacking/.

- **REQ-RH2** WHEN a candidate's stage2 `combined_score` exceeds a fixed multiple (e.g. 3×) of
  the population's best-ever stage2 score, THE SYSTEM SHALL flag it as an implausible-jump
  trip-wire and route it to adversary review BEFORE any promotion — it SHALL NOT be
  auto-accepted purely because it scores highest. Source: Anthropic, "Sycophancy to Subterfuge"
  (agents "generalize zero-shot to directly rewriting their own reward function") —
  https://arxiv.org/abs/2406.10162.

- **REQ-RH3** Strategy code inside the EVOLVE-BLOCK SHALL have NO order-execution capability and
  NO ledger-write capability at evaluation time. `evaluate*()` SHALL call the strategy's scoring
  function in a pure, backtest-only context; any live order-execution code (`place_order.py`,
  `execute_swap.py`, `run.sh`) lives entirely outside the EVOLVE-BLOCK/evaluator boundary and is
  NEVER imported or invoked by evaluator code. This is the sandbox half of "decision vs. ledger
  write are separate" (ch08 §B item (b) / BP layer L4).

- **REQ-RH4** Promotion (merging a candidate's EVOLVE-BLOCK into the live/paper baseline strategy
  file) SHALL require, in order: (1) stage2 walk-forward PASS (REQ-EV3/EV4), (2) trip-wire clear
  (REQ-RH2), (3) fresh vcsdd-adversary PASS on the diff + its `artifacts` verdict trail. The
  MINIMUM numeric bar for (1) SHALL be at least as strict as the existing, already-proven
  `evolve.mjs::evaluatePromotion` gate: the candidate must be net-positive in absolute terms
  (not merely "less negative than baseline") AND must beat baseline's floor
  (`max(baseline_score, 0)`) — this internal pattern is kept because it is real, tested code
  already enforcing exactly the Goodhart-resistant floor ch08 recommends.

- **REQ-RH5** A candidate that improves `combined_score` by overfitting to the SPECIFIC backtest
  window boundaries used in one run (e.g. a threshold that happens to fire only inside that
  window) SHALL be caught by REQ-EV3: window pairs are drawn fresh (rotated/expanded) on each
  run, so a candidate cannot memorize one fixed window across generations. Source: Lopez de
  Prado (walk-forward overfitting risk, cited above).

### Group GR — Grounded elements kept from prior audit

- **REQ-GR1** Fitness SHALL satisfy Verifier's Law (objective, fast, scalable, low-noise,
  continuous reward) — `combined_score` = realized/backtest USD IS this; an LLM judge score MAY
  appear only inside `artifacts` as auxiliary/explanatory signal, NEVER as `combined_score`
  itself. Source: Jason Wei, Verifier's Law (URL above); benchflow-ai/awesome-evals.

- **REQ-GR2** The survival-ledger accounting semantics (net = income − cost) SHALL be the basis
  of `combined_score`: concretely, the evaluator's backtest cost model SHALL use the SAME
  `earn_usdc − cost_usdc = net_usdc` semantics already defined in
  `skills/_shared/lib/ledger.mjs::deriveLine`, applied to historical/backtest data rather than
  live data during this phase. Source: HKUDS/ClawWork `economic_tracker.py`
  (`get_net_worth()`/`is_bankrupt()`) — github.com/HKUDS/ClawWork.

- **REQ-GR3** Real compute/token cost incurred BY the evolution process itself (openevolve's own
  LLM calls to generate candidates) SHALL be counted as a cost against this feature's own budget
  ledger — it SHALL NOT be treated as free. Source: HKUDS/ClawWork TrackedProvider (real per-call
  cost measurement) — same repo as REQ-GR2.

- **REQ-GR4** The misattributed originals from `eval-driven-earning` — the Beta-bandit
  `decideActivity` (Group DA) and the Pearson-correlation `calibrationDrift` (Group EV5) — SHALL
  NOT be included, ported, or re-derived-with-a-new-name in this feature. If a LATER feature
  needs cross-strategy allocation, it SHALL cite a genuine bandit source (e.g. Sutton & Barto with
  explicit recency-weighting/sliding-window per their §2.4 non-stationarity warning) rather than
  reusing eval-driven-earning's spec text; if judge-calibration is needed, it SHALL cite a real
  calibration methodology (e.g. Hamel Husain, "LLM-as-a-Judge") rather than reusing Group EV5.
  Source: docs/loop-engineering/08-evidence-eval-driven-earning-verdict.md §A rows 3 and 6.

## Global Invariants (MUST / NEVER)

| # | Invariant |
|---|---|
| INV-1 | MUST be zero human in the loop and zero human credential anywhere in this feature's run path (config, keys, approvals) |
| INV-2 | MUST use openevolve as the self-improve mechanism; MUST NOT hand-write a substitute evolution/selection algorithm |
| INV-3 | Denylist (REQ-DL1) MUST be enforced ENTIRELY by this feature's own `scope_guard.py` wrapper (whole-file diff-scope comparison against the frozen baseline REQ-DL2, fixed-region checksum REQ-DL3, static import/path scan REQ-DL4, wired as evaluator stage1's first operation REQ-DL5). `# EVOLVE-BLOCK-START`/`END` markers themselves provide NO technical/structural enforcement in real openevolve (verified: `controller.py`'s `_load_initial_program` reads the whole file via `f.read()`; `prompt/templates.py` shows the LLM the ENTIRE `current_program` with no marker-respecting instruction; `process_parallel.py`'s `apply_diff` matches against the whole `parent.code`; full-rewrite mode sets `child_code = new_code` — the entire file, no scoping; `parse_evolve_blocks()` exists but is dead code, never called from the real generation/evaluation path) — the markers are an LLM-facing convention/hint ONLY. This invariant is NEVER expressed as prose-only guidance to the evolving LLM; `scope_guard.py`'s checks run against the ACTUAL resulting candidate file, not the LLM's raw diff/instruction text, and are the sole enforcement mechanism (not a backup to any openevolve-native guarantee, because none exists) |
| INV-4 | MUST NEVER edit `.vcsdd/features/anicca-agent-economy/**` |
| INV-5 | The ONLY shared interface between this feature and the live earn system is `earn-ledger.jsonl`, read exclusively via `skills/_shared/lib/ledger.mjs` (`readLedger`/`isProfitable`); no second parallel ledger reader/writer is introduced |
| INV-6 | This phase is paper/backtest ONLY: no code in this feature invokes `skills/earn/sol-trade/run.sh`, `skills/earn/polymarket-trade/place_order.py`, or any other live order-execution path. `SOL_TRADE_MAX_SPEND` remains at its current value (0 for this feature's own runs — the harness never sets or relies on a nonzero spend cap) for the duration of this phase |
| INV-7 | Every "good"/"done" judgment on a candidate or on this feature as a whole is made by a fresh-context vcsdd-adversary PLUS an external citation — never by the builder's own vibes (project rule: memory `feedback_never_claim_good_without_external_citation`) |
| INV-8 | genome.mjs / evolve.mjs (the pre-existing JS prototype) are read-only references for this feature; this feature does not modify them |

## Edge Cases

- **EDGE-1** Zero historical data available for a given engine (e.g. a brand-new market type):
  `evaluate_stage1` returns the fail-sentinel (REQ-EV6); the run reports "insufficient data,"
  and is NOT treated as a promotion-blocking failure of the harness itself — it blocks only that
  engine's evolution until historical fixtures exist.
- **EDGE-2** openevolve proposes a candidate identical to the current baseline (no-op diff):
  evaluated normally; if scored, it neither passes nor fails the beats-baseline bar (REQ-RH4) —
  ties are treated as "does not beat baseline," consistent with `evolve.mjs::evaluatePromotion`'s
  strict `>` comparison.
- **EDGE-3** The adversary is unavailable/errors when REQ-RH4 step (3) is due: promotion is
  BLOCKED (fail-closed), never silently skipped; the candidate sits in a pending-review state.
- **EDGE-4** A candidate's diff modifies only comments/whitespace inside the EVOLVE-BLOCK (no
  behavior change): REQ-DL2/DL4 do not reject it (no denylisted access), but REQ-RH4 will not
  promote it either unless it independently clears stage2 + trip-wire + adversary (a no-op
  functional change cannot "beat baseline" per EDGE-2's tie rule).
- **EDGE-5** Two generations propose candidates that both look net-positive but on
  NON-overlapping backtest windows (survivorship/selection artifact): REQ-EV3's fixed-window
  rotation requires ≥3 windows per stage2 run specifically to prevent a single lucky window from
  producing a false promotion.

## "Done" / 4-D Convergence

| dimension | condition |
|---|---|
| spec | this document + verification-architecture.md; fresh-context vcsdd-adversary `vcsdd-spec-review` verdict = PASS (strict mode: zero BLOCKING findings, all findings resolved or explicitly deferred with rationale) |
| test | RED phase: denylist-reject, held-out-regress-reject, adversary-DISAPPROVE→no-merge, reward-hacking trip-wire, and ≥1-accepted-edit-beats-baseline tests all written and failing for the right reason; GREEN: all passing |
| impl | openevolve vendored under `~/anicca/` (or referenced as a pinned dependency); `skills/earn/self-improve/` wrapper (strategy program w/ EVOLVE-BLOCK, evaluator.py, config.yaml) present and runnable end-to-end on real historical fixtures |
| impl review (harness's OWN source, distinct from the per-candidate runtime gate below) | a standard VCSDD Phase-3 `vcsdd-adversary` review of THIS FEATURE'S OWN implementation files (`scope_guard.py`, `evaluator.py`, `gate_math.py`, `run_evolve.sh`, `promote.py`, `config.yaml`) — per project rule `.claude/rules/dev-workflow.md` (codex-review + vcsdd-adversary after 5+ files implemented, before commit/PR/release) — returns PASS. This is a DIFFERENT adversary invocation than REQ-RH4 step (3)'s per-candidate runtime gate (which reviews individual openevolve-proposed strategy diffs, not this feature's own code); satisfying REQ-RH4 alone does NOT satisfy this row |
| verification | Phase 5 hardening (`vcsdd-harden`): proof obligations below all discharged; a REAL openevolve run over ≥1 real historical window produces at least one candidate whose stage2 walk-forward `combined_score` beats the current `baseline-genome.json`-equivalent baseline, with a fresh adversary PASS on that specific diff (REQ-RH4 step 3, the per-candidate runtime gate) — evidence = the run's output directory (best_program.py, evolution.log, EvaluationResult JSON), not a claim |

Strict-mode gate: no phase advances with any BLOCKING adversary finding open. Convergence
(`vcsdd-converge`) additionally checks finding diminishment across rounds, finding specificity,
criteria coverage (every REQ above has ≥1 proof obligation in verification-architecture.md), and
duplicate-finding detection, per project CLAUDE.md's GLVS Verify stage.

## UNVERIFIED

- RESOLVED this revision (was UNVERIFIED in iteration-1): the exact upstream openevolve config
  field names were re-verified against a freshly cloned copy of the real repo (this worktree's
  scratchpad clone) — `openevolve/config.py`'s `EvaluatorConfig.cascade_thresholds: List[float] =
  [0.5, 0.75, 0.9]` (default) and `DatabaseConfig.num_islands: int = 5` (default) both confirmed
  directly by reading `config.py`. Implementation still MUST re-confirm these against whichever
  exact commit/tag is vendored under `~/anicca/` at implementation time, in case upstream has
  since changed defaults.
- `pick.py`'s exact function boundary is NO LONGER the open question it was in the prior spec
  iteration — this revision resolves it as an explicit Architecture Decision (`pick.py` is not the
  evolvable file at all; see above). What remains genuinely unverified/deferred to implementation:
  the concrete historical PM market/outcome fixture format and source
  `pm_backtest_strategy.py`'s evaluator will load (real historical resolution data export vs. a
  realistic synthetic fixture) is not pinned by this spec pass — implementation MUST source or
  construct this fixture and confirm it is sufficient for ≥3 non-overlapping walk-forward window
  pairs (REQ-EV3) before writing `evaluator.py`.
- The cached-historical-consensus replay design needed to LATER integrate the live `pick.py` (see
  frontmatter `out_of_scope_this_phase`) is not designed at all in this phase — a future feature
  must specify it from scratch before attempting that integration.
