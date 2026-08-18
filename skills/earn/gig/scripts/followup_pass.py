#!/usr/bin/env python3
"""Plan one pass of follow-ups, and record the ones that landed.

Two commands, deliberately separate: ``build`` runs before the browser and decides who is
contacted, ``record`` runs after and writes down who was. Splitting them means a crash
between the two loses a message rather than the memory of one -- the safe direction, since
the cap that keeps this lane from becoming harassment is counted from what was recorded.

Neither command can fail the pass. The buyers who wrote to us are answered by
INQUIRY_REPLY; this lane exists to add revenue on top, and taking the pass down to protect
a sales message would cost more than the message is worth.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import followup_candidates  # noqa: E402
import followup_ledger  # noqa: E402
import followup_queue  # noqa: E402
import followup_source  # noqa: E402


def _load_json(path: str) -> dict:
    try:
        with open(str(path), encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json(path: str, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)


def build(args: argparse.Namespace) -> int:
    snapshot = _load_json(args.snapshot)
    sent_counts = followup_ledger.followups_sent(args.ledger)
    send_times = followup_source.transcript_send_times(args.transcripts)
    now = int(time.time())
    rows = followup_source.candidate_rows(
        snapshot, followups_sent=sent_counts, send_times=send_times, now=now
    )
    selected = followup_candidates.select(rows, now=now, limit=args.limit)
    queue = followup_queue.build(selected, now=datetime.now(timezone.utc))
    # Why the other rows were left out, counted. Without this the lane reports "0 items"
    # for a fortnight and nobody can tell a healthy quiet inbox from a broken filter.
    reasons: dict[str, int] = {}
    for row in rows:
        reason = followup_candidates.exclusion_reason(row, now=now)
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
    queue["considered"] = len(rows)
    queue["excluded"] = reasons
    _write_json(args.output, queue)
    return 0


def record(args: argparse.Namespace) -> int:
    result = _load_json(args.result)
    now = int(time.time())
    for event in result.get("events") or []:
        if not isinstance(event, dict):
            continue
        # Only a send the lane verified against the live thread counts. reply_lane projects
        # an event solely for a verified result and stamps it status="replied"; measured
        # against a real reply-lane-result.json, there is no "verified" key to read.
        # Recording an attempt would spend one of the three chances this buyer gets on a
        # message that may never have arrived.
        if str(event.get("status") or "") != "replied":
            continue
        thread_id = str(event.get("talkroom_id") or "")
        if thread_id:
            followup_ledger.record_followup(args.ledger, thread_id=thread_id, sent_at=now)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("build")
    plan.add_argument("--snapshot", required=True)
    plan.add_argument("--transcripts", required=True)
    plan.add_argument("--ledger", required=True)
    plan.add_argument("--output", required=True)
    plan.add_argument("--limit", type=int, default=followup_candidates.DEFAULT_PER_PASS_LIMIT)
    plan.set_defaults(handler=build)

    done = sub.add_parser("record")
    done.add_argument("--result", required=True)
    done.add_argument("--ledger", required=True)
    done.set_defaults(handler=record)

    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
