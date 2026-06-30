"""STEP 6 ACT — tasks/ enqueue. PURE helpers + one I/O sink.

Per sprint-3 #33 spec REQ-T1..T5. Single source of truth for filename
formatting + descriptor shape. Cross-platform.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

_KEEP_RE = re.compile(r"[^a-z0-9_-]")
_COLLAPSE_DASH = re.compile(r"-+")


def sanitize_name(name: str) -> str:
    """REQ-T3: lowercase → keep [a-z0-9_-] → collapse runs of '-' → fallback 'unnamed'."""
    if not isinstance(name, str):
        return "unnamed"
    lowered = name.lower()
    kept = _KEEP_RE.sub("-", lowered)
    collapsed = _COLLAPSE_DASH.sub("-", kept).strip("-")
    return collapsed or "unnamed"


def task_filename(*, ts: int, pass_id: str, name: str) -> str:
    """REQ-T1: <unix_ts>-<pass_id>-<sanitized_name>.json."""
    return f"{int(ts)}-{pass_id}-{sanitize_name(name)}.json"


def task_descriptor(
    *, pass_id: str, ts: int, picked: dict, budget: str, slot: str,
) -> dict:
    """REQ-T2: 7-key shape."""
    return {
        "schema_version": 1,
        "pass_id": pass_id,
        "ts": int(ts),
        "picked": picked,
        "budget": str(budget),
        "proactive_loop_origin": "step6-act",
        "slot": slot,
    }


def enqueue_task_descriptor(
    slot_dir: Path | str, descriptor: dict,
) -> dict:
    """REQ-T1 + T4 + EDGE-E1/E3/E8: write task file unless dup pass_id."""
    slot = Path(slot_dir)
    tasks_dir = slot / "tasks"
    try:
        tasks_dir.mkdir(parents=True, exist_ok=True)  # EDGE-E1
    except OSError as e:
        return {"ok": False, "status": f"enqueue-failed-mkdir-{type(e).__name__}"}

    pass_id = descriptor.get("pass_id")
    if not pass_id:
        return {"ok": False, "status": "enqueue-failed-no-pass-id"}

    # REQ-T4 / EDGE-E3: detect duplicate via glob('*-<pass_id>-*.json')
    if list(tasks_dir.glob(f"*-{pass_id}-*.json")):
        return {"ok": False, "status": "enqueue-skipped-dup"}

    picked = descriptor.get("picked") or {}
    name = picked.get("name", "") if isinstance(picked, dict) else ""
    fn = task_filename(ts=descriptor.get("ts", 0), pass_id=pass_id, name=name)
    out_path = tasks_dir / fn

    try:
        # Atomic-ish: write to tmp + rename. Avoids partial-write reads.
        tmp_path = tasks_dir / f".{fn}.tmp"
        tmp_path.write_text(json.dumps(descriptor, indent=2))
        tmp_path.rename(out_path)
    except OSError as e:
        return {"ok": False, "status": f"enqueue-failed-write-{type(e).__name__}"}

    return {"ok": True, "filename": fn, "status": "enqueued"}
