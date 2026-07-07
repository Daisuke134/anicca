"""Required test 5 (delegated task spec): a hand-crafted BETTER `score_candidate` variant yields
backtested net USD > the baseline strategy's, and the promotion gate (scope_guard PASS +
beats_baseline + walk-forward non-regress) returns True.

This proves the Done-condition-3 evaluator/promotion machinery DETERMINISTICALLY: real backtest
math (gate_math.net_usd) over the real committed historical fixture
(strategies/fixtures/pm_history.csv), a real scope_guard.check() pass, and the real stage_gate()
boolean gate all wired together end-to-end. The REAL openevolve LLM-proposing run is the NEXT
stage (this stage builds and proves the deterministic core the LLM's candidates will be evaluated
against, per behavioral-spec.md's phase framing).

Numbers (derived by running the real backtest harness over the real committed fixture —
scratchpad gen_fixture.py sweep, not invented): baseline's own stage2 walk-forward mean OOS net is
slightly negative (~-0.40, i.e. its beats_baseline floor is 0.0); the better candidate
(min_confidence raised from 6.0 to 8.0, filtering out a historically-unprofitable
mid-confidence "value trap" cluster in the fixture) scores a mean OOS net of roughly +11.5,
clearly beating that floor.
"""
import evaluator
from conftest import patched_baseline_code, read_baseline_code, write_candidate_with_fixtures
from lib import gate_math, scope_guard


def _better_candidate_code() -> str:
    return patched_baseline_code(('config.get("min_confidence", 6.0)', 'config.get("min_confidence", 8.0)'))


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


def test_full_evaluate_cascade_and_promotion_gate_return_true(tmp_path):
    candidate_code = _better_candidate_code()
    candidate_path = write_candidate_with_fixtures(tmp_path, candidate_code)

    result = evaluator.evaluate(candidate_path)

    assert result["stage1_pass"] is True
    assert result["stage2_pass"] is True  # this IS beats_baseline, computed inside evaluate()
    assert result["combined_score"] > 0.0
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
