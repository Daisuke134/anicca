#!/usr/bin/env python3
"""Generic, request-scoped project state and append-only delivery ledger.

The runner supplies a request id and marketplace adapter; no customer or site is
embedded in this module.  State is a materialized view, while events.jsonl is
the audit trail and is never rewritten.
"""
import argparse
import json
import time
from pathlib import Path
from typing import Any

PROJECT_DIRS = ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence")


def init_project(base: str | Path, request_id: str, adapter: str, state: dict[str, Any] | None = None) -> Path:
    if not request_id or not adapter:
        raise ValueError("request_id and adapter are required")
    root = Path(base) / request_id
    for name in PROJECT_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    initial = {"request_id": request_id, "adapter": adapter, **(state or {})}
    initial["request_id"] = request_id
    initial["adapter"] = adapter
    _write_state(root, initial)
    _append_event(root, "project_initialized", initial)
    return root


def _read_state(root: Path) -> dict[str, Any]:
    path = root / "state.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _write_state(root: Path, state: dict[str, Any]) -> None:
    tmp = root / "state.json.tmp"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(root / "state.json")


def _append_event(root: Path, event: str, state: dict[str, Any]) -> None:
    row = {"ts": time.time(), "request_id": state["request_id"], "adapter": state["adapter"], "event": event, "state": state}
    with (root / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def append(root: str | Path, state: dict[str, Any], event: str) -> dict[str, Any]:
    root = Path(root)
    current = _read_state(root)
    if not current.get("request_id") or not current.get("adapter"):
        raise ValueError("project must be initialized")
    supplied = state.get("request_id")
    if supplied is not None and supplied != current["request_id"]:
        raise ValueError("request_id mismatch")
    merged = {**current, **state, "request_id": current["request_id"], "adapter": current["adapter"], "updated_at": time.time()}
    _write_state(root, merged)
    _append_event(root, event, merged)
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("event")
    parser.add_argument("--state", default="{}")
    args = parser.parse_args()
    append(args.root, json.loads(args.state), args.event)
