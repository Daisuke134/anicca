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
  - Sutton & Barto, Reinforcement Learning: An Introduction, 2nd ed., §2.4 — https://web.stanford.edu/class/psych209/Readings/SuttonBartoIPRLBook2ndEd.pdf ("appropriate in a stationary environment, but not if the bandit is changing over time")
  - Lilian Weng, "Reward Hacking in Reinforcement Learning" — https://lilianweng.github.io/posts/2024-11-28-reward-hacking/
  - Anthropic, "Sycophancy to Subterfuge: Investigating Reward-Tampering in Large Language Models" — https://arxiv.org/abs/2406.10162
  - anicca-project/docs/loop-engineering/08-evidence-eval-driven-earning-verdict.md — external-citation audit (misattribution findings, BP-5-layer architecture, copy+tweak recommendation)
  - anicca-project/docs/loop-engineering/09-cobus-adoption-no-human-and-my-exit.md — human-zero gate replacement design (P-observe/P-branch/P-live staging)
integration:
  supersedes:
    - eval-driven-earning/specs/behavioral-spec.md Group DA (`decideActivity` Beta-bandit) — MISATTRIBUTED to ClawWork (repo has no bandit/epsilon code, gh search hits = 0); NOT carried into this feature
    - eval-driven-earning/specs/behavioral-spec.md Group EV5 (`calibrationDrift` Pearson-correlation) — MISATTRIBUTED to awesome-evals (term appears, algorithm does not); NOT carried into this feature
  does_not_replace_or_modify:
    - skills/earn/lib/genome.mjs / skills/earn/lib/evolve.mjs (the existing #19-EVOLVE JS prototype: random single/dual-knob mutation of pm-trade's MIN_EDGE/MIN_CONF/etc. + evaluatePromotion chain-verified gate). This prototype PRE-DATES the ch08 openevolve discovery, is NOT openevolve, and is OUT OF SCOPE to migrate or delete here (avoid scope creep). It IS cited as internal grounding for Group RH's promotion-gate design (its `evaluatePromotion` absolute-net-positive-floor + verified-only-counting pattern, and `stripForbidden`/FORBIDDEN_CAP_KEYS pattern).
    - skills/_shared/lib/ledger.mjs (isProfitable/appendLedger/readLedger/deriveLine) — read-only dependency, never edited by this feature
    - .vcsdd/features/anicca-agent-economy/** — NEVER edited by this feature (separate feature's ownership)
  integrates_at:
    - skills/_shared/lib/ledger.mjs::readLedger / isProfitable — the evaluator's historical-fitness bootstrap reads (never writes) earn-ledger.jsonl through this exact module; no parallel ledger reader is introduced
    - skills/earn/sol-trade/run.sh (SOL_TRADE_MAX_SPEND, default $0.25) — this feature's evaluation/evolution runs MUST NOT invoke this script; it only ever runs FROM the existing live sol-trade loop, never from openevolve
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

## Scope of "the strategy program" this phase covers

The evolvable unit is a **Python strategy-decision file** per earn engine that currently has
externally-tunable parameters/logic (initially: `skills/earn/polymarket-trade` — `pick.py`'s
candidate-selection logic, which already exposes `MIN_EDGE`/`MIN_CONF`/`RESOLVE_HORIZON_DAYS`/
`MAX_CANDIDATES` per `skills/earn/baseline-genome.json`; `sol-trade` and `hl-trade` are follow-on
work, out of scope for phase 1). The file has exactly one evolvable region:

```python
# EVOLVE-BLOCK-START
def score_candidate(candidate, market_features, config) -> float:
    ...  # entry/exit thresholds, sizing, timing — the ONLY thing openevolve may rewrite
# EVOLVE-BLOCK-END
```

Everything else in the file (data loading, ledger reads, wallet/order-execution calls, imports of
`ledger.mjs`-equivalent modules, the harness that calls this file) is FIXED — openevolve's own
scoping guarantee (ch08 agent3 finding) means it structurally cannot propose edits there, and
REQ-DL2/DL3 below add a defensive second check because "the tool guarantees it" is not, by
itself, a verified property of THIS deployment until tested.

## Grounded Interface (verified, not invented)

| openevolve concept | verified shape | our use |
|---|---|---|
| Evolvable region | `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END` in the program file | strategy decision logic lives here; ledger/wallet/execution code never does |
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

- **REQ-OE2** WHEN a strategy program file is created for evolution, THE SYSTEM SHALL mark
  exactly one evolvable region with `# EVOLVE-BLOCK-START` / `# EVOLVE-BLOCK-END`, and openevolve
  configuration SHALL be the unmodified upstream scoping behavior (no monkey-patch of openevolve's
  own diff-application code). Source: openevolve verified interface (see table above).

- **REQ-OE3** THE EVOLVE-BLOCK content SHALL contain ONLY strategy decision logic (candidate
  scoring / entry-exit thresholds / position sizing / timing) analogous in kind to the existing
  `genome.mjs::KNOB_KEYS` concept (MIN_EDGE, MIN_CONF, RESOLVE_HORIZON_DAYS, MAX_CANDIDATES) but
  expressed as evolvable CODE, not just numeric knobs — openevolve can propose logic changes
  (e.g. new features, different combination formulas), not only parameter nudges.

- **REQ-OE4** `config.yaml`'s `llm.api_base` SHALL point at a no-human-credential OpenAI-compatible
  endpoint (ClawRouter free-tier model or equivalent per-instance-funded endpoint). It SHALL NEVER
  be set to a human's personal API key or subscription (project-wide invariant, memory
  `feedback_earn_accounts_use_ai_own_email_not_dais_google` / colony no-human-loop mandate).

- **REQ-OE5** `database.population_size` and `database.num_islands` SHALL be configured to
  maintain ≥2 islands / diverse candidates (MAP-Elites), not collapse to a single running best.
  Rationale: a single accumulated-posterior selection is documented as fragile under a
  non-stationary reward (Sutton & Barto §2.4, "appropriate in a stationary environment, but not
  if the bandit is changing over time") — market conditions ARE non-stationary, so diversity
  (multiple surviving candidate lineages) is the openevolve-native answer to ch08 deviation (a).

- **REQ-OE6** WHEN the openevolve process crashes, times out, or is killed mid-run, THE SYSTEM
  SHALL treat the run as inconclusive: no candidate from that run is promoted, and the
  last-known-good baseline strategy file (outside any run's working directory) is left untouched.

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

### Group DL — Denylist enforced structurally by EVOLVE-BLOCK

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

- **REQ-DL2** WHEN a proposed program diff (openevolve's LLM-generated candidate) contains ANY
  change outside its file's own `# EVOLVE-BLOCK-START`/`END` markers, THE SYSTEM SHALL reject the
  candidate BEFORE evaluation. This is openevolve's own structural guarantee; this requirement
  adds a defensive second check (a diff-scope verifier run by our wrapper, not trusted to
  openevolve alone) mirroring the `stripForbidden()` pattern already proven in `genome.mjs`.

- **REQ-DL3** THE fixed (non-EVOLVE) region of each strategy program file SHALL be checksummed
  before and after every generation; a checksum mismatch SHALL abort the run immediately and
  route the offending candidate + diff to adversary review rather than silently discarding it.

- **REQ-DL4** WHEN a proposed diff, entirely inside the EVOLVE-BLOCK, adds an import of a
  denylisted module (e.g. `import ledger`, `from skills._shared.lib import ledger`, any wallet/
  key-file module, any live order-execution module such as `place_order`/`execute_swap`), THE
  SYSTEM SHALL reject the candidate via a static import-scan gate before evaluation (mirrors
  eval-driven-earning's NFR-ED1 AST-import-scan pattern, applied here to the strategy file's
  EVOLVE-BLOCK rather than to a pure-function module).

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
| INV-3 | Denylist (REQ-DL1) MUST be enforced structurally via EVOLVE-BLOCK scoping + the defensive diff-scope/checksum/import-scan checks (REQ-DL2–DL4); it is NEVER expressed as prose-only guidance to the evolving LLM |
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
| verification | Phase 5 hardening (`vcsdd-harden`): proof obligations below all discharged; a REAL openevolve run over ≥1 real historical window produces at least one candidate whose stage2 walk-forward `combined_score` beats the current `baseline-genome.json`-equivalent baseline, with a fresh adversary PASS on that specific diff — evidence = the run's output directory (best_program.py, evolution.log, EvaluationResult JSON), not a claim |

Strict-mode gate: no phase advances with any BLOCKING adversary finding open. Convergence
(`vcsdd-converge`) additionally checks finding diminishment across rounds, finding specificity,
criteria coverage (every REQ above has ≥1 proof obligation in verification-architecture.md), and
duplicate-finding detection, per project CLAUDE.md's GLVS Verify stage.

## UNVERIFIED

- The exact upstream openevolve config field names (`evaluator.cascade_thresholds` shape,
  `database.num_islands` default) are taken from the task's verified-interface summary and ch08's
  repo audit, not re-verified by this spec-writing pass against a freshly cloned copy — the
  implementation phase MUST re-confirm exact field names/types against the vendored openevolve
  source before writing `config.yaml`.
- `pick.py`'s exact function boundary for `score_candidate`-equivalent logic (the concrete
  EVOLVE-BLOCK contents for polymarket-trade) was not re-read line-by-line in this spec pass;
  implementation MUST confirm the smallest correct EVOLVE-BLOCK boundary inside `pick.py` before
  writing the initial program file.
