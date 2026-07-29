"""Required test 5 (delegated task spec): a hand-crafted BETTER `score_candidate` variant yields a
higher RISK-ADJUSTED stage2 fitness than the baseline strategy's, with a non-negative worst-window
OOS, and the promotion gate (scope_guard PASS + beats_baseline + walk-forward non-regress) returns
True.

This proves the Done-condition-3 evaluator/promotion machinery DETERMINISTICALLY: real backtest
math (gate_math.net_usd + gate_math.risk_adjusted_score) over the real committed historical
fixture (strategies/fixtures/pm_history.csv), a real scope_guard.check() pass, and the real
stage_gate() boolean gate all wired together end-to-end. The REAL openevolve LLM-proposing run is
the NEXT stage (this stage builds and proves the deterministic core the LLM's candidates will be
evaluated against, per behavioral-spec.md's phase framing).

Close-loop revision (2026-07-08, Gap 2): `combined_score` for stage2/promotion is now a
Sharpe-like risk-adjusted metric (`gate_math.risk_adjusted_score`), not raw mean OOS net USD — see
evaluator.py's module docstring. The "better candidate" here changed from the prior revision's
`min_edge: 0.15 -> 0.24` (which is now the FROZEN BASELINE ITSELF — see next paragraph) to
`min_edge: 0.25 -> 0.26` + `max_stake: 12 -> 10`, a genuine selection and risk-cap change
against the current promoted baseline, not a leverage/stake-size-only change.

REAL PROMOTION (2026-07-08, commit a6f608c, capable-improver run): the openevolve-discovered
candidate that raised `min_edge`/`min_confidence`/added liquidity+price+horizon+combined-signal
filters and an adaptive stake multiplier (free/gpt-oss-120b, real fresh-Opus-adversary PASS) is now
the COMMITTED baseline `strategies/pm_backtest_strategy.py` itself — this file's own "baseline"
therefore already has a POSITIVE worst OOS window (~+2.38, not negative) and a materially higher
risk-adjusted score (~3.21, not ~1.26) than the earlier revision's simple threshold-only baseline.
Every literal/number below was re-derived directly off the REAL evaluator/fixture against this NEW
committed baseline (not invented, not carried over from the pre-promotion revision): baseline's
stage2 risk-adjusted score is ~3.208 (mean ~4.218, std ~1.315, worst OOS ~+2.375); the
That candidate's current risk-adjusted score is higher with mean up, spread down, and a positive
worst window — a genuine Pareto improvement over an already-good baseline, not a variance trick.
A pure-leverage variant of
baseline (same thresholds, base_stake scaled 5.0 -> 20.0) is verified elsewhere
(test_risk_adjusted_fitness.py) to score IDENTICALLY to baseline under this metric, proving
leverage alone cannot pass this test.
"""
import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math, scope_guard


def _better_candidate_code() -> str:
    return patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.26)'),
        ('config.get("max_stake", 12.0)', 'config.get("max_stake", 10.0)'),
    )


def test_better_candidate_scope_guard_passes():
    baseline_code = read_baseline_code()
    candidate_code = _better_candidate_code()

    ok, reason = scope_guard.check(candidate_code, baseline_code)

    assert ok is True
    assert reason == "scope-guard-pass"


def test_better_candidate_beats_baseline_on_stage2_walk_forward(tmp_path):
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    baseline_stage2 = evaluator.baseline_stage2_score()
    candidate_stage2 = evaluator.evaluate_stage2(candidate_path)["combined_score"]

    assert candidate_stage2 > 0.0
    assert gate_math.beats_baseline(candidate_stage2, baseline_stage2) is True


def test_better_candidate_has_non_negative_worst_window_oos(tmp_path):
    """Strengthens the beats-baseline claim above: the improvement must not be an aggregate-only
    artifact (EDGE-5) — the WORST individual OOS window must itself be non-negative. Post-promotion
    (commit a6f608c) the committed baseline ALREADY has a non-negative worst OOS window (the real
    promoted candidate fixed that exact problem for the pre-promotion baseline) — this test now
    asserts the candidate PRESERVES that non-negative-worst-window property while still improving
    mean/std further, not that it fixes a still-losing baseline (there is no longer one)."""
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    baseline_stage2 = evaluator.evaluate_stage2(evaluator.BASELINE_PATH)
    candidate_stage2 = evaluator.evaluate_stage2(candidate_path)

    assert baseline_stage2["worst_window_oos_net_usd"] >= 0.0, (
        "the committed baseline (post-promotion) is expected to already have a non-negative worst "
        "OOS window — if this regresses, the committed strategies/pm_backtest_strategy.py itself "
        "changed underneath this test"
    )
    assert candidate_stage2["worst_window_oos_net_usd"] >= 0.0
    # Genuine Pareto improvement, not just a variance trick: mean up AND spread down.
    assert candidate_stage2["mean_oos_net_usd"] > baseline_stage2["mean_oos_net_usd"]
    assert candidate_stage2["std_oos_net_usd"] < baseline_stage2["std_oos_net_usd"]


def test_full_evaluate_cascade_and_promotion_gate_return_true(tmp_path):
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    result = evaluator.evaluate(candidate_path)

    assert result["stage1_pass"] is True
    assert result["stage2_pass"] is True  # this IS beats_baseline, computed inside evaluate()
    assert result["combined_score"] > 0.0
    assert result["worst_window_oos_net_usd"] >= 0.0
    assert "scope_guard_verdict" in result["artifacts"]
    assert result["artifacts"]["scope_guard_verdict"] == "scope-guard-pass"

    promotable = gate_math.stage_gate(
        stage1_pass=result["stage1_pass"],
        stage2_pass=result["stage2_pass"],
        tripwire_clear=True,
        adversary_verdict="PASS",
    )
    assert promotable is True


def test_promotion_gate_is_not_trivially_true_adversary_fail_still_blocks(tmp_path):
    """Strengthens the "returns True" claim above: the SAME passing candidate must NOT be
    promotable if the fresh adversary verdict is not PASS (REQ-RH4 step 3) or if the trip-wire is
    not clear (REQ-RH4 step 2) — the gate is a real conjunction, not a constant."""
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)
    result = evaluator.evaluate(candidate_path)
    assert result["stage1_pass"] is True and result["stage2_pass"] is True  # re-confirm preconditions

    blocked_by_adversary = gate_math.stage_gate(
        stage1_pass=result["stage1_pass"],
        stage2_pass=result["stage2_pass"],
        tripwire_clear=True,
        adversary_verdict="FAIL",
    )
    blocked_by_tripwire = gate_math.stage_gate(
        stage1_pass=result["stage1_pass"],
        stage2_pass=result["stage2_pass"],
        tripwire_clear=False,
        adversary_verdict="PASS",
    )

    assert blocked_by_adversary is False
    assert blocked_by_tripwire is False
