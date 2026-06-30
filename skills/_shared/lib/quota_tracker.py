"""quota_tracker — continuous budget per pass (sprint-2).

PROP-P1 + Q3 + Q3d + Q3e + Q5 + Q6.
"""
from __future__ import annotations

import math
from enum import Enum


class Budget(str, Enum):
    FULL = "FULL"
    MEDIUM = "MEDIUM"
    LIGHT = "LIGHT"
    MINIMAL = "MINIMAL"


def compute_budget(*, remaining_pct: float, minutes_until_reset: int) -> float:
    """REQ-Q2: budget_per_pass = remaining_pct / (minutes_until_reset / 5).
    When minutes_until_reset == 0, return a large value (>= 3.0 = FULL bucket).
    """
    if minutes_until_reset <= 0:
        return math.inf
    return remaining_pct / (minutes_until_reset / 5.0)


def quantize_budget(b: float) -> Budget:
    """REQ-Q2 half-open canonical: FULL iff b>=3.0; MEDIUM iff 1.0<=b<3.0;
    LIGHT iff 0.1<=b<1.0; MINIMAL iff b<0.1.
    """
    if b >= 3.0:
        return Budget.FULL
    if b >= 1.0:
        return Budget.MEDIUM
    if b >= 0.1:
        return Budget.LIGHT
    return Budget.MINIMAL


def apply_estimate_penalty(base_cost: float, ratio_estimated_over_all: float) -> float:
    """REQ-Q3(c)+(d): 2× penalty default; 4× when ratio > 0.5 (= 100-row aggregate)."""
    if ratio_estimated_over_all > 0.5:
        return base_cost * 4.0
    return base_cost * 2.0


def should_route_mother_queue(*, neg_roi_days: int, age_days: int) -> bool:
    """REQ-Q3(e): 7-day persistent degradation routes to mother-recovery-queue.
    Slot age must be > 14 days (= young slots never routed — they need warmup time).
    """
    if age_days <= 14:
        return False
    return neg_roi_days >= 7


def is_dormant(*, neg_7day_windows: int, age_days: int) -> bool:
    """REQ-Q5: 14 consecutive negative 7-day windows AND age > 14d → dormant."""
    if age_days <= 14:
        return False
    return neg_7day_windows >= 14
