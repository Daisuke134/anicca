#!/usr/bin/env python3
"""record_cost_event_cli.py — thin CLI wrapper around budget.build_cost_event/record_cost_event
(REQ-CEO-020). Called via record-cost-event.sh by each roster loop's OWN pass-end reporting hook
(the same STARTUP prompt that already calls loop-report.sh, one line added alongside it) -- never by
the CEO WEEKLY pass itself, which only ever READS ceo-cost-events.jsonl (budget.load_cost_events)."""
from __future__ import annotations

import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import budget  # noqa: E402


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: record_cost_event_cli.py <loop> <usd_estimate> <state_dir>", file=sys.stderr)
        return 1
    loop, usd_estimate_raw, state_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        usd_estimate = float(usd_estimate_raw)
    except ValueError:
        print(f"usd_estimate must be a number, got {usd_estimate_raw!r}", file=sys.stderr)
        return 1
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event = budget.build_cost_event(ts, loop, usd_estimate)
    path = os.path.join(state_dir, "ceo-cost-events.jsonl")
    budget.record_cost_event(path, event)
    print(f"recorded cost event: {event}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
