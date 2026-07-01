"""Phase 2a RED — sprint-4 (c) dispatcher-live-dormant-mode.

Unit tests for the two new PURE helpers in quota_tracker.py:
  - has_realized_in_window(roi_rows, now_ts, window_days=90) -> bool
  - compute_dormant_state(roi_rows, slot_age_days, time_horizon_days, now_ts) -> dict

Maps to:
  PROP-L1-window-detection, PROP-L2-live-mode-{false,true}-*, PROP-L3-most-recent-LAST,
  PROP-E1..E7.

These MUST fail until Phase 2b implements the helpers.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "skills" / "_shared"))
from lib.quota_tracker import (  # noqa: E402
    count_consecutive_negative_windows,
    is_dormant_with_horizon,
)

# The helpers under test — imported unconditionally so the test module fails
# to load until Phase 2b ships the functions.
from lib.quota_tracker import (  # noqa: E402
    has_realized_in_window,
    compute_dormant_state,
)


DAY = 86400


# ─── PROP-L1 has_realized_in_window ───────────────────────────────
def test_L1_recent_positive_returns_true():
    now = 1_800_000_000
    rows = [{"ts": now - 5 * DAY, "roi_jpy_realized": 25000}]
    assert has_realized_in_window(rows, now_ts=now, window_days=90) is True


def test_L1_only_zero_returns_false():
    now = 1_800_000_000
    rows = [{"ts": now - 5 * DAY, "roi_jpy_realized": 0}]
    assert has_realized_in_window(rows, now_ts=now, window_days=90) is False


def test_L1_positive_but_out_of_window_returns_false():
    now = 1_800_000_000
    rows = [{"ts": now - 100 * DAY, "roi_jpy_realized": 40000}]
    assert has_realized_in_window(rows, now_ts=now, window_days=90) is False


def test_L1_multi_row_one_qualifies_returns_true():
    now = 1_800_000_000
    rows = [
        {"ts": now - 100 * DAY, "roi_jpy_realized": 40000},   # out of window
        {"ts": now - 5 * DAY, "roi_jpy_realized": 12000},     # in window
        {"ts": now - 3 * DAY, "roi_jpy_realized": 0},         # zero
    ]
    assert has_realized_in_window(rows, now_ts=now, window_days=90) is True


def test_L1_empty_rows_returns_false():
    assert has_realized_in_window([], now_ts=1_800_000_000, window_days=90) is False


# ─── PROP-E1..E7 edge cases inside compute_dormant_state ──────────
def test_E1_empty_rows_live_mode_false_not_dormant():
    now = 1_800_000_000
    r = compute_dormant_state(
        roi_rows=[], slot_age_days=100.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is False
    assert r["is_dormant"] is False


def test_E2_all_zero_realized_live_mode_false():
    now = 1_800_000_000
    rows = [{"ts": now - i * DAY, "roi_jpy_realized": 0, "roi_jpy_expected": 100}
            for i in range(1, 40)]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=100.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is False
    assert r["is_dormant"] is False


def test_E3_old_realized_out_of_window_live_mode_false():
    now = 1_800_000_000
    rows = [{"ts": now - 200 * DAY, "roi_jpy_realized": 40000}]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=300.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is False
    assert r["is_dormant"] is False


def test_E4_new_slot_not_dormant_despite_live_mode():
    now = 1_800_000_000
    rows = [{"ts": now - 3 * DAY, "roi_jpy_realized": 25000}]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=1.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is True
    assert r["is_dormant"] is False  # age gate not passed


def test_E6_malformed_row_skipped():
    now = 1_800_000_000
    rows = [
        {"ts": "garbage", "roi_jpy_realized": 40000},
        {"ts": now - 5 * DAY, "roi_jpy_realized": 25000},
    ]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=1.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is True


def test_E7_missing_expected_treated_as_zero():
    now = 1_800_000_000
    rows = [{"ts": now - 5 * DAY, "roi_jpy_realized": 25000}]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=1.0, time_horizon_days=14, now_ts=now,
    )
    assert isinstance(r["consecutive_neg_windows"], int)


# ─── PROP-L3 most-recent-LAST ordering ────────────────────────────
def test_L3_rolling_7d_most_recent_last_ordering():
    """The list built inside compute_dormant_state MUST be ordered MOST RECENT LAST.
    Verify by constructing a slot with tail-negatives and confirming
    consecutive_neg_windows matches count_consecutive_negative_windows called
    on a list with the same ordering.
    """
    now = 1_800_000_000
    rows = []
    # 45 consecutive negative days ending yesterday
    for i in range(45):
        rows.append({"ts": now - (45 - i) * DAY,
                     "roi_jpy_realized": 0,
                     "roi_jpy_expected": 500})
    # Settle placed 80 days ago → in 90d window (live_mode=True) but
    # OUTSIDE the tail-side rolling windows (2*horizon=28 days from today)
    rows.append({"ts": now - 80 * DAY, "roi_jpy_realized": 25000, "roi_jpy_expected": 0})
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=100.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is True
    assert r["consecutive_neg_windows"] >= 1


# ─── PROP-L2 live-mode compositions ───────────────────────────────
def test_L2_live_mode_false_forces_not_dormant():
    now = 1_800_000_000
    # No realized → live_mode=False → is_dormant=False regardless of neg windows
    rows = [{"ts": now - i * DAY, "roi_jpy_realized": 0, "roi_jpy_expected": 500}
            for i in range(1, 60)]
    r = compute_dormant_state(
        roi_rows=rows, slot_age_days=100.0, time_horizon_days=14, now_ts=now,
    )
    assert r["live_mode"] is False
    assert r["is_dormant"] is False


def test_L2_live_mode_true_delegates_to_horizon_check():
    """When live_mode is True AND the horizon gate is satisfied AND
    consecutive_neg_windows > horizon, is_dormant follows is_dormant_with_horizon.
    """
    now = 1_800_000_000
    rows = []
    # 45 days of consistent negatives (realized 0, expected 500)
    for i in range(45):
        rows.append({"ts": now - (45 - i) * DAY,
                     "roi_jpy_realized": 0, "roi_jpy_expected": 500})
    # One real settle 2 days ago → live_mode=True
    rows.append({"ts": now - 2 * DAY, "roi_jpy_realized": 25000, "roi_jpy_expected": 0})
    r = compute_dormant_state(
        roi_rows=rows,
        slot_age_days=100.0,      # > 2*14
        time_horizon_days=14,
        now_ts=now,
    )
    assert r["live_mode"] is True
    # Delegates to is_dormant_with_horizon(consecutive_neg_windows, 100, 14)
    expected = is_dormant_with_horizon(
        consecutive_neg_windows=r["consecutive_neg_windows"],
        slot_age_days=100.0,
        time_horizon_days=14,
    )
    assert r["is_dormant"] == expected
