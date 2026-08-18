#!/usr/bin/env python3
"""Classify a validated paid progress send for finalize-only handling.

The caller must run the queue-bound browser evidence validator first.  This
module decides only whether the remaining queue state is the single expected
non-terminal blocker: formal delivery has not yet been confirmed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_PENDING_BLOCKERS = ["formal_delivery_not_confirmed"]


def finalize_reason(queue_item: Any) -> str | None:
    if not isinstance(queue_item, dict):
        raise ValueError("queue item is not an object")
    queue_class = queue_item.get("queue_class")
    delivery_action = queue_item.get("delivery_action")
    blockers = queue_item.get("blockers")
    if not isinstance(queue_class, str) or not queue_class:
        raise ValueError("queue_class is missing or invalid")
    if not isinstance(delivery_action, str) or not delivery_action:
        raise ValueError("delivery_action is missing or invalid")
    if not isinstance(blockers, list) or not all(isinstance(item, str) and item for item in blockers):
        raise ValueError("blockers are missing or invalid")
    if delivery_action != "progress" or blockers != EXPECTED_PENDING_BLOCKERS:
        return None
    return f"validated_paid_progress_formal_pending:{queue_class}"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: paid_progress_finalize_gate.py QUEUE_ITEM.json", file=sys.stderr)
        return 2
    try:
        queue_item = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        reason = finalize_reason(queue_item)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"paid progress finalize gate invalid: {exc}", file=sys.stderr)
        return 2
    if reason is None:
        return 1
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
