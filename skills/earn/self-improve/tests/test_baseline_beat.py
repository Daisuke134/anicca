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
`min_confidence: 6.0 -> 8.0` (which does not hold up on the regenerated fixture) to
`min_edge: 0.15 -> 0.24` — a GENUINE selection change (concentrating on the strongest-signal rows
of `strategies/fixtures/pm_history.csv`'s documented true edge, see
`strategies/fixtures/generate_fixture.py`), not a leverage/stake-size change. Numbers recomputed
directly off the real evaluator/fixture (not invented): baseline's stage2 risk-adjusted score is
~1.26 with a NEGATIVE worst OOS window (~-0.47); the `min_edge=0.24` candidate's risk-adjusted
score is ~2.44 with a POSITIVE worst OOS window (~+4.53) — both a higher mean (5.69 -> 7.98) AND a
lower OOS standard deviation (4.51 -> 3.27), a genuine Pareto improvement, not a variance trick. A
pure-leverage variant of baseline (same thresholds, base_stake scaled 5.0 -> 20.0) is verified
elsewhere (test_risk_adjusted_fitness.py) to score IDENTICALLY to baseline under this metric,
proving leverage alone cannot pass this test.
"""
import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math, scope_guard


def _better_candidate_code() -> str:
    return patched_baseline_code(('config.get("min_edge", 0.15)', 'config.get("min_edge", 0.24)'))


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
    artifact (EDGE-5) — the WORST individual OOS window must itself be non-negative, unlike
    baseline's own worst window (which is negative on the real fixture)."""
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    baseline_stage2 = evaluator.evaluate_stage2(evaluator.BASELINE_PATH)
    candidate_stage2 = evaluator.evaluate_stage2(candidate_path)

    assert baseline_stage2["worst_window_oos_net_usd"] < 0.0, (
        "expected the real fixture's baseline to have a genuinely losing worst OOS window "
        "(that is the real problem this candidate must fix, not a strawman)"
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
