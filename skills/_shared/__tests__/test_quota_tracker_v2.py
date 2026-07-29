"""PROP-P1 + Q3 + Q3d + Q3e + Q5 + Q6 — quota_tracker (sprint-2).

Spec: __REPO_ROOT__/.vcsdd/features/proactive-loop-skeleton/specs/behavioral-spec.md
"""
from __future__ import annotations

import json
import pytest

from lib.quota_tracker import (  # FAIL until 2b
    Budget,
    quantize_budget,
    compute_budget,
    apply_estimate_penalty,
    should_route_mother_queue,
    is_dormant,
)


# ─── PROP-P1-budget-quantize (required:true) ──────────────────────
@pytest.mark.parametrize("b,expected", [
    (10.0, Budget.FULL),
    (3.0, Budget.FULL),       # inclusive lower
    (2.99, Budget.MEDIUM),
    (1.0, Budget.MEDIUM),     # inclusive lower
    (0.99, Budget.LIGHT),
    (0.1, Budget.LIGHT),      # inclusive lower
    (0.0999, Budget.MINIMAL),
    (0.0, Budget.MINIMAL),
])
def test_quantize_budget_half_open(b, expected):
    assert quantize_budget(b) == expected


def test_quantize_budget_never_throws():
    # property-test sketch: bounds + nan
    for b in [-1.0, 0.0, 0.05, 0.1, 0.5, 1.0, 1.5, 3.0, 5.0, 100.0]:
        result = quantize_budget(b)
        assert isinstance(result, Budget)


# ─── PROP-Q3-fallback (penalty multiplier) ────────────────────────
def test_estimated_token_source_2x_penalty_default():
    base = 100.0
    result = apply_estimate_penalty(base, ratio_estimated_over_all=0.3)
    assert result == base * 2.0


# ─── PROP-Q3d-ratio-escalation (required:true) ────────────────────
def test_estimated_ratio_above_threshold_uses_4x():
    base = 100.0
    result = apply_estimate_penalty(base, ratio_estimated_over_all=0.51)
    assert result == base * 4.0


def test_estimated_ratio_at_threshold_uses_2x():
    """Boundary: exactly 0.5 is NOT above; 2× applies."""
    base = 100.0
    result = apply_estimate_penalty(base, ratio_estimated_over_all=0.5)
    assert result == base * 2.0


def test_estimated_ratio_below_threshold_uses_2x():
    base = 100.0
    result = apply_estimate_penalty(base, ratio_estimated_over_all=0.49)
    assert result == base * 2.0


# ─── PROP-Q3e-mother-queue (required:true) ────────────────────────
def test_mother_queue_route_when_degraded_7d():
    """FIND-005 fix: no age gate; REQ-Q3(e) verbatim is just neg_roi_days>=7."""
    assert should_route_mother_queue(neg_roi_days=7) is True


def test_no_mother_queue_route_at_6_days():
    assert should_route_mother_queue(neg_roi_days=6) is False


# ─── PROP-Q5-dormant ──────────────────────────────────────────────
def test_dormant_at_14_consecutive_negative_windows():
    """FIND-006 fix: param renamed to consecutive_neg_7day_windows."""
    assert is_dormant(consecutive_neg_7day_windows=14, age_days=30) is True


def test_not_dormant_at_13_windows():
    assert is_dormant(consecutive_neg_7day_windows=13, age_days=30) is False


def test_not_dormant_when_slot_young():
    assert is_dormant(consecutive_neg_7day_windows=14, age_days=10) is False


def test_dormant_boundary_age_15():
    """FIND-020 fix: age=15 (just past >14 boundary) IS eligible."""
    assert is_dormant(consecutive_neg_7day_windows=14, age_days=15) is True


def test_dormant_boundary_age_14_not_eligible():
    """Boundary inclusive-lower-of-14d: age=14 is NOT past the boundary."""
    assert is_dormant(consecutive_neg_7day_windows=14, age_days=14) is False


# ─── REQ-Q5 count_consecutive_negative_windows (FIND-3-005 fix) ────
def test_count_consecutive_empty_list():
    from lib.quota_tracker import count_consecutive_negative_windows
    assert count_consecutive_negative_windows([]) == 0


def test_count_consecutive_all_positive():
    from lib.quota_tracker import count_consecutive_negative_windows
    assert count_consecutive_negative_windows([1.0, 2.0, 3.0]) == 0


def test_count_consecutive_trailing_negatives():
    from lib.quota_tracker import count_consecutive_negative_windows
    # Most recent at tail; 3 consecutive negative
    assert count_consecutive_negative_windows([5.0, -1.0, -2.0, -3.0]) == 3


def test_count_consecutive_positive_resets():
    from lib.quota_tracker import count_consecutive_negative_windows
    # Positive in middle breaks chain — only the trailing negatives count
    assert count_consecutive_negative_windows([-1.0, 0.5, -2.0, -3.0]) == 2


def test_count_consecutive_most_recent_positive_returns_zero():
    from lib.quota_tracker import count_consecutive_negative_windows
    # Most recent = positive → 0 regardless of history
    assert count_consecutive_negative_windows([-1.0, -2.0, -3.0, 0.1]) == 0


def test_count_consecutive_single_negative():
    from lib.quota_tracker import count_consecutive_negative_windows
    assert count_consecutive_negative_windows([-1.0]) == 1


def test_count_consecutive_zero_is_not_negative():
    from lib.quota_tracker import count_consecutive_negative_windows
    # 0 is NOT negative; breaks the consecutive chain
    assert count_consecutive_negative_windows([-1.0, 0.0, -2.0]) == 1


# ─── REQ-Q5 SIDE-EFFECT (FIND-001 fix) ────────────────────────────
def test_write_dormant_sentinel(tmp_path):
    from lib.quota_tracker import write_dormant_sentinel
    write_dormant_sentinel(tmp_path, evidence={"reason": "test", "ratio": -0.5})
    sentinel = tmp_path / ".dormant.sentinel"
    assert sentinel.exists()
    import json
    parsed = json.loads(sentinel.read_text())
    assert parsed["reason"] == "test"


# ─── REQ-Q6 sentinel removal allowlist (FIND-002 + FIND-014 fix) ─
def test_sentinel_removal_only_allowed_callers():
    from lib.quota_tracker import is_allowed_sentinel_removal_call
    assert is_allowed_sentinel_removal_call("bot2bot.apply_sibling_response") is True
    assert is_allowed_sentinel_removal_call("mutation_gate.post_merge_hook") is True
    assert is_allowed_sentinel_removal_call("random_caller") is False
    assert is_allowed_sentinel_removal_call("proactive_loop.main") is False


# ─── compute_budget formula sanity ────────────────────────────────
def test_compute_budget_formula():
    """budget_per_pass = remaining_pct / (minutes_until_reset / 5)."""
    # 30% / (60/5) = 30 / 12 = 2.5
    result = compute_budget(remaining_pct=30.0, minutes_until_reset=60)
    assert result == pytest.approx(2.5, abs=0.001)


def test_compute_budget_at_reset_returns_max():
    """When minutes_until_reset == 0, treat as unlimited (= FULL bucket)."""
    result = compute_budget(remaining_pct=30.0, minutes_until_reset=0)
    assert result >= 3.0
