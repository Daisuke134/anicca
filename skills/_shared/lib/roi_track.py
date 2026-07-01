"""Per-pass ROI tracker for proactive-loop tick.

Sprint-3 #34 REQ-W1..W5. Row schema:
  {schema_version:1, ts, pass_id, slot, budget, picked, outcome,
   roi_jpy_realized (default 0), roi_jpy_expected (default 0)}.

roi_jpy_realized stays 0 for all of sprint-3; sprint-4 wires LAYER C settle
callback to update it. See spec §1 for the dead-code deferral rationale.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


def compute_expected_jpy(picked: Optional[dict]) -> int:
    """PROP-W3: int(roi_estimate_jpy × probability_of_landing) with EDGE-E6/E7 handling."""
    if not isinstance(picked, dict):
        return 0
    try:
        roi = float(picked.get("roi_estimate_jpy", 0) or 0)
        prob = float(picked.get("probability_of_landing", 0) or 0)
    except (TypeError, ValueError):
        return 0
    # EDGE-E7: clamp probability to [0, 1]
    prob = max(0.0, min(1.0, prob))
    return int(roi * prob)


def roi_row(
    *,
    ts: int,
    pass_id: str,
    slot: str,
    budget: str,
    picked: Optional[str] | Optional[dict],
    outcome: str,
    realized: int = 0,
    expected: int = 0,
) -> dict:
    """Build a roi.jsonl row dict. Caller is responsible for computing
    `expected` from the picked menu item (via compute_expected_jpy)."""
    # For the JSON row, `picked` is the item's NAME (str) or None; the full
    # menu dict is captured in the tasks/ descriptor instead.
    if isinstance(picked, dict):
        picked_name = picked.get("name")
    else:
        picked_name = picked  # str or None
    return {
        "schema_version": 1,
        "ts": int(ts),
        "pass_id": str(pass_id),
        "slot": str(slot),
        "budget": str(budget),
        "picked": picked_name,
        "outcome": str(outcome),
        "roi_jpy_realized": int(realized),
        "roi_jpy_expected": int(expected),
    }


def append_roi_row(roi_jsonl_path: Path | str, row: dict) -> dict:
    """REQ-W1 + W4 + W5: best-effort append; never crash. Returns {ok, status}."""
    p = Path(roi_jsonl_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "status": f"roi-write-failed-mkdir-{type(e).__name__}"}
    try:
        # Single line + trailing newline. Concurrent writes to the same file
        # cannot happen because proactive-loop.sh's fcntl re-entrancy guard
        # serializes ticks within one slot (per spec REQ-W4).
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as e:
        return {"ok": False, "status": f"roi-write-failed-{type(e).__name__}"}
    return {"ok": True, "status": "roi-written"}
