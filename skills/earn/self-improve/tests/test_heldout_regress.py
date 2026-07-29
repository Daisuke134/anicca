"""Required test 3 (delegated task spec): a candidate that improves stage1 (looks profitable on
the small cheap-filter window) but REGRESSES on stage2's risk-adjusted walk-forward out-of-sample
score is NOT promoted — the promotion gate returns False even though the in-sample signal looked
good.

Traces to behavioral-spec.md REQ-EV2/EV3/EV4/RH4, EDGE-5 (a single lucky window must never
produce a false promotion); verification-architecture.md PROP-SI-EV3/RH4.

The "regressing" candidate hardcodes LOOSE thresholds directly in its EVOLVE-BLOCK defaults
(min_edge~0.01, min_confidence=0.0, min_combined=0.0, max_price=1.0, min_liquidity=1.0 — bets on
almost every historical row, all five of the committed baseline's own selection filters loosened
to near-nothing).

Close-loop revision (2026-07-08, Gap 2): `combined_score` for stage2 is now a Sharpe-like
risk-adjusted metric (`gate_math.risk_adjusted_score`), not raw mean OOS net USD (see evaluator.py's
module docstring).

REAL PROMOTION update (2026-07-08, commit a6f608c): the committed baseline itself changed (the
capable-improver openevolve run's discovered candidate — tighter selection filters + an adaptive
stake multiplier — was promoted into `strategies/pm_backtest_strategy.py`). Re-measured directly
off the REAL evaluator/fixture against this NEW baseline (not carried over from the pre-promotion
revision): this loose-all-filters candidate's stage1 (cheap-window) score still clears
STAGE1_MIN_NET_USD comfortably (~14.0), but its stage2 walk-forward risk-adjusted score collapses to
~0.18 (mean ~1.95, one window losing badly at ~-12.32, std ~10.67) — clearly BELOW the new,
already-much-better baseline's own risk-adjusted score (~3.21). This is precisely the
reward-hacking-by-variance failure mode the risk-adjusted metric exists to catch (see
gate_math.risk_adjusted_score's docstring) — demonstrated here with a real, current, non-hypothetical
candidate, not a strawman.
"""
import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math, scope_guard


def _regressing_candidate_code() -> str:
    return patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.01)'),
        ('config.get("min_confidence", 7.5)', 'config.get("min_confidence", 0.0)'),
        ('config.get("min_combined", 2.0)', 'config.get("min_combined", 0.0)'),
        ('config.get("max_price", 0.88)', 'config.get("max_price", 1.0)'),
        ('config.get("min_liquidity", 800.0)', 'config.get("min_liquidity", 1.0)'),
    )


def test_regressing_candidate_passes_stage1_but_scores_worse_than_baseline_on_stage2_oos(tmp_path):
    baseline_code = read_baseline_code()
    candidate_code = _regressing_candidate_code()

    ok, reason = scope_guard.check(candidate_code, baseline_code)
    assert ok is True, f"expected the config-default-only edit to stay in scope: {reason}"

    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    stage1 = evaluator.evaluate_stage1(candidate_path)
    assert stage1["stage1_pass"] is True
    assert stage1["combined_score"] > evaluator.STAGE1_MIN_NET_USD

    stage2 = evaluator.evaluate_stage2(candidate_path)
    baseline_stage2 = evaluator.baseline_stage2_score()
    assert stage2["combined_score"] < baseline_stage2, (
        "regressing candidate's risk-adjusted stage2 score must score BELOW baseline's "
        f"(got candidate={stage2['combined_score']}, baseline={baseline_stage2})"
    )
    # It gets there via variance, not via a genuinely negative worst window being the WHOLE story:
    # confirm the specific failure mode is a blown-out worst window swamping the mean.
    assert stage2["worst_window_oos_net_usd"] < 0.0
    assert stage2["std_oos_net_usd"] > 0.0


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
