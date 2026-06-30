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
    """Novelty key (category, platform). FIND-011 fix: read 'category' from BOTH
    item (= the menu item's category field, NOT 'name') and history (= row's category).
    Items without 'category' fall back to their 'name' as a category alias.
    """
    item_category = item.get("category", item.get("name"))
    key = (item_category, item.get("platform"))
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

    # Novelty quota (FIND-003 fix: aligns to REQ-M3(v) verbatim — measures
    # NOVELTY-PICK RATE over history, not uniqueness). Spec: at least 10% of picks
    # across history must be (category, platform) tuples not previously present.
    novelty_ratio = float(menu.get("novelty_quota_ratio", 0.1))
    novel_items = [c for c in candidates if _is_novelty_eligible(c, history)]
    # Guard: novelty_ratio == 0 means "disabled" → never force a novelty pick.
    if novel_items and novelty_ratio > 0 and len(history) >= int(1.0 / novelty_ratio):
        # Count how many of the last 1/ratio picks were novel at the time of selection.
        # We approximate via: of the last N picks (N = 1/ratio), how many introduced a
        # new (category, platform) key. If < ratio, promote a novel item this pass.
        window = int(1.0 / novelty_ratio)
        recent = history[-window:]
        seen_before_each: list[bool] = []
        seen_set: set = set()
        for r in history[: -window]:
            seen_set.add((r.get("category"), r.get("platform")))
        for r in recent:
            key = (r.get("category"), r.get("platform"))
            was_novel = key not in seen_set
            seen_set.add(key)
            seen_before_each.append(was_novel)
        novel_count = sum(1 for x in seen_before_each if x)
        if novel_count < int(novelty_ratio * window) + 1:
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
