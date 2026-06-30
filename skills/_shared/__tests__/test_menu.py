"""PROP-P7 + M3 + cadence + blocker-gate + novelty-key — menu picker (sprint-2).

Spec REQ-M3 canonical: pick_next(menu, log_tail, history, blockers, now_ts, budget)
Ordered gates: (i) cadence (ii) budget (iii) blocker (iv) rank (v) novelty.
"""
from __future__ import annotations

import pytest

# FIND-002 fix (sprint-2 carry): novelty_quota_ratio=0 must not crash pick_next.
import pytest as _pytest_for_novelty_guard

from lib.menu import (  # FAIL until 2b
    Budget,
    pick_next,
    is_blocker,
    compute_roi_score,
)


def _menu_3items():
    return {
        "schema_version": 1,
        "categories": [
            {"name": "scan-requests", "roi_estimate_jpy": 50000, "probability_of_landing": 0.05,
             "required_budget": "LIGHT", "blocker_check": None, "platform": "coconala"},
            {"name": "nurture-talk-rooms", "roi_estimate_jpy": 30000, "probability_of_landing": 0.20,
             "required_budget": "LIGHT", "blocker_check": None, "platform": "coconala"},
            {"name": "adversary-daily", "roi_estimate_jpy": 1000, "probability_of_landing": 1.0,
             "required_budget": "FULL", "blocker_check": None, "platform": "internal",
             "min_cadence_seconds": 86400},
        ],
        "novelty_quota_ratio": 0.1,
    }


# ─── PROP-P7-pivot (required:true) ────────────────────────────────
def test_pick_next_returns_highest_unblocked_roi():
    menu = _menu_3items()
    result = pick_next(menu=menu, log_tail=[], history=[], blockers=set(),
                      now_ts=1782900000, budget=Budget.FULL)
    # nurture: 30000 × 0.20 = 6000. scan: 50000 × 0.05 = 2500. adversary: 1000 × 1.0 = 1000.
    assert result["name"] == "nurture-talk-rooms"


def test_pick_next_pivots_when_primary_blocked():
    menu = _menu_3items()
    blockers = {"nurture_talk_room_reachable"}
    menu["categories"][1]["blocker_check"] = "nurture_talk_room_reachable"
    result = pick_next(menu=menu, log_tail=[], history=[], blockers=blockers,
                      now_ts=1782900000, budget=Budget.FULL)
    # nurture blocked → fall to scan (2500) > adversary (1000)
    assert result["name"] == "scan-requests"


def test_pick_next_returns_None_when_all_excluded():
    menu = _menu_3items()
    for cat in menu["categories"]:
        cat["blocker_check"] = "always_blocked"
    blockers = {"always_blocked"}
    assert pick_next(menu=menu, log_tail=[], history=[], blockers=blockers,
                    now_ts=1782900000, budget=Budget.FULL) is None


# ─── PROP-cadence (required:false but needs test) ─────────────────
def test_pick_next_excludes_recently_fired_cadence_items():
    menu = _menu_3items()
    # adversary-daily last fired 3600s ago (within 86400 cadence)
    log_tail = [{"picked": "adversary-daily", "ts": 1782896400}]
    result = pick_next(menu=menu, log_tail=log_tail, history=[], blockers=set(),
                      now_ts=1782900000, budget=Budget.FULL)
    # adversary excluded by cadence → nurture (highest ROI of remaining)
    assert result["name"] == "nurture-talk-rooms"


def test_pick_next_allows_cadence_item_after_window():
    menu = _menu_3items()
    # Force nurture + scan low ROI so adversary wins on rank if cadence passes
    menu["categories"][0]["roi_estimate_jpy"] = 100
    menu["categories"][1]["roi_estimate_jpy"] = 100
    log_tail = [{"picked": "adversary-daily", "ts": 1782900000 - 90000}]  # >86400s ago
    result = pick_next(menu=menu, log_tail=log_tail, history=[], blockers=set(),
                      now_ts=1782900000, budget=Budget.FULL)
    # adversary now eligible (cadence elapsed) and wins on ROI score:
    # adversary: 1000 × 1.0 = 1000; nurture: 100 × 0.20 = 20; scan: 100 × 0.05 = 5
    assert result["name"] == "adversary-daily"


# ─── PROP-P8-budget-depth via budget gate ─────────────────────────
def test_pick_next_excludes_items_above_budget():
    menu = _menu_3items()
    # adversary requires FULL; budget is MEDIUM
    result = pick_next(menu=menu, log_tail=[], history=[], blockers=set(),
                      now_ts=1782900000, budget=Budget.MEDIUM)
    # nurture-talk-rooms requires LIGHT → fits MEDIUM; should win
    assert result["name"] == "nurture-talk-rooms"


# ─── PROP-blocker-gate (required:false) ───────────────────────────
def test_is_blocker_returns_true_when_check_in_blockers():
    item = {"blocker_check": "coconala_search_reachable"}
    assert is_blocker(item, slot_state={"failing_blockers": {"coconala_search_reachable"}}) is True


def test_is_blocker_returns_false_when_no_check():
    item = {"blocker_check": None}
    assert is_blocker(item, slot_state={"failing_blockers": set()}) is False


def test_is_blocker_returns_false_when_unknown_check():
    """Unknown blocker_check defaults to NOT blocked (= conservative)."""
    item = {"blocker_check": "unknown_check_name"}
    assert is_blocker(item, slot_state={"failing_blockers": set()}) is False


# ─── PROP-novelty-key-aligned (required:true; FIND-004 + FIND-2-006 fix) ─
def test_novelty_promotes_unseen_category_platform():
    """Novelty quota: when history is saturated with one (cat, platform) tuple,
    the picker should promote a (cat, platform) NOT in history (= novelty)."""
    menu = {
        "schema_version": 1,
        "categories": [
            # high ROI but fully-seen
            {"name": "scan", "category": "scan-requests", "platform": "coconala",
             "roi_estimate_jpy": 100000, "probability_of_landing": 0.20,
             "required_budget": "LIGHT", "blocker_check": None},
            # low ROI but never-tried (= novel)
            {"name": "explore", "category": "explore-affiliate", "platform": "amazon",
             "roi_estimate_jpy": 100, "probability_of_landing": 0.05,
             "required_budget": "LIGHT", "blocker_check": None},
        ],
        "novelty_quota_ratio": 0.1,
    }
    # 10 picks of scan-requests/coconala = saturated; novel one not in history
    history = [{"category": "scan-requests", "platform": "coconala"}] * 10
    result = pick_next(menu=menu, log_tail=[], history=history, blockers=set(),
                      now_ts=1782900000, budget=Budget.FULL)
    # Real assertion (= NOT tautological): the novel item beats high-ROI saturated one
    assert result is not None
    assert result["name"] == "explore", \
        f"novelty quota should promote explore-affiliate (unseen), got {result['name']}"


def test_novelty_uses_category_key_not_name():
    """FIND-2-007: novelty key reads .category from item AND history (not .name)."""
    menu = {
        "schema_version": 1,
        "categories": [
            # item.name differs from item.category — verify key picks category
            {"name": "scan-v2", "category": "scan-requests", "platform": "coconala",
             "roi_estimate_jpy": 1000, "probability_of_landing": 0.1,
             "required_budget": "LIGHT"},
            {"name": "new", "category": "explore", "platform": "amazon",
             "roi_estimate_jpy": 100, "probability_of_landing": 0.05,
             "required_budget": "LIGHT"},
        ],
        "novelty_quota_ratio": 0.1,
    }
    # scan-requests/coconala saturated via history
    history = [{"category": "scan-requests", "platform": "coconala"}] * 10
    result = pick_next(menu=menu, log_tail=[], history=history, blockers=set(),
                      now_ts=1782900000, budget=Budget.FULL)
    # Even though scan-v2 has higher ROI, it's NOT novel (its .category matches history);
    # novelty quota promotes the unseen explore category
    assert result["name"] == "new"


# ─── compute_roi_score basic ──────────────────────────────────────
def test_compute_roi_score_is_product():
    item = {"roi_estimate_jpy": 10000, "probability_of_landing": 0.2}
    assert compute_roi_score(item) == pytest.approx(2000.0, abs=0.01)


# ─── FIND-002 fix: novelty_ratio=0 guard (sprint-2 carry) ─────────
class TestNoveltyRatioZeroGuard:
    """REQ-M3 + FIND-002: novelty_quota_ratio == 0.0 means novelty disabled.
    Prior code: int(1.0 / 0.0) → ZeroDivisionError on first tick of any slot
    with novelty disabled (e.g. an adversary-only slot). Fix: gate with > 0."""

    def test_novelty_ratio_zero_does_not_crash(self):
        menu = {
            "schema_version": 1,
            "categories": [
                {"name": "a", "category": "x", "platform": "p",
                 "roi_estimate_jpy": 100, "probability_of_landing": 0.5,
                 "required_budget": "LIGHT", "min_cadence_seconds": 0},
            ],
            "novelty_quota_ratio": 0.0,
        }
        # Should NOT raise; should return the only candidate.
        from lib.quota_tracker import Budget
        result = pick_next(menu=menu, log_tail=[], history=[],
                           blockers=set(), now_ts=0, budget=Budget.LIGHT)
        assert result is not None
        assert result.get("name") == "a"

    def test_novelty_ratio_zero_with_history_does_not_crash(self):
        menu = {
            "schema_version": 1,
            "categories": [
                {"name": "a", "category": "scan", "platform": "coconala",
                 "roi_estimate_jpy": 100, "probability_of_landing": 0.5,
                 "required_budget": "LIGHT", "min_cadence_seconds": 0},
            ],
            "novelty_quota_ratio": 0.0,
        }
        # History present too — would have triggered the divide on the old code path
        from lib.quota_tracker import Budget
        result = pick_next(
            menu=menu, log_tail=[],
            history=[{"category": "scan", "platform": "coconala"}] * 20,
            blockers=set(), now_ts=0, budget=Budget.LIGHT,
        )
        assert result is not None
        assert result.get("name") == "a"

    def test_novelty_ratio_negative_treated_as_disabled(self):
        # Defensive: negative ratio should also not crash.
        menu = {
            "schema_version": 1,
            "categories": [
                {"name": "a", "category": "x", "platform": "p",
                 "roi_estimate_jpy": 100, "probability_of_landing": 0.5,
                 "required_budget": "LIGHT", "min_cadence_seconds": 0},
            ],
            "novelty_quota_ratio": -0.5,
        }
        from lib.quota_tracker import Budget
        result = pick_next(menu=menu, log_tail=[], history=[],
                           blockers=set(), now_ts=0, budget=Budget.LIGHT)
        assert result is not None
