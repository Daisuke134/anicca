"""tests/test_adversary_disapprove.py — REQ-RH4 step 3: a fresh per-candidate adversary FAIL
verdict blocks promotion even when every deterministic gate (scope_guard, stage1, stage2
beats_baseline, trip-wire) already passed. `lib.promote.promote` (the git-commit side effect) must
NEVER be called in that case — verified by mocking it (per `lib/promote.py`'s own docstring
convention: "tests exercising the promotion GATE never call this with commit=True against a real
repo — they mock this function entirely").

This is the missing test `lib/promote.py`'s docstring already referenced before this close-loop
revision existed — Gap 3 fixes the fact that nothing wired the fresh per-candidate promotion
adversary (REQ-RH4) into an actual orchestration path at all. `lib/promote_gate.py` is that wiring
(pure/testable half); `promote_gate.sh` is the effectful half that gets the real adversary verdict
via a fresh headless `claude --model opus` call.
"""
from unittest import mock

import evaluator
from conftest import patched_baseline_code, write_candidate_with_fixtures
from lib import promote_gate


def _good_candidate(tmp_path):
    # Literals updated 2026-07-08 (commit a6f608c promoted a new committed baseline — see
    # test_baseline_beat.py's module docstring for the full re-derivation): a stricter min_edge
    # is a genuine adaptive-sizing-emphasis change against the NEW baseline, beating it on the real
    # risk-adjusted metric with a still-positive worst OOS window.
    code = patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.26)'),
        ('config.get("max_stake", 12.0)', 'config.get("max_stake", 10.0)'),
    )
    return code, write_candidate_with_fixtures(tmp_path, code)


def _regressing_candidate(tmp_path):
    # Literals updated 2026-07-08 (commit a6f608c) — see test_heldout_regress.py's module
    # docstring: loosens all five of the new baseline's selection filters near-to-nothing.
    code = patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.01)'),
        ('config.get("min_confidence", 7.5)', 'config.get("min_confidence", 0.0)'),
        ('config.get("min_combined", 2.0)', 'config.get("min_combined", 0.0)'),
        ('config.get("max_price", 0.88)', 'config.get("max_price", 1.0)'),
        ('config.get("min_liquidity", 800.0)', 'config.get("min_liquidity", 1.0)'),
    )
    return code, write_candidate_with_fixtures(tmp_path, code)


def test_good_candidate_is_eligible_for_adversary_review(tmp_path):
    _, candidate_path = _good_candidate(tmp_path)

    assessment = promote_gate.assess_candidate(candidate_path)

    assert assessment["scope_guard_ok"] is True
    assert assessment["stage1_pass"] is True
    assert assessment["stage2_pass"] is True
    assert assessment["tripwire_clear"] is True
    assert assessment["eligible_for_adversary_review"] is True


def test_adversary_fail_blocks_promotion_even_though_deterministic_gates_pass(tmp_path):
    candidate_code, candidate_path = _good_candidate(tmp_path)
    assessment = promote_gate.assess_candidate(candidate_path)
    assert assessment["eligible_for_adversary_review"] is True  # preconditions really did pass

    decision = promote_gate.decide_promotion(
        assessment, adversary_verdict="FAIL", adversary_reason="looks like it may not generalize"
    )
    assert decision["promote"] is False

    with mock.patch("lib.promote.promote") as mocked_promote:
        result = promote_gate.promote_if_approved(
            candidate_code, evaluator.BASELINE_PATH, decision, cwd=str(tmp_path), commit=True
        )

    mocked_promote.assert_not_called()
    assert result["committed"] is False


def test_adversary_missing_or_erroring_verdict_also_blocks_promotion_fail_closed(tmp_path):
    """EDGE-3: the adversary being unavailable/erroring must BLOCK promotion, never silently skip
    the check (fail-closed), even though the deterministic gates passed."""
    candidate_code, candidate_path = _good_candidate(tmp_path)
    assessment = promote_gate.assess_candidate(candidate_path)
    assert assessment["eligible_for_adversary_review"] is True

    decision = promote_gate.decide_promotion(assessment, adversary_verdict=None, adversary_reason="adversary process errored")
    assert decision["promote"] is False

    with mock.patch("lib.promote.promote") as mocked_promote:
        promote_gate.promote_if_approved(candidate_code, evaluator.BASELINE_PATH, decision, cwd=str(tmp_path), commit=True)

    mocked_promote.assert_not_called()


def test_adversary_pass_on_eligible_candidate_promotes_and_calls_promote_exactly_once(tmp_path):
    candidate_code, candidate_path = _good_candidate(tmp_path)
    assessment = promote_gate.assess_candidate(candidate_path)
    assert assessment["eligible_for_adversary_review"] is True

    decision = promote_gate.decide_promotion(
        assessment, adversary_verdict="PASS", adversary_reason="genuine edge-based selection change, not leverage"
    )
    assert decision["promote"] is True

    with mock.patch("lib.promote.promote") as mocked_promote:
        mocked_promote.return_value = {"committed": True, "candidate_id": "abc123", "path": evaluator.BASELINE_PATH}
        result = promote_gate.promote_if_approved(
            candidate_code, evaluator.BASELINE_PATH, decision, cwd=str(tmp_path), commit=True
        )

    mocked_promote.assert_called_once_with(candidate_code, evaluator.BASELINE_PATH, cwd=str(tmp_path), commit=True)
    assert result["committed"] is True


def test_ineligible_regressing_candidate_never_becomes_eligible_for_adversary_review(tmp_path):
    """A candidate that already fails a deterministic gate (the same loose-threshold regressing
    candidate from test_heldout_regress.py) must never even be marked eligible for adversary
    review — this is the flag `promote_gate.sh`'s real shell wrapper uses to skip the (costly)
    LLM call entirely, not just skip promotion after asking."""
    _, candidate_path = _regressing_candidate(tmp_path)

    assessment = promote_gate.assess_candidate(candidate_path)

    assert assessment["stage2_pass"] is False
    assert assessment["eligible_for_adversary_review"] is False

    # Even a (hypothetical, never-actually-requested) "PASS" cannot promote an ineligible candidate.
    decision = promote_gate.decide_promotion(assessment, adversary_verdict="PASS")
    assert decision["promote"] is False
    assert decision["adversary_verdict"] is None  # the adversary was never actually consulted
