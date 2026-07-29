#!/usr/bin/env python3
"""Fail-closed deterministic gate for the lower-priority B2 apply step."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BLOCKING_QUEUE_CLASSES = frozenset(
    {
        "overdue_or_today_paid_deliverable",
        "buyer_feedback_or_revision",
        "quote_needing_proposal",
        "other_paid_work",
    }
)
LOWER_PRIORITY_QUEUE_CLASSES = frozenset({"nurture", "listing_apply_learn"})


def policy_skip_reason(queue: Any) -> str | None:
    if not isinstance(queue, dict):
        raise ValueError("queue is not an object")
    items = queue.get("items")
    if not isinstance(items, list):
        raise ValueError("queue items is not a list")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("queue item is not an object")
        queue_class = item.get("queue_class")
        if not isinstance(queue_class, str) or not queue_class:
            raise ValueError("queue_class is missing or not a string")
        if queue_class not in BLOCKING_QUEUE_CLASSES:
            if queue_class not in LOWER_PRIORITY_QUEUE_CLASSES:
                raise ValueError(f"unknown queue_class: {queue_class}")
            continue
        identity = str(
            item.get("request_id")
            or item.get("talkroom_id")
            or item.get("contract_id")
            or "unknown"
        )
        return f"B2:unresolved_higher_priority_queue:{queue_class}:{identity}"
    return None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: b2_queue_gate.py QUEUE.json", file=sys.stderr)
        return 2
    try:
        queue = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        reason = policy_skip_reason(queue)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"B2 queue gate unreadable: {exc}", file=sys.stderr)
        return 2
    if reason is None:
        return 1
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
