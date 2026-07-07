"""Required test 3 (delegated task spec): a candidate that improves stage1 (looks profitable on
the small cheap-filter window) but REGRESSES on stage2's walk-forward out-of-sample aggregate is
NOT promoted — the promotion gate returns False even though the in-sample signal looked good.

Traces to behavioral-spec.md REQ-EV2/EV3/EV4/RH4, EDGE-5 (a single lucky window must never
produce a false promotion); verification-architecture.md PROP-SI-EV3/RH4.

The "regressing" candidate hardcodes LOOSE thresholds (min_edge=0.10, min_confidence=0.0 — bets
on almost every historical row) directly in its EVOLVE-BLOCK defaults. Against the real fixture
this scores +4.54 net USD on stage1's window (window 0 alone, comfortably above
evaluator.STAGE1_MIN_NET_USD=1.0) but a MEAN out-of-sample net of -3.10 across stage2's 3
walk-forward window pairs — worse than the baseline's own out-of-sample floor (max(baseline, 0)).
These exact numbers were derived by running the real backtest harness over the real committed
fixture (see scratchpad gen_fixture.py sweep) before being hardcoded here as fixed expectations.
"""
import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math, scope_guard


def _regressing_candidate_code() -> str:
    return patched_baseline_code(
        ('config.get("min_edge", 0.15)', 'config.get("min_edge", 0.10)'),
        ('config.get("min_confidence", 6.0)', 'config.get("min_confidence", 0.0)'),
    )


def test_regressing_candidate_passes_stage1_but_scores_below_zero_on_stage2_oos(tmp_path):
    baseline_code = read_baseline_code()
    candidate_code = _regressing_candidate_code()

    ok, reason = scope_guard.check(candidate_code, baseline_code)
    assert ok is True, f"expected the config-default-only edit to stay in scope: {reason}"

    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    stage1 = evaluator.evaluate_stage1(candidate_path)
    assert stage1["stage1_pass"] is True
    assert stage1["combined_score"] > evaluator.STAGE1_MIN_NET_USD

    stage2 = evaluator.evaluate_stage2(candidate_path)
    assert stage2["combined_score"] < 0.0, (
        "regressing candidate must score NEGATIVE mean out-of-sample net USD "
        f"(got {stage2['combined_score']})"
    )


def test_regressing_candidate_is_not_promoted_end_to_end(tmp_path):
    """Full evaluate() cascade + the promotion gate itself: even though the candidate "improved"
    on the cheap stage1 filter, the ordered gate (REQ-RH4) must return False for promotion."""
    candidate_code = _regressing_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    result = evaluator.evaluate(candidate_path)

    assert result["stage1_pass"] is True  # it DID look good on the cheap filter...
    assert result["stage2_pass"] is False  # ...but REQ-EV4: stage1 alone is never promotion-eligible
    assert not gate_math.beats_baseline(result["combined_score"], result["baseline_stage2_score"])

    promotable = gate_math.stage_gate(
        stage1_pass=result["stage1_pass"],
        stage2_pass=result["stage2_pass"],
        tripwire_clear=True,
        adversary_verdict="PASS",
    )
    assert promotable is False
