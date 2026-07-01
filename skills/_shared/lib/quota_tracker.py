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
    Consecutive (= reset on any positive day), not cumulative (FIND-006 + FIND-2-013 fix).

    The CONSECUTIVE invariant is enforced by the CALLER: the parameter name carries
    the contract; the caller's responsibility is to reset the counter to 0 the moment
    a positive day occurs, NOT to keep a cumulative sum across resets.
    """
    if age_days <= 14:
        return False
    if consecutive_neg_7day_windows < 0:
        return False  # defensive
    return consecutive_neg_7day_windows >= 14


def count_consecutive_negative_windows(daily_roi_7day_jpy: list[float]) -> int:
    """REQ-Q5 helper (FIND-2-013 fix): scan a list of daily rolling-7d ROI values
    (most recent LAST) and return the count of CONSECUTIVE negatives at the tail.
    Returns 0 if the most recent value is non-negative.
    This is the canonical way to compute `consecutive_neg_7day_windows` for is_dormant.
    """
    count = 0
    for v in reversed(daily_roi_7day_jpy):
        if v < 0:
            count += 1
        else:
            break
    return count


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


# ─── sprint-3 #34: time-horizon-aware dormant helpers ─────────────
def resolve_time_horizon_days(menu: dict, *, default: int = 14) -> int:
    """REQ-T1: read menu.json's `time_horizon_days` with defensive fallback.

    Returns `default` when the field is missing, None, non-castable to int,
    or ≤ 0. Sprint-3 #34 spec REQ-T1 + EDGE-E3/E4.
    """
    if not isinstance(menu, dict):
        return int(default)
    raw = menu.get("time_horizon_days")
    if raw is None:
        return int(default)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return int(default)
    return v if v > 0 else int(default)


def is_dormant_with_horizon(
    *,
    consecutive_neg_windows: int,
    slot_age_days: float,
    time_horizon_days: int,
) -> bool:
    """REQ-T2: parent §7b INV-P3 canonical predicate. Returns True IFF BOTH:
      - slot_age_days > 2 * time_horizon_days  (= we've given it enough time)
      - consecutive_neg_windows > time_horizon_days  (= persistent failure)
    Sprint-2's is_dormant() stays for backward compat; sprint-4 wires this
    to the dispatcher when LAYER C settle callback lands.
    """
    return (
        float(slot_age_days) > 2 * int(time_horizon_days)
        and int(consecutive_neg_windows) > int(time_horizon_days)
    )


# ─── sprint-4 (c): live-mode dormant helpers ──────────────────────
def has_realized_in_window(
    roi_rows: list[dict],
    now_ts: int,
    window_days: int = 90,
) -> bool:
    """REQ-L1: True iff at least one row has realized>0 and ts within window.

    Malformed rows (missing/garbage ts or realized) are skipped, not raised.
    """
    horizon_s = int(window_days) * 86400
    now_i = int(now_ts)
    for row in roi_rows or []:
        try:
            realized = int(row.get("roi_jpy_realized", 0) or 0)
            ts = int(row.get("ts", 0) or 0)
        except (TypeError, ValueError):
            continue
        if realized > 0 and (now_i - ts) <= horizon_s:
            return True
    return False


def compute_dormant_state(
    *,
    roi_rows: list[dict],
    slot_age_days: float,
    time_horizon_days: int,
    now_ts: int,
) -> dict:
    """REQ-L2 / REQ-L3: compose has_realized_in_window + is_dormant_with_horizon
    behind a 90-day live-mode gate. Returns:
      { live_mode: bool, consecutive_neg_windows: int, is_dormant: bool }

    Semantics:
      - live_mode = has_realized_in_window(roi_rows, now_ts, window_days=90)
      - If live_mode is False → is_dormant is False (unconditional; slot has
        never settled, cannot be judged dormant).
      - If live_mode is True → consecutive_neg_windows is computed from a
        7-day rolling list of (realized - expected) window sums, ordered
        MOST RECENT LAST, and passed to count_consecutive_negative_windows.
        is_dormant follows is_dormant_with_horizon(consec, slot_age_days,
        time_horizon_days).
    """
    live_mode = has_realized_in_window(roi_rows, now_ts=now_ts, window_days=90)
    if not live_mode:
        return {"live_mode": False, "consecutive_neg_windows": 0,
                "is_dormant": False}

    # Group roi_rows by day (midnight-UTC boundary) — REQ-L3 (i)
    daily_net: dict[int, int] = {}
    for row in roi_rows or []:
        try:
            ts = int(row.get("ts", 0) or 0)
            realized = int(row.get("roi_jpy_realized", 0) or 0)
            expected = int(row.get("roi_jpy_expected", 0) or 0)
        except (TypeError, ValueError):
            continue
        if ts <= 0:
            continue
        day = ts // 86400
        daily_net[day] = daily_net.get(day, 0) + (realized - expected)

    if not daily_net:
        return {"live_mode": True, "consecutive_neg_windows": 0,
                "is_dormant": False}

    # REQ-L3 (ii): build rolling_7d list — MOST RECENT LAST — of
    # 2 * time_horizon_days entries. Each entry = 7-day trailing sum ending
    # at day_i. If fewer than time_horizon_days complete windows exist,
    # return 0 (slot too young). REQ-L3 (iv).
    day_end = int(now_ts) // 86400
    window_count = 2 * int(time_horizon_days)
    rolling_7d: list[float] = []
    for offset in range(window_count - 1, -1, -1):
        day_i = day_end - offset
        window_sum = 0
        for d in range(day_i - 6, day_i + 1):
            window_sum += daily_net.get(d, 0)
        rolling_7d.append(float(window_sum))
    # rolling_7d[-1] = most recent complete 7-day window ending today.

    # REQ-L3 (iv): if slot too young (< time_horizon_days full windows), 0.
    if float(slot_age_days) < float(time_horizon_days):
        consecutive_neg_windows = 0
    else:
        consecutive_neg_windows = count_consecutive_negative_windows(rolling_7d)

    is_dormant_val = is_dormant_with_horizon(
        consecutive_neg_windows=consecutive_neg_windows,
        slot_age_days=slot_age_days,
        time_horizon_days=time_horizon_days,
    )
    return {"live_mode": True,
            "consecutive_neg_windows": int(consecutive_neg_windows),
            "is_dormant": bool(is_dormant_val)}
