---
feature: eval-driven-earning
phase: 1b
mode: lean
sources:
  - earn-shared-skeleton/specs/verification-architecture.md (purity boundary and PROP-* conventions)
  - benchflow-ai/awesome-evals — pass@k / pass^k, Verifier's Law, calibration-drift methodology
  - HKUDS/ClawWork — TrackedProvider measurement contract, decide_activity pure-function guarantee
---

# Verification Architecture — eval-driven-earning (Phase 1b)

## Purity Boundary Map

The map below is the formal extension of the skeleton's purity boundary
(`earn-shared-skeleton/specs/behavioral-spec.md §Purity Boundary`).

### Pure Core

All functions in `~/anicca/skills/_shared/eval_spine.py`.
Invariants: deterministic, referentially transparent, zero side effects, no I/O imports.
Verified by: AST import scan (test_eval_spine_no_io.py) asserting no `import os / subprocess /
pathlib / requests / urllib` in the module.

| function | signature | why it is pure |
|---|---|---|
| `netWorth` | `(cost_usdc: float, income_usdc: float) → float` | linear arithmetic; no branching on external state |
| `isSolvent` | `(net_usdc: float, loss_start_ts: Optional[int], grace_window_secs: int, now_ts: int) → bool` | boolean predicate on numeric inputs; clock is a parameter, not `time.time()` |
| `decideActivity` | `(menu: list[MenuEntry], novelty_quota: float, budget: Budget, now_ts: int) → ActivityDecision` | selection over in-memory data; now_ts is a parameter |
| `rubricScore` | `(dimension_scores: dict[str,float], weights: dict[str,float], has_deliverable: bool, deliverable_required: bool) → RubricResult` | weighted average with hard override |
| `calibrationDrift` | `(scores: list[float], realized_usdc: list[float], min_pairs: int) → DriftResult` | statistical computation over two lists |
| `updateBanditArm` | `(arm: BanditArm, realized_usdc: float, usdc_scale: float) → BanditArm` | Beta distribution parameter update; returns new arm, does not mutate |

### Effectful Shell

| module / script | primary I/O surface |
|---|---|
| `tracked-provider.sh` | subprocess `claude`/ClawRouter; tmux pane read; `events/<pass_id>.jsonl` append |
| `survivalLedger.recompute()` (in `eval_spine_io.py`) | reads `cumulative.json`, `fx.json`; writes `survival.json` atomically |
| `rubricJudge.invoke()` (in `rubric-judge.py`) | LLM call (claude -p); reads `rubric-config.json` |
| `calibrationWriter.append()` | appends row to `calibration.jsonl` |
| `curationGate.run()` (in `curation-gate.sh`) | sandbox spawn; adversary subagent spawn (skeleton REQ-E4); writes `menu-curation.jsonl`, `reviews/curation-*/verdict.json` |
| `discoveryRadar.scan()` (in `discovery-radar.sh`) | firecrawl HTTP; `gh search`; appends `discovery.jsonl` |

The effectful shell is NEVER imported by tests for the pure layer.  Tests for the effectful
shell use subprocess mocks and tmp-file fixtures.

---

## Proof Obligations

All PROP IDs below are new to this feature (no collision with skeleton PROP-* series).

| ID | Property | Tier | Required for convergence | Tool |
|---|---|---|---|---|
| PROP-S1 | `netWorth(c, i) == i − c` for all float pairs | 0 | true | pytest parametrize |
| PROP-S2 | `netWorth(c, i) == −netWorth(i, c)` (antisymmetry) | 1 | true | Hypothesis |
| PROP-S3 | `isSolvent(net >= 0, ...) == True` for all non-negative net | 1 | true | Hypothesis |
| PROP-S4 | `isSolvent(net < 0, loss_start=T, grace=G, now=T+G+1) == False` | 0 | true | pytest |
| PROP-S5 | `isSolvent(net < 0, loss_start=T, grace=G, now=T+G−1) == True` (within grace) | 0 | true | pytest |
| PROP-S6 | `isSolvent(0.0, None, G, T) == True` (loss_start=None → not yet bankrupt) | 0 | true | pytest |
| PROP-S7 | `survival.json` recomputed twice from the same `cumulative.json` produces bit-identical files (idempotence) | 1 | true | Hypothesis (random cumulative inputs) |
| PROP-DA1 | `decideActivity` always returns exactly one mode in `{"exploit","explore"}` | 1 | true | Hypothesis |
| PROP-DA2 | When `menu` is empty → `ActivityDecision(mode="explore", pick=None, reason="discover-first")` | 0 | true | pytest |
| PROP-DA3 | When all `attempt_count < K_MIN_EXPLOIT` → `mode == "explore"` | 1 | true | Hypothesis |
| PROP-DA4 | When `novelty_quota > 0` and a `novelty_tried=False` entry exists → at least one in 100 synthetic wakes returns `mode="explore"` (quota simulation) | 1 | true | pytest simulation |
| PROP-DA5 | `decideActivity` in exploit mode selects the entry with highest `expected_usdc_per_wake` among eligible arms | 1 | true | Hypothesis |
| PROP-E1 | `rubricScore(has_deliverable=False, deliverable_required=True, ...) → verdict=="HARD_FAIL", score==0.0` | 0 | true | pytest |
| PROP-E2 | `rubricScore(weighted_score)` ∈ `[0.0, 1.0]` for all valid dimension_scores ∈ `[0,1]^n` and weights summing to 1 | 1 | true | Hypothesis |
| PROP-E3 | `rubricScore` with all weights summing to `!= 1.0` raises `ValueError` | 0 | true | pytest |
| PROP-E4 | `calibrationDrift(scores, realized_usdc, min_pairs)` where `len(scores) < min_pairs` → `DriftResult(sufficient_data=False, pearson_r=None, drift_detected=False)` | 0 | true | pytest |
| PROP-E5 | `calibrationDrift([0.9,0.8,0.7], [0.9,0.8,0.7], ...)` (scores ≡ outcomes, perfect rank order) → `pearson_r ≈ 1.0, drift_detected=False` | 0 | true | pytest |
| PROP-E6 | `calibrationDrift([0.9,0.1,0.5], [0.1,0.9,0.5], ...)` (inverse rank) → `pearson_r ≈ −1.0, drift_detected=True` | 0 | true | pytest |
| PROP-E7 | `calibrationDrift` with constant `realized_usdc=[0,0,0,...10+]` → `pearson_r=None` (undefined variance) → `drift_detected=False` (insufficient signal) | 0 | true | pytest |
| PROP-M1 | `updateBanditArm({alpha=1, beta=1}, realized_usdc=0, scale=1) → {alpha=1, beta=2}` | 0 | true | pytest |
| PROP-M2 | `updateBanditArm({alpha=1, beta=1}, realized_usdc=scale, scale=scale) → {alpha=2, beta=1}` | 0 | true | pytest |
| PROP-M3 | `updateBanditArm` always returns `alpha >= 1.0` and `beta >= 1.0` | 1 | true | Hypothesis |
| PROP-M4 | `expected_usdc_per_wake = alpha / (alpha+beta) × scale` holds after N sequential updates (convergence to empirical mean) | 1 | false (nice-to-have) | Hypothesis |
| PROP-C1 | A MenuEntry admitted to `menu.json` MUST have a corresponding `verdict.json` with `overallVerdict=="PASS"` in `reviews/curation-<skill_id>/output/` | 2 | true | integration test (file-system assertion) |
| PROP-EV3 | When a verifiable check returns `PASS`, `rubricScore` returns `PASS` regardless of mock judge score | 2 | true | integration test (mock judge stub) |
| PROP-EV3f | When a verifiable check returns `FAIL`, `rubricScore` returns `HARD_FAIL` regardless of mock judge score (e.g. 0.9) | 2 | true | integration test |

---

## Verification Strategy

### Tier 0 — No formal proof needed; trivially verifiable by parametric unit tests

Properties: PROP-S1, PROP-S4, PROP-S5, PROP-S6, PROP-DA2, PROP-E1, PROP-E3, PROP-E4,
PROP-E5, PROP-E6, PROP-E7, PROP-M1, PROP-M2.

These are closed-form arithmetic or single-branch boolean predicates.  A pytest parametrize
table exercises every stated example from the behavioral spec.  No fuzzing needed.

### Tier 1 — Property tests with Hypothesis (stateless pure functions; stateful simulation)

Properties: PROP-S2, PROP-S3, PROP-S7, PROP-DA1, PROP-DA3, PROP-DA4, PROP-DA5, PROP-E2,
PROP-M3.

**Hypothesis strategy:**

```python
# Example: PROP-S3
@given(st.floats(min_value=0, allow_nan=False, allow_infinity=False),
       st.floats(allow_nan=False),
       st.integers(min_value=0),
       st.integers(min_value=0))
def test_solvent_when_net_positive(net, income, grace, now):
    assume(net >= 0)
    assert isSolvent(net, None, grace, now) is True

# Example: PROP-DA1 — mode is always in {"exploit", "explore"}
@given(st.lists(menu_entry_strategy(), min_size=0, max_size=20),
       st.floats(min_value=0.0, max_value=1.0),
       st.sampled_from(Budget),
       st.integers(min_value=0))
def test_decide_activity_mode_valid(menu, quota, budget, now):
    result = decideActivity(menu, quota, budget, now)
    assert result.mode in {"exploit", "explore"}
```

PROP-S7 (idempotence of survival.json recompute) is verified by:
- generating random `cumulative.json` content via Hypothesis,
- calling `survivalLedger.recompute()` twice on it (reading from the same tmp file),
- asserting the two output files are byte-identical.

PROP-DA4 (novelty quota simulation):
- generate a synthetic menu with 5 entries, 4 with `novelty_tried=True`, 1 with `False`,
- run `decideActivity` 100 times with monotonically increasing `now_ts` (to avoid time-ties),
- assert `sum(1 for r in results if r.mode=="explore") >= ceil(0.1 × 100) == 10`.

### Tier 2 — Integration tests (multi-component, file-system, adversary stub)

Properties: PROP-C1, PROP-EV3, PROP-EV3f.

**PROP-C1 integration fixture:**
1. Stub `curation-gate.sh` so it writes a deterministic `verdict.json` with
   `overallVerdict="PASS"` for skill_id="test-skill".
2. Call `curationGate.admit("test-skill")`.
3. Assert `~/loops/gig/menu.json` contains an entry with `id="test-skill"`.
4. Assert `reviews/curation-test-skill/output/verdict.json` exists with `overallVerdict="PASS"`.
5. Assert no `admitted_at_ts=null` entries in menu.json after admission.

**PROP-EV3 / PROP-EV3f integration fixtures:**
```python
def test_verifiable_pass_overrides_low_judge():
    # verifiable check returns PASS; judge stub returns 0.2
    result = rubricEval("trading-polymarket", verifiable=True, judge_score=0.2)
    assert result.verdict == "PASS"

def test_verifiable_fail_overrides_high_judge():
    # verifiable check returns FAIL; judge stub returns 0.9
    result = rubricEval("trading-polymarket", verifiable=False, judge_score=0.9)
    assert result.verdict == "HARD_FAIL"
```

**Losing-arm-retired / winning-arm-doubled integration test (required for "Done"):**
```
1. Create menu with two entries: arm-A (alpha=1, beta=9, expected≈0.1×scale)
                                  arm-B (alpha=9, beta=1, expected≈0.9×scale).
2. Run decideActivity 10 times in FULL budget mode — verify arm-B is selected each time
   (exploit mode picks highest expected_usdc_per_wake).
3. Simulate 5 wakes of arm-A with realized_usdc=0.0 (losing); 5 wakes arm-B with
   realized_usdc=scale (winning).
4. After updates: arm-A has (alpha=1, beta=14); arm-B has (alpha=14, beta=1).
5. Assert arm-A.expected_usdc_per_wake < 0.1×scale (arm demoted toward retirement).
6. Assert arm-B.expected_usdc_per_wake > 0.9×scale (arm strengthened toward double-down).
7. Assert isSolvent remains True for this test ledger (income > cost in the winning scenario).
```

**Survival ledger E2E (required for "Done"):**
```
1. Write a minimal roi.jsonl row with token_cost_jpy=174 (real cost, model=sonnet).
2. Write a cumulative.json reflecting that cost; income=0.0.
3. Call survivalLedger.recompute() → survival.json.
4. Assert survival.json.cost_usdc ≈ 174 / FX_USDJPY.
5. Assert survival.json.net_usdc < 0.
6. Assert isSolvent(ledger.net_usdc, loss_start_ts=now, grace=7d, now=now) == True (within grace).
7. Now write an earnings.jsonl row with amount_usdc=0.5 (INV-7 verified, receipt_id present).
8. Call survivalLedger.recompute() again.
9. Assert survival.json.income_usdc == 0.5.
10. Assert survival.json.net_usdc == 0.5 − cost_usdc (may still be negative if cost > 0.5).
11. Assert netWorth(survival.json.cost_usdc, survival.json.income_usdc) == survival.json.net_usdc.
```

### Tier 3 — No-mock E2E (real slot run, required for final convergence)

Not specified as unit/integration tests — these are manual E2E verification steps run by
the builder after Green phase, per VCSDD Phase 5 / HARD 0.31:

1. **Cost measurement E2E**: Run one real gig slot wake; verify `events/<pass_id>.jsonl`
   contains at least one `event: "cost"` row with `token_source != "estimated"`.
2. **Survival ledger real row**: After the wake, verify `survival.json` has been updated with
   non-zero `cost_usdc` computed from the real token counts.
3. **decideActivity live pick**: Verify proactive-loop.sh step 5 logs the
   `ActivityDecision.mode` and `pick.id` from a real `decideActivity` call.
4. **Calibration record**: After a real action with a determined outcome (accepted or rejected),
   verify `calibration.jsonl` has a new row with `rubric_score` and `realized_usdc`.

---

## Fixture Corpus (adversary-required per behavioral-spec REQ-EV3)

The adversary review SHALL have access to these test fixtures to verify REQ-EV3 (Verifier's
Law) is correctly implemented:

| fixture | input | expected output |
|---|---|---|
| `fix_verifiable_pass_low_judge` | verifiable=PASS, judge_score=0.1 | PASS |
| `fix_verifiable_fail_high_judge` | verifiable=FAIL, judge_score=0.95 | HARD_FAIL |
| `fix_no_verifiable_high_judge` | verifiable=NotApplicable, judge_score=0.85 | PASS (judge wins) |
| `fix_no_verifiable_low_judge` | verifiable=NotApplicable, judge_score=0.25 | FAIL (judge wins) |
| `fix_hard_fail_no_deliverable` | deliverable_required=True, has_deliverable=False | HARD_FAIL regardless of judge |

---

## Module Map

```
~/anicca/skills/_shared/
├── eval_spine.py                  # PURE: netWorth, isSolvent, decideActivity, rubricScore,
│                                  #        calibrationDrift, updateBanditArm
├── eval_spine_io.py               # EFFECTFUL: survivalLedger.recompute() (reads files, writes survival.json)
├── tracked-provider.sh            # EFFECTFUL: TrackedProvider wrapper
├── rubric-judge.py                # EFFECTFUL: LLM rubric judge invocation
├── rubric-default.json            # DEFAULT rubric config (shipped with framework)
├── curation-gate.sh               # EFFECTFUL: curation gate runner (sandbox + adversary)
└── discovery-radar.sh             # EFFECTFUL: self-search radar

tests/eval_driven_earning/
├── test_eval_spine.py             # Tier-0 unit + Tier-1 Hypothesis tests (pure functions)
├── test_survival_ledger.py        # Tier-2 integration: recompute idempotence, E2E flow
├── test_decide_activity.py        # Tier-0/1: mode validity, quota simulation, exploit selection
├── test_rubric_score.py           # Tier-0/1: HARD_FAIL override, weight constraint, range
├── test_calibration_drift.py      # Tier-0/1: all calibration boundary conditions
├── test_bandit_arm.py             # Tier-0/1: alpha/beta update, convergence to mean
├── test_curation_gate.py          # Tier-2: admission condition, adversary stub, menu write
├── test_verifiable_priority.py    # Tier-2: fix corpus from Fixture Corpus table above
└── conftest.py                    # shared: tmp-dir fixtures, cumulative.json factory, menu factory
```

---

## Anti-Slop Rules (Adversary must check)

The adversary SHALL flag these patterns as critical defects:

1. **Impure pure layer** — any `import os / subprocess / pathlib / requests / time.time()` in
   `eval_spine.py` (the pure module).  Verified by: `grep -E "^import (os|subprocess|pathlib|
   requests|time)" eval_spine.py` returns 0 matches.

2. **Clock injection violation** — any `time.time()`, `datetime.now()`, or `time.monotonic()`
   inside `isSolvent` or `decideActivity` — `now_ts` MUST be a parameter, not read from the
   system clock inside the function.  Makes the function deterministic and testable without
   monkeypatching.

3. **Fake cost row** — any path that records a `cost-error` event and then falls through to
   record `cost_usdc=0` instead of escalating.  Zero cost for an unknown model is indistinguishable
   from "free" and defeats the survival ledger.

4. **Admission without verdict** — any path where `menu.json` gains a new entry whose
   `admitted_at_ts is NOT null` but no `reviews/curation-<skill_id>/output/verdict.json`
   with `overallVerdict=="PASS"` exists.

5. **Judge overriding verifiable check** — any code path where an LLM judge score can cause a
   verifiable-FAIL action to proceed, or prevent a verifiable-PASS action from proceeding.

6. **calibrationDrift raising on insufficient data** — must return `DriftResult(sufficient_data=False, ...)`,
   never raise an exception.

7. **discovery-radar importing secrets** — `discovery-radar.sh` MUST NOT read
   `~/.openclaw/.env::FOUNDER_WALLET_KEY` or `GOOGLE_LOGIN_*`.  Verified by grep of the script.

8. **human-touch surfaces in curation gate** — same check as skeleton REQ-J8: no Telegram,
   no `label=needs-human` gh issues in `curation-gate.sh`.
