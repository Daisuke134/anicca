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


def should_route_mother_queue(*, neg_roi_days: int) -> bool:
    """REQ-Q3(e) verbatim: degraded for 7 days → append to mother-recovery-queue.
    No age precondition — REQ-Q3(e) does NOT require slot age > 14d (FIND-005 fix).
    """
    return neg_roi_days >= 7


def is_dormant(*, consecutive_neg_7day_windows: int, age_days: int) -> bool:
    """REQ-Q5: 14 CONSECUTIVE negative 7-day windows AND age > 14d → dormant.
    Consecutive (= reset on any positive day), not cumulative (FIND-006 fix).
    """
    if age_days <= 14:
        return False
    return consecutive_neg_7day_windows >= 14


def write_dormant_sentinel(slot_dir, *, evidence: dict) -> None:
    """REQ-Q5 SIDE-EFFECT (FIND-001 fix): write .dormant.sentinel with evidence.
    The cron's next tick reads this and short-circuits step 6.
    """
    from pathlib import Path
    import json
    p = Path(slot_dir) / ".dormant.sentinel"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(evidence, indent=2))


def is_allowed_sentinel_removal_call(call_source: str) -> bool:
    """REQ-Q6 (FIND-002 + FIND-014 fix): static-analysis helper.
    Returns True iff the call_source matches one of the 2 allowed call sites:
      (a) bot2bot apply-sibling-response handler with adversary-PASS verdict
      (b) REQ-C3 mutation-gate post-merge hook
    Any other caller must be flagged by the daily adversary.
    """
    ALLOWED = {"bot2bot.apply_sibling_response", "mutation_gate.post_merge_hook"}
    return call_source in ALLOWED
