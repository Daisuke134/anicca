---
feature: anicca-self-improve-harness
phase: 1b
mode: strict
sources:
  - behavioral-spec.md (this feature, same directory) — REQ/INV/EDGE IDs referenced below
  - skills/earn/lib/genome.mjs + evolve.mjs — internal precedent for pure-fn/effectful-shell split and the `stripForbidden`/`evaluatePromotion` patterns reused here
  - eval-driven-earning/specs/verification-architecture.md — PROP-ID convention and tier-table format (adapted; PROP-DA*/PROP-M*/PROP-E4-E7 series NOT reused, per ch08 misattribution finding)
---

# Verification Architecture — anicca-self-improve-harness (Phase 1b)

## Purity Boundary Map

### Pure Core

Target module: `skills/earn/self-improve/lib/gate_math.py` (new, this feature). Invariants:
deterministic, referentially transparent, zero side effects, no I/O imports. Verified by an AST
import-scan test asserting no `import os / subprocess / pathlib / requests / urllib / socket`
inside this module (same technique as eval-driven-earning's NFR-ED1 / `test_eval_spine_no_io.py`).

| function | signature | why it is pure | REQ traced |
|---|---|---|---|
| `net_usd(gross_usd, cost_usd)` | `(float, float) → float` | linear arithmetic, mirrors `ledger.mjs::deriveLine`'s `earn_usdc − cost_usdc` formula exactly | REQ-GR2, REQ-EV1 |
| `apply_score_cap(raw_score, ceiling)` | `(float, float) → float` | `min(raw_score, ceiling)`, no branching on external state | REQ-RH1 |
| `is_implausible_jump(candidate_score, population_best, multiple=3.0)` | `(float, float, float) → bool` | pure numeric comparison over injected inputs (population_best is passed in, never read from disk here) | REQ-RH2 |
| `diff_in_scope(candidate_code, baseline_code, evolve_block_range)` | `(str, str, tuple[int,int]) → DiffScopeResult(in_scope: bool, out_of_scope_lines: list[int])` | pure whole-file-text comparison of the two full file strings outside the given line range — operates on the ACTUAL resulting file text (`child_code`, produced via either diff-apply or full-rewrite), never on openevolve's own diff/marker object (which is not trusted for this — see behavioral-spec.md "Scope of the strategy program") | REQ-DL2 |
| `scan_denylisted_imports(code_text, denylist_modules)` | `(str, list[str]) → list[str]` | pure static-text scan (regex/AST parse of a string), no filesystem access | REQ-DL4 |
| `checksums_match(before_hash, after_hash)` | `(str, str) → bool` | trivial equality; hash computation itself is effectful (below), this predicate is not | REQ-DL3 |
| `stage_gate(stage1_pass, stage2_pass, tripwire_clear, adversary_verdict)` | `(bool, bool, bool, Literal["PASS","FAIL","PENDING"]) → bool` | boolean AND over four injected inputs; mirrors `evolve.mjs::evaluatePromotion`'s decision-only-no-IO shape | REQ-RH4 |
| `beats_baseline(candidate_score, baseline_score)` | `(float, float) → bool` | strict `candidate_score > max(baseline_score, 0)`, copied verbatim from `evolve.mjs::evaluatePromotion`'s floor logic | REQ-RH4, EDGE-2 |

### Effectful Shell

| module / script | primary I/O surface | REQ traced |
|---|---|---|
| `skills/earn/self-improve/run_evolve.sh` (wrapper) | subprocess `openevolve-run.py` / `run_evolution`; writes `runs/<run_id>/` | REQ-OE1, REQ-OE6 |
| `skills/earn/self-improve/evaluator.py::evaluate/_stage1/_stage2` | reads historical fixture files (read-only); calls pure `net_usd`/`apply_score_cap`; NEVER calls `ledger.mjs`'s append path | REQ-EV1–EV7 |
| `skills/earn/self-improve/lib/scope_guard.py` | reads the candidate's RESULTING program file (`child_code` — the whole file text openevolve produced, via diff-apply or full-rewrite) and the frozen baseline file from disk, computes checksums, calls pure `diff_in_scope`/`scan_denylisted_imports`/`checksums_match`; invoked by `evaluator.py::evaluate_stage1` as its FIRST operation (REQ-DL5) — this is the sole enforcement mechanism (openevolve provides none of its own) | REQ-DL1–DL5 |
| `skills/earn/self-improve/lib/promote.py` | reads/writes the baseline strategy file; git commit (mirrors `evolve.mjs::promote`); invoked ONLY after `stage_gate(...) == True` | REQ-RH4 |
| adversary spawn (vcsdd-adversary Task invocation) | fresh-context subagent read of the candidate diff + artifacts trail; writes verdict to `reviews/<candidate_id>/verdict.json` | REQ-EV5, REQ-RH4, INV-7 |
| `skills/_shared/lib/ledger.mjs::readLedger` (existing, unmodified) | reads `earn-ledger.jsonl` for historical-baseline bootstrap only | INV-5, REQ-GR2 |

The pure layer forms a fully deterministic, directly-unit-testable core. The effectful shell
snapshots inputs (diff text, file bytes, ledger rows, adversary verdict) and passes them to the
pure layer; it never re-implements the pure layer's decision logic inline.

---

## Proof Obligations

| ID | Property (traces to REQ) | Tier | Method |
|---|---|---|---|
| PROP-SI-OE1 | No new hand-written evolution/selection module is added outside the openevolve wrapper (REQ-OE1) | deterministic | repo-scan CI check: no new top-level function matching `def (mutate|select_arm|evolve_step)` outside `skills/earn/self-improve/` and `skills/earn/lib/{genome,evolve}.mjs` (the pre-existing, unmodified prototype) |
| PROP-SI-OE2 | Every strategy program file has exactly one `# EVOLVE-BLOCK-START`/`END` pair (REQ-OE2) | deterministic | pytest: parse fixture files, count markers |
| PROP-SI-OE3 | EVOLVE-BLOCK content contains no denylisted identifiers by default on the SEED (unmutated) program (REQ-OE3, DL4) | deterministic | pytest over the initial program file |
| PROP-SI-OE4 | `config.yaml`'s `llm.api_base` is NOT a human-named key/subscription endpoint pattern (REQ-OE4) | deterministic | pytest: string/regex assertion against an allowlist of endpoint hosts |
| PROP-SI-OE5 | `config.yaml`'s `database.num_islands >= 2` (REQ-OE5) | deterministic | pytest: parse config.yaml |
| PROP-SI-OE6 | A killed/crashed openevolve subprocess leaves the baseline strategy file byte-identical (hash before == hash after) (REQ-OE6) | backtest | integration test: `SIGKILL` the subprocess mid-run against a real (small) historical fixture, compare file hashes |
| PROP-SI-OE7 | `run_evolve.sh`'s invocation is wired to a recurring, human-zero trigger: a launchd plist exists under `skills/earn/self-improve/launchd/` referencing `run_evolve.sh`, with a `StartInterval`/`StartCalendarInterval` key present and no step requiring manual/human invocation (REQ-OE7) | deterministic | pytest/repo-scan: parse the plist file (plistlib), assert the required scheduling key is present and `Program`/`ProgramArguments` points at `run_evolve.sh` |
| PROP-SI-EV1 | `net_usd(gross, cost) == gross - cost` for all float pairs; equals `ledger.mjs::deriveLine`'s `earn_usdc - cost_usdc` on the same inputs (REQ-GR2, EV1) | deterministic | pytest parametrize + cross-check against a Node subprocess computing `deriveLine` on identical fixture rows |
| PROP-SI-EV2 | `evaluate_stage1`'s configured historical window is a subset of the historical range `evaluate_stage2` draws its walk-forward window pairs from — stage1 is a cheap SUBSET-window filter, never an independent or larger-scope score (REQ-EV2) | deterministic | pytest: assert stage1's configured window bounds ⊆ the union of stage2's window-pair bounds over the same fixture |
| PROP-SI-EV3 | `evaluate_stage2` produces ≥3 non-overlapping walk-forward window pairs from a real historical fixture and its reported `combined_score` uses ONLY out-of-sample scores (REQ-EV3) | backtest | integration test over a real (or realistic synthetic) multi-period price/outcome fixture |
| PROP-SI-EV4 | A candidate with stage1 PASS / stage2 not-yet-run is `promotable == False` (REQ-EV4) | deterministic | pytest: call `stage_gate` with `stage2_pass=False` |
| PROP-SI-EV5 | `EvaluationResult.artifacts` contains a non-empty `adversary_verdict` key after ≥1 generation has completed (REQ-EV5) | backtest | integration test over a short (2-generation) real run |
| PROP-SI-EV6 | Corrupted/missing historical fixture → `evaluate_stage1` returns the documented fail-sentinel, no exception propagates (REQ-EV6) | deterministic | pytest with a deliberately corrupted fixture file |
| PROP-SI-EV7 | Static scan of `evaluator.py` finds zero calls to `appendLedger`/any ledger-write symbol (REQ-EV7) | deterministic | pytest: source-text scan of the evaluator module |
| PROP-SI-DL1 | Denylist constant (wallet keys, `.env`, `ledger.mjs`, spend caps, harness files, `anicca-agent-economy/**`) is present and non-empty, and matches the list in behavioral-spec.md REQ-DL1 verbatim (REQ-DL1) | deterministic | pytest: compare denylist constant to a fixture copy of the spec's list |
| PROP-SI-DL2 | `diff_in_scope` returns `in_scope=False` for a synthetic candidate FILE (the whole resulting text, both a diff-applied-result shape and a full-rewrite-result shape) whose text differs from baseline on one line outside the EVOLVE-BLOCK markers (REQ-DL2) | deterministic | pytest: hand-crafted whole-file candidate fixtures (both openevolve modes) vs. baseline, not a raw diff object |
| PROP-SI-DL3 | `checksums_match` (and its effectful caller `scope_guard.py`) aborts the run when the fixed-region hash changes between snapshots (REQ-DL3) | deterministic | pytest: mutate a byte outside the EVOLVE-BLOCK, assert abort path taken |
| PROP-SI-DL4 | `scan_denylisted_imports` flags a synthetic EVOLVE-BLOCK diff that adds `import ledger` / a wallet-key module reference (REQ-DL4) | deterministic | pytest: hand-crafted candidate source fixture |
| PROP-SI-DL5 | `evaluator.py::evaluate_stage1` calls `scope_guard.py`'s full check chain (DL2+DL3+DL4) BEFORE any backtest computation; a candidate that scope_guard rejects receives the documented fail-sentinel `combined_score` and `evaluate_stage2` is NEVER invoked for it (REQ-DL5) | deterministic | pytest: mock `scope_guard.check()` to reject, assert a stage2 mock has zero calls and the returned score equals the fail sentinel |
| PROP-SI-RH1 | `apply_score_cap(raw_score, ceiling)` never returns a value above `ceiling`, for any `raw_score` (REQ-RH1) | deterministic | Hypothesis property test |
| PROP-SI-RH2 | `is_implausible_jump(score, best, multiple)` returns `True` iff `score > multiple * best` (for `best > 0`) (REQ-RH2) | deterministic | pytest parametrize + Hypothesis |
| PROP-SI-RH3 | Static scan of `evaluator.py` finds zero imports of any order-execution module (`place_order`, `execute_swap`, `run.sh` invocation) (REQ-RH3) | deterministic | pytest: source-text scan, mirrors PROP-SI-EV7 |
| PROP-SI-RH4 | `stage_gate(s1, s2, tw, adv)` returns `True` iff ALL of `s1 ∧ s2 ∧ tw ∧ (adv == "PASS")`; any single `False`/non-PASS blocks promotion regardless of the other three (REQ-RH4) | deterministic | pytest: full truth-table (16 combinations) |
| PROP-SI-RH4b | A real candidate diff, evaluated end-to-end, is NOT merged into the baseline strategy file when a mocked adversary verdict is `FAIL`, even though stage1/stage2/trip-wire all pass (REQ-RH4, INV-7) | adversary | integration test with a stubbed adversary call returning `FAIL`; assert `promote.py` is never invoked |
| PROP-SI-RH5 | Two independent runs against the same historical corpus use DIFFERENT walk-forward window boundaries (rotation), verified by comparing the window-pair lists logged in each run's `evolution.log` (REQ-RH5) | backtest | integration test: run twice, diff window logs |
| PROP-SI-GR1 | `combined_score`'s source field is `net_usd(...)`, never a field named `judge_score`/`rubric_score` (REQ-GR1) | deterministic | pytest: static assertion on `EvaluationResult` construction call site |
| PROP-SI-GR3 | After a real run, the evolution process's own LLM-call cost is recorded in a budget/cost file (non-zero, incrementing) (REQ-GR3) | backtest | integration test over a real short run, read the cost file before/after |
| PROP-SI-GR4 | Repo-wide grep for `decideActivity`/`calibrationDrift`-named symbols returns zero NEW matches introduced by this feature (existing eval-driven-earning spec text is not touched/deleted by this check) (REQ-GR4) | deterministic | CI grep check scoped to `skills/earn/self-improve/**` |

---

## Test List (the five required end-to-end behaviors + supporting units)

1. **Denylist reject** (REQ-DL1/DL2/DL4/DL5, PROP-SI-DL2/DL4/DL5) — construct a candidate whole
   FILE (the resulting `child_code`, not a raw diff object) that (a) edits one line inside
   `ledger.mjs`-equivalent fixed-region text relative to baseline, and separately (b) adds
   `import ledger` inside the EVOLVE-BLOCK. Both MUST be rejected by `scope_guard.py`, invoked as
   `evaluate_stage1`'s first operation (REQ-DL5), BEFORE any backtest scoring runs (assert the
   backtest-scoring mock has zero calls and `evaluate_stage2` is never invoked).

2. **Held-out (out-of-sample) regress reject** (REQ-EV3/RH4, PROP-SI-EV3/RH4) — construct a
   candidate that scores well on the in-sample window but WORSE than baseline on the
   out-of-sample window(s). Assert `stage_gate(...)` returns `False` and `promote.py` is never
   invoked, even though the in-sample score alone would look like an improvement.

3. **Adversary DISAPPROVE → no merge** (REQ-RH4, PROP-SI-RH4b, INV-7) — stub the adversary call
   to return `FAIL` for a candidate that otherwise passes stage1 + stage2 + trip-wire. Assert
   `promote.py` is never invoked and the run's state records the candidate as rejected with the
   adversary's findings attached.

4. **Reward-hacking trip-wire** (REQ-RH1/RH2, PROP-SI-RH1/RH2) — construct a synthetic candidate
   scoring >3× the population's best-ever `combined_score`. Assert it is flagged
   `implausible_jump=True` and routed to adversary review rather than auto-promoted, AND that
   the raw score, wherever displayed/logged, is capped at the configured ceiling.

5. **≥1 accepted edit beats baseline** (REQ-EV1–EV5, REQ-RH4, REQ-GR1/GR2 — the Done-dimension
   acceptance evidence) — run a REAL openevolve evolution (small `--iterations`, real vendored
   openevolve, over the self-contained `pm_backtest_strategy.py` program — NOT `pick.py`, see
   behavioral-spec.md's Architecture Decision — with real or realistic-synthetic historical
   fixture data) end-to-end. Assert: (a) at
   least one generation's best candidate's stage2 walk-forward `combined_score` strictly beats
   the current baseline's floor (`beats_baseline` == True); (b) that candidate clears the
   trip-wire; (c) a fresh vcsdd-adversary run (not mocked, for THIS specific final acceptance
   test — mocking is only for tests 1–4 which target the gate logic in isolation) returns PASS;
   (d) `promote.py` is invoked exactly once and the resulting committed strategy file's
   EVOLVE-BLOCK differs from the seed only within the marked region (cross-check against
   PROP-SI-DL2's `diff_in_scope`). Evidence artifact: the run's `runs/<run_id>/` directory
   (best_program.py, evolution.log, EvaluationResult JSON dump, adversary verdict.json) — not a
   prose claim.

## Convergence Gate (strict mode)

No phase advances while any PROP-SI-* obligation above is `false`/unproven for a REQ marked
"Required for convergence" (all are, in this feature — there are no nice-to-have properties in
this spec; every REQ in behavioral-spec.md maps to at least one PROP-SI-* row above, satisfying
the criteria-coverage dimension of `vcsdd-converge`). Test 5 is the single piece of evidence that
satisfies the behavioral-spec.md "Done" table's `verification` row; tests 1–4 satisfy `test`
(RED→GREEN) together with the PROP-SI unit/property tests.
