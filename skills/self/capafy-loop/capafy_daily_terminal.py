#!/usr/bin/env python3
"""Append and audit durable daily-owner terminal evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path


STATE_HOME = Path(os.environ.get("LIFE_MANAGER_STATE_HOME", Path.home() / ".local/state/life-manager"))
DEFAULT_LEDGER = STATE_HOME / "state/capafy-daily-terminals.jsonl"


def append_event(path: Path, execution_id: str, phase: str, rc: int | None, verdict: str | None,
                 observed_at: str | None = None) -> dict:
    now = observed_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    event = {"schema_version": 1, "execution_id": execution_id, "phase": phase,
             "observed_at": now, "local_date": dt.datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone().date().isoformat()}
    if phase == "terminal":
        event.update({"rc": rc, "verdict": verdict, "healthy": rc == 0})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, 0o600)
    return event


def streak_status(path: Path, today: str | None = None) -> dict:
    rows = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("execution_id") and row.get("local_date"):
                rows.append(row)
    by_execution: dict[str, dict] = {}
    for row in rows:
        state = by_execution.setdefault(str(row["execution_id"]), {"started": False, "terminal": None, "date": row["local_date"]})
        if row.get("phase") == "started":
            state["started"] = True
        elif row.get("phase") == "terminal":
            state["terminal"] = row
    by_day: dict[str, list[dict]] = {}
    for state in by_execution.values():
        by_day.setdefault(state["date"], []).append(state)
    day = dt.date.fromisoformat(today) if today else dt.datetime.now().astimezone().date()
    streak = 0
    while True:
        states = by_day.get(day.isoformat())
        if not states or any(not state["started"] or not state["terminal"] or not state["terminal"].get("healthy") for state in states):
            break
        streak += 1
        day -= dt.timedelta(days=1)
    return {"schema_version": 1, "consecutive_healthy_days": streak, "required": 7,
            "pass": streak >= 7, "days_observed": len(by_day)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "finish", "status"))
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--execution-id")
    parser.add_argument("--rc", type=int)
    parser.add_argument("--verdict")
    parser.add_argument("--today")
    args = parser.parse_args()
    if args.action == "status":
        value = streak_status(args.ledger, args.today)
    else:
        if not args.execution_id:
            parser.error("--execution-id is required")
        value = append_event(args.ledger, args.execution_id,
                             "started" if args.action == "start" else "terminal",
                             args.rc, args.verdict)
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
