"""Close-loop Gap 2 tests: `gate_math.risk_adjusted_score` itself, and the structural property it
exists to buy — a candidate that ONLY leverages (scales up stake size on the exact same trade
selection as baseline) cannot improve `combined_score`, unlike a genuine selection change.

Traces to behavioral-spec.md REQ-EV1/RH1/RH5 and this feature's close-loop Stop-hook review Gap 2
("risk-adjusted fitness... kill variance-amplification; the prior candidate just leveraged
stakes"). The real historical instance this guards against is candidate `233d923c`
(execution-notes-self-improve.md's "HONEST re-read" section): identical trade selection to
baseline in every OOS window, stake merely scaled — under the OLD raw-mean-net-USD metric this
"beat baseline"; under `risk_adjusted_score` it does not (proven directly below).
"""
import math

import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math


def test_risk_adjusted_score_is_mean_over_stddev_when_stddev_clears_the_eps_floor():
    scores = [10.0, 20.0, 30.0]
    mean = 20.0
    stddev = (((10 - 20) ** 2 + (20 - 20) ** 2 + (30 - 20) ** 2) / 3) ** 0.5  # population stddev
    expected = mean / stddev  # stddev (~8.16) clears the 1e-9 eps floor -> no eps contamination

    assert gate_math.risk_adjusted_score(scores) == expected


def test_risk_adjusted_score_falls_back_to_eps_only_in_the_zero_variance_degenerate_case():
    scores = [5.0, 5.0, 5.0]  # stddev == 0.0 exactly -> the ONE case eps is meant to guard

    result = gate_math.risk_adjusted_score(scores, eps=1e-9)

    assert result == 5.0 / 1e-9


def test_risk_adjusted_score_empty_input_is_fail_sentinel_zero():
    assert gate_math.risk_adjusted_score([]) == 0.0


def test_risk_adjusted_score_is_invariant_to_uniform_positive_leverage():
    """The core proof from gate_math.risk_adjusted_score's own docstring: scaling every OOS window
    score by the same positive constant k (a pure leverage change) leaves the ratio EXACTLY
    unchanged (the `max(stddev, eps)` denominator, not `stddev + eps`, makes this exact rather than
    merely asymptotic — see the docstring)."""
    scores = [3.36, 67.26, -42.28]  # the real accepted candidate 233d923c's actual OOS window net USD
    for k in (0.25, 2.0, 4.0, 100.0):
        scaled = [s * k for s in scores]

        base_ratio = gate_math.risk_adjusted_score(scores)
        scaled_ratio = gate_math.risk_adjusted_score(scaled)

        # Exact algebraically (mean*k / stddev*k == mean/stddev); the assertion allows IEEE-754
        # float rounding noise only (~1e-13 relative at k=100), NOT the eps-driven asymmetric drift
        # a `stddev + eps` design would have shown here (that alternative failed this exact test
        # with a real, reproducible, if tiny, k-dependent bias — see git history of this file).
        assert math.isclose(scaled_ratio, base_ratio, rel_tol=1e-9), (
            f"leverage k={k} changed the ratio beyond float noise: {base_ratio} -> {scaled_ratio}"
        )


def test_leverage_only_candidate_does_not_beat_baseline_on_real_fixture(tmp_path):
    """End-to-end (not just the pure-math proof above): a candidate whose ONLY EVOLVE-BLOCK change
    scales both `base_stake: 5.0 -> 10.0` and `max_stake: 12.0 -> 24.0` uniformly (identical
    selection and clipping geometry every window) must score IDENTICALLY to baseline's own
    risk-adjusted combined_score and therefore must NOT beat_baseline (a tie never beats,
    EDGE-2)."""
    leverage_code = patched_baseline_code(
        ('config.get("base_stake", 5.0)', 'config.get("base_stake", 10.0)'),
        ('config.get("max_stake", 12.0)', 'config.get("max_stake", 24.0)'),
    )
    leverage_path = write_candidate_with_fixtures(tmp_path, leverage_code)

    baseline_stage2 = evaluator.evaluate_stage2(evaluator.BASELINE_PATH)
    leverage_stage2 = evaluator.evaluate_stage2(leverage_path)

    assert math.isclose(leverage_stage2["combined_score"], baseline_stage2["combined_score"], rel_tol=1e-9)
    assert gate_math.beats_baseline(leverage_stage2["combined_score"], baseline_stage2["combined_score"]) is False


def test_genuine_selection_change_beats_baseline_where_leverage_could_not(tmp_path):
    """Contrast case, same fixture: a genuine selection/sizing-emphasis change (real openevolve
    promotion, commit a6f608c, 2026-07-08 — see test_baseline_beat.py's module docstring for the
    full re-derivation against the NEW committed baseline) DOES beat baseline, unlike the
    leverage-only candidate above — proving `risk_adjusted_score` rewards genuine edge-finding,
    not just any code change."""
    baseline_code = read_baseline_code()
    selection_code = patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.26)'),
        ('config.get("max_stake", 12.0)', 'config.get("max_stake", 10.0)'),
    )
    assert selection_code != baseline_code
    selection_path = write_candidate_with_fixtures(tmp_path, selection_code)

    baseline_stage2 = evaluator.evaluate_stage2(evaluator.BASELINE_PATH)
    selection_stage2 = evaluator.evaluate_stage2(selection_path)

    assert gate_math.beats_baseline(selection_stage2["combined_score"], baseline_stage2["combined_score"]) is True
    assert selection_stage2["worst_window_oos_net_usd"] >= 0.0
