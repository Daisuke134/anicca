"""menu — infinite-menu picker with ordered gates (sprint-2).

REQ-M3 canonical signature: pick_next(menu, log_tail, history, blockers, now_ts, budget) → dict|None
Ordered gates: (i) cadence (ii) budget (iii) blocker (iv) rank (v) novelty quota.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from lib.quota_tracker import Budget


_BUDGET_RANK = {
    Budget.FULL: 4, Budget.MEDIUM: 3, Budget.LIGHT: 2, Budget.MINIMAL: 1,
    "FULL": 4, "MEDIUM": 3, "LIGHT": 2, "MINIMAL": 1,
}


def compute_roi_score(item: dict) -> float:
    """roi_estimate × probability_of_landing."""
    return float(item.get("roi_estimate_jpy", 0)) * float(item.get("probability_of_landing", 0))


def is_blocker(item: dict, slot_state: dict) -> bool:
    """Item is blocked iff item.blocker_check is in slot_state.failing_blockers.
    Unknown blocker_check names default to NOT blocked (conservative).
    """
    check = item.get("blocker_check")
    if check is None:
        return False
    failing = slot_state.get("failing_blockers", set())
    if not isinstance(failing, set):
        failing = set(failing)
    return check in failing


def _passes_cadence(item: dict, log_tail: list, now_ts: int) -> bool:
    """Cadence gate: item not picked within min_cadence_seconds."""
    cad = item.get("min_cadence_seconds")
    if not cad:
        return True
    last_fired = None
    for row in reversed(log_tail):
        if row.get("picked") == item.get("name"):
            last_fired = int(row.get("ts", 0))
            break
    if last_fired is None:
        return True
    return (now_ts - last_fired) >= cad


def _passes_budget(item: dict, budget: Budget) -> bool:
    """Budget gate: item.required_budget <= current budget (per rank)."""
    req = item.get("required_budget")
    if not req:
        return True
    cur_rank = _BUDGET_RANK.get(budget, 0)
    req_rank = _BUDGET_RANK.get(req, 0)
    return cur_rank >= req_rank


def _passes_blocker(item: dict, blockers: set) -> bool:
    check = item.get("blocker_check")
    if check is None:
        return True
    return check not in blockers


def _is_novelty_eligible(item: dict, history: list) -> bool:
    """Novelty key is the (category, platform) tuple from sprint-1's REQ-H1."""
    key = (item.get("name"), item.get("platform"))
    seen = {(h.get("category"), h.get("platform")) for h in history if isinstance(h, dict)}
    return key not in seen


def pick_next(
    *, menu: dict, log_tail: list, history: list,
    blockers: set, now_ts: int, budget: Budget,
) -> dict | None:
    """Canonical 6-arg pick_next per REQ-M3."""
    if not menu or "categories" not in menu:
        return None

    candidates = []
    for item in menu["categories"]:
        if not _passes_cadence(item, log_tail, now_ts):
            continue
        if not _passes_budget(item, budget):
            continue
        if not _passes_blocker(item, blockers):
            continue
        candidates.append(item)

    if not candidates:
        return None

    # Rank by ROI score
    candidates.sort(key=compute_roi_score, reverse=True)

    # Novelty quota — if ratio of novelty-eligible picks is below threshold, promote one
    novelty_ratio = float(menu.get("novelty_quota_ratio", 0.1))
    novel_items = [c for c in candidates if _is_novelty_eligible(c, history)]
    if novel_items and len(history) >= 10:
        # Check current novelty ratio
        recent_picks = [(h.get("category"), h.get("platform")) for h in history[-10:]]
        unique_recent = len(set(recent_picks))
        if unique_recent / 10 < novelty_ratio:
            return novel_items[0]

    return candidates[0]


def load_menu(path: Path) -> dict:
    """REQ-M2: load menu.json with malformed-fallback."""
    path = Path(path)
    try:
        return json.loads(path.read_text())
    except Exception:
        return {
            "schema_version": 1,
            "categories": [{"name": "pending", "roi_estimate_jpy": 0,
                            "probability_of_landing": 0,
                            "note": "menu.json malformed; investigate"}],
            "novelty_quota_ratio": 0.1,
        }
