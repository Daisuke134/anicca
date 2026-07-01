"""PROP-T1 + T2 unit tests for lib.quota_tracker.{resolve_time_horizon_days, is_dormant_with_horizon}."""
from __future__ import annotations
import pytest
from lib.quota_tracker import resolve_time_horizon_days, is_dormant_with_horizon


# ─── PROP-T1 fallback ─────────────────────────────────────────────
class TestResolveHorizon:
    @pytest.mark.parametrize("menu,expected", [
        ({}, 14),  # EDGE-E3 missing key
        ({"time_horizon_days": 14}, 14),
        ({"time_horizon_days": 30}, 30),
        ({"time_horizon_days": 1}, 1),
        ({"time_horizon_days": 0}, 14),  # EDGE-E4 zero
        ({"time_horizon_days": -5}, 14),  # EDGE-E4 negative
        ({"time_horizon_days": None}, 14),  # EDGE-E4 None
        ({"time_horizon_days": "14"}, 14),  # castable string
        ({"time_horizon_days": "abc"}, 14),  # non-castable → default
        ({"time_horizon_days": 3.7}, 3),  # float truncated
    ])
    def test_fallback(self, menu, expected):
        assert resolve_time_horizon_days(menu, default=14) == expected

    def test_custom_default(self):
        assert resolve_time_horizon_days({}, default=7) == 7
        assert resolve_time_horizon_days({"time_horizon_days": 0}, default=30) == 30


# ─── PROP-T2 truth table ──────────────────────────────────────────
class TestIsDormantWithHorizon:
    def test_both_false(self):
        # slot_age_days ≤ 2*horizon AND consecutive ≤ horizon → False
        assert is_dormant_with_horizon(
            consecutive_neg_windows=0, slot_age_days=5.0, time_horizon_days=14,
        ) is False

    def test_age_true_consecutive_false(self):
        # Age gate passes (30 > 28) but consecutive doesn't (10 <= 14) → False
        assert is_dormant_with_horizon(
            consecutive_neg_windows=10, slot_age_days=30.0, time_horizon_days=14,
        ) is False

    def test_age_false_consecutive_true(self):
        # Consecutive gate passes but age doesn't (15 <= 28) → False
        assert is_dormant_with_horizon(
            consecutive_neg_windows=20, slot_age_days=15.0, time_horizon_days=14,
        ) is False

    def test_both_true(self):
        # BOTH pass → True
        assert is_dormant_with_horizon(
            consecutive_neg_windows=20, slot_age_days=40.0, time_horizon_days=14,
        ) is True

    def test_boundary_strict_gt(self):
        # Boundary check: must be STRICTLY greater
        # slot_age_days == 2*horizon → False (28 > 28 is False)
        assert is_dormant_with_horizon(
            consecutive_neg_windows=20, slot_age_days=28.0, time_horizon_days=14,
        ) is False
        # consecutive == horizon → False (14 > 14 is False)
        assert is_dormant_with_horizon(
            consecutive_neg_windows=14, slot_age_days=100.0, time_horizon_days=14,
        ) is False

    def test_fast_horizon_class_1_day(self):
        # FAST class: horizon=1, dormant threshold = 2d zero
        assert is_dormant_with_horizon(
            consecutive_neg_windows=2, slot_age_days=3.0, time_horizon_days=1,
        ) is True

    def test_slow_horizon_class_14_day_gig(self):
        # SLOW class (gig): only after 28 days of zero settled + 15+ neg windows
        assert is_dormant_with_horizon(
            consecutive_neg_windows=15, slot_age_days=29.0, time_horizon_days=14,
        ) is True
        # Live gig scenario: ~1 hour old + 0 neg windows → False
        assert is_dormant_with_horizon(
            consecutive_neg_windows=0, slot_age_days=1.0/24, time_horizon_days=14,
        ) is False
