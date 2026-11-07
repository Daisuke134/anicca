"""Read the one canonical, sequential Manager implementation cursor.

The operational source of truth is the existing company SSOT; P00–P12
lessons, BFM project documents and phase G-numbers are references rather than
parallel execution queues. This module only reads text and never mutates the
SSOT, production runtime, customer accounts, model, or environment.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = "manager.single_cursor.v1"
SSOT = Path(__file__).resolve().parents[3] / (
    "docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md"
)
MARKER = "## MANAGER｜唯一の順番付き実装TODO"
ID_RE = re.compile(r"^\*{0,2}MG-(\d{2})( ← NOW)?\*{0,2}$")


def parse_manager_queue(document: str) -> dict:
    """Reject a second current item, gaps, duplicates, and future completions."""
    if type(document) is not str or document.count(MARKER) != 1:
        raise ValueError("canonical Manager queue missing or ambiguous")
    section = document.split(MARKER, 1)[1].split("\n---\n", 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        fields = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(fields) != 4:
            continue
        match = ID_RE.fullmatch(fields[0])
        if match is None:
            continue
        rows.append((int(match.group(1)), match.group(2) is not None, fields[1], fields[2], fields[3]))
    if not rows or [item[0] for item in rows] != list(range(1, len(rows) + 1)):
        raise ValueError("Manager IDs missing, duplicated, or out of order")
    now = [i for i, row in enumerate(rows) if row[1]]
    if len(now) != 1:
        raise ValueError("exactly one current Manager item required")
    current_index = now[0]
    for index, (_, _, status, _task, _acceptance) in enumerate(rows):
        normalized = status.strip("* ").strip()
        # "未完了" contains the characters "完了" but means NOT complete.
        # Determine advancement from the explicit leading status, not a substring.
        is_complete = normalized.startswith("完了")
        is_active = normalized.startswith("進行中") or normalized.startswith("作業中")
        if index < current_index and not is_complete:
            raise ValueError("prior Manager item not complete")
        if index == current_index and not is_active:
            raise ValueError("current Manager item must be in progress")
        if index > current_index and (is_complete or is_active):
            raise ValueError("future Manager item cannot be completed or active")
    item = rows[current_index]
    return {
        "schema": SCHEMA,
        "current_id": f"MG-{item[0]:02d}",
        "total_ordered_items": len(rows),
        "task": item[3],
        "acceptance": item[4],
        "done": False,
        "current_status": item[2].strip("* "),
        "historical_learning_and_G_phase_aliases_are_not_other_cursors": True,
    }


def read_current_manager_task(path: Path = SSOT) -> dict:
    """Read only the existing canonical company SSOT, no additional TODO files."""
    return parse_manager_queue(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(read_current_manager_task(), ensure_ascii=False, indent=2))
