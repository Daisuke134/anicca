"""PROP-P11 + EDGE-S4-sink + P0/P10 status — proactive-loop orchestrator.

Tests the Python-side orchestrator helper that proactive-loop.sh delegates to.
"""
from __future__ import annotations

import json
import pytest

from lib.proactive_loop import (  # FAIL until 2b
    should_skip_step6,
    write_unfixable_cascade_sink,
    PassResult,
)


# ─── PROP-P11-skip (3 conditions, FIND-2-004 fix) ─────────────────
def test_skip_when_minimal_budget_and_no_tasks():
    skip, reason = should_skip_step6(
        budget="MINIMAL", tasks_pending=0, dormant=False, unfixable_count=0
    )
    assert skip is True
    assert reason == "minimal-budget-no-tasks"


def test_skip_when_dormant_sentinel_present():
    skip, reason = should_skip_step6(
        budget="FULL", tasks_pending=10, dormant=True, unfixable_count=0
    )
    assert skip is True
    assert reason == "dormant-sentinel"


def test_skip_when_3_plus_unfixable_cascade():
    skip, reason = should_skip_step6(
        budget="FULL", tasks_pending=0, dormant=False, unfixable_count=3
    )
    assert skip is True
    assert reason == "unfixable-cascade"


def test_no_skip_when_none_of_3_match():
    skip, reason = should_skip_step6(
        budget="FULL", tasks_pending=0, dormant=False, unfixable_count=0
    )
    assert skip is False


def test_no_skip_when_minimal_but_has_tasks():
    """MINIMAL alone is NOT a skip if there are owner tasks to process."""
    skip, reason = should_skip_step6(
        budget="MINIMAL", tasks_pending=5, dormant=False, unfixable_count=0
    )
    assert skip is False


# ─── PROP-EDGE-S4-sink (required:false; FIND-018 carry) ───────────
def test_full_block_writes_unfixable_durable(tmp_path):
    """When all menu items blocked AND bot2bot also fails, write a durable
    .unfixable.jsonl entry so the NEXT pass surfaces it as a menu item."""
    unfixable = tmp_path / ".unfixable.jsonl"
    write_unfixable_cascade_sink(
        slot_dir=tmp_path,
        blockers=["coconala_search_reachable", "nurture_room_reachable"],
        bot2bot_error="gh API rate-limited",
    )
    assert unfixable.exists()
    rows = [json.loads(l) for l in unfixable.read_text().splitlines() if l.strip()]
    assert len(rows) >= 1
    assert "blockers" in rows[0]
    assert "bot2bot_error" in rows[0]
    assert rows[0]["surface_as_menu_item"] is True
