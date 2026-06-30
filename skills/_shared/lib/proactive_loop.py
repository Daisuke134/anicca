"""proactive_loop — orchestrator helper (sprint-2).

PROP-P11 (3-condition skip) + EDGE-S4-sink (durable unfixable.jsonl).
"""
from __future__ import annotations

import time
from pathlib import Path
from dataclasses import dataclass

from lib._common import append_jsonl


@dataclass
class PassResult:
    pass_id: str
    budget: str
    picked: str | None
    outcome: str
    next_candidate: str | None


def should_skip_step6(
    *,
    budget: str,
    tasks_pending: int,
    dormant: bool,
    unfixable_count: int,
) -> tuple[bool, str | None]:
    """REQ-P11 (FIND-2-004 fix: EXACTLY 3 conditions).
    Returns (skip, reason).
    """
    # (b) dormant sentinel — checked first (highest priority skip)
    if dormant:
        return True, "dormant-sentinel"
    # (c) cascading unfixable
    if unfixable_count >= 3:
        return True, "unfixable-cascade"
    # (a) MINIMAL budget AND no tasks
    if budget == "MINIMAL" and tasks_pending == 0:
        return True, "minimal-budget-no-tasks"
    return False, None


def write_unfixable_cascade_sink(
    *,
    slot_dir: Path | str,
    blockers: list[str],
    bot2bot_error: str | None = None,
) -> None:
    """EDGE-S4 sink: when all menu items blocked AND bot2bot.sh post fails, write
    a durable row to .unfixable.jsonl. Next pass surfaces it as a menu item.
    """
    slot_dir = Path(slot_dir)
    row = {
        "ts": int(time.time()),
        "kind": "menu-full-block-cascade",
        "blockers": list(blockers),
        "bot2bot_error": bot2bot_error,
        "surface_as_menu_item": True,
    }
    append_jsonl(slot_dir / ".unfixable.jsonl", row)
