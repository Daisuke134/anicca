#!/usr/bin/env python3
"""Report whether every OPEN talkroom is still being observed.

Why: on 2026-07-26 a thread looked unobserved for 10 hours and I assumed a coverage
bug. Measurement said otherwise -- observation stopped at 14:21 because the room
closed at 14:24, which is correct. The real gap was that closure never reached
earnings.jsonl (fixed by revenue_collector.py).

So this is NOT a fix for a present defect. It is the missing guard: nothing today
would notice if an OPEN thread silently stopped being polled, and an unobserved open
thread means missed buyer messages -- the expensive failure. Measured baseline at the
time of writing: the one open thread had 301 observations in 24h, max gap 10 min.

Closed rooms are expected to go stale and are not flagged: the open set comes from
the loop's own marketplace snapshot, and revenue for closed rooms settles separately.

Usage:
  thread_freshness.py                 # JSON verdict for the auditor
  thread_freshness.py --max-age-min 60
  thread_freshness.py --queue FILE    # explicit snapshot instead of the newest one
  thread_freshness.py --exit-nonzero-on-stale
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
EVIDENCE = STATE_DIR / "evidence"


def newest_queue() -> Path | None:
    """Newest marketplace snapshot.

    Deliberately NOT delivery-queue.json: that file lists rooms awaiting a delivery
    action, so a healthy open order with nothing pending shows up as an empty list
    (measured: the live IFU order yielded items=0). The snapshot's `orders` is the
    real set of open transactions.
    """
    files = glob.glob(str(EVIDENCE / "*" / "marketplace-snapshot.json"))
    if not files:
        return None
    return Path(max(files, key=os.path.getmtime))


def open_talkrooms(queue_path: Path | None) -> list[dict]:
    """Open rooms per the loop's own queue. Missing/torn queue -> empty, never crash."""
    if not queue_path or not queue_path.exists():
        return []
    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rooms = []
    for item in data.get("orders", []) or data.get("items", []) or []:
        room = item.get("talkroom_id")
        if not room:
            continue
        rooms.append(
            {
                "talkroom_id": str(room),
                "buyer": item.get("buyer"),
                "price_jpy": item.get("price_jpy"),
                "talkroom_state": item.get("talkroom_state"),
                "title": (item.get("title") or "")[:40],
            }
        )
    return rooms


def last_observed(talkroom_id: str) -> float | None:
    files = glob.glob(str(EVIDENCE / "*" / "live-dom" / f"talkroom-{talkroom_id}.json"))
    if not files:
        return None
    return max(os.path.getmtime(f) for f in files)


def check(max_age_min: int, queue_path: Path | None) -> dict:
    now = time.time()
    rooms = open_talkrooms(queue_path)
    results, stale = [], []
    for room in rooms:
        seen = last_observed(room["talkroom_id"])
        age_min = None if seen is None else round((now - seen) / 60, 1)
        row = {**room, "last_observed_age_min": age_min}
        results.append(row)
        if age_min is None or age_min > max_age_min:
            stale.append(row)
    if queue_path is None:
        verdict = "NO_SNAPSHOT (no marketplace-snapshot.json yet)"
    elif not rooms:
        verdict = "NO_OPEN_THREADS"
    elif stale:
        verdict = f"STALE ({len(stale)} open thread(s) unobserved > {max_age_min}min)"
    else:
        verdict = f"FRESH ({len(rooms)} open thread(s) observed within {max_age_min}min)"
    return {
        "ts": int(now),
        "check": "thread_freshness",
        "verdict": verdict,
        "max_age_min": max_age_min,
        "open_threads": len(rooms),
        "stale_threads": len(stale),
        "queue": str(queue_path) if queue_path else None,
        "threads": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-min", type=int, default=60)
    ap.add_argument("--queue")
    ap.add_argument("--exit-nonzero-on-stale", action="store_true")
    args = ap.parse_args()

    queue = Path(args.queue) if args.queue else newest_queue()
    verdict = check(args.max_age_min, queue)
    print(json.dumps(verdict, ensure_ascii=False))
    if args.exit_nonzero_on_stale and verdict["stale_threads"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
