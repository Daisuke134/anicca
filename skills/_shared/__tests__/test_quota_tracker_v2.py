"""PROP-P1 + Q3 + Q3d + Q3e + Q5 + Q6 — quota_tracker (sprint-2).

Spec: ~/anicca/.vcsdd/features/proactive-loop-skeleton/specs/behavioral-spec.md
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
    # 7 consecutive negative ROI days
    assert should_route_mother_queue(neg_roi_days=7, age_days=30) is True


def test_no_mother_queue_route_at_6_days():
    assert should_route_mother_queue(neg_roi_days=6, age_days=30) is False


def test_no_mother_queue_route_when_slot_young():
    """slot age < 14 days = young, never routed."""
    assert should_route_mother_queue(neg_roi_days=14, age_days=10) is False


# ─── PROP-Q5-dormant ──────────────────────────────────────────────
def test_dormant_at_14_consecutive_negative_windows():
    assert is_dormant(neg_7day_windows=14, age_days=30) is True


def test_not_dormant_at_13_windows():
    assert is_dormant(neg_7day_windows=13, age_days=30) is False


def test_not_dormant_when_slot_young():
    assert is_dormant(neg_7day_windows=14, age_days=10) is False


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
