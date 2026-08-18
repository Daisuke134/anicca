#!/usr/bin/env python3
"""Schema gate for the B2 apply step. ★ It no longer reads the paid queue's state. ★

A13 (2026-08-08). This module used to answer "does an unresolved paid item exist?"
and, if so, shut the application lane for the whole pass. Measured that morning::

    STEP B2 skipped (policy B2:unresolved_higher_priority_queue:buyer_feedback_or_revision:91000001)

repeated on six consecutive passes while order 91000001 could not move at all. One
existing customer's jam was therefore also a ban on acquiring new customers -- and
new-customer intake is the one lane whose throughput has no ceiling.

★ The apply lane and the paid lane share a resource (the CDP lease, held for the
whole pass) but have no dependency. ★ Nothing an application does can make a paid
order worse, and nothing a stuck paid order implies about an application. Spec
`docs/loop-engineering/35-gig-no-head-of-line-blocking-design.md` §4 rule 3.

What remains is a schema check, and only a schema check: a queue that cannot be
parsed, or that carries a ``queue_class`` no consumer in this repository knows,
means a producer changed under us. That is fail-closed for the same reason it
always was -- an unrecognised routing value must never be guessed at -- and it is
a statement about the FILE, never about whether a customer is owed work.
"""

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


def policy_skip_reason(queue: Any, projects_root: Any = None) -> str | None:
    """★ Always None for a well-formed queue. ★ Raises ValueError on a malformed one.

    ``projects_root`` is accepted and ignored. It is kept so the call sites and the
    CLI signature do not have to change in the same edit that removes the
    dependency; nothing in this module reads a project ledger any more.
    """
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
        if queue_class not in BLOCKING_QUEUE_CLASSES and queue_class not in LOWER_PRIORITY_QUEUE_CLASSES:
            raise ValueError(f"unknown queue_class: {queue_class}")
    # ★ No paid item, in any class, in any state, closes the apply lane. ★
    return None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (1, 2):
        print("usage: b2_queue_gate.py QUEUE.json [PROJECTS_ROOT]", file=sys.stderr)
        return 2
    projects_root = Path(args[1]).expanduser() if len(args) == 2 else Path("~/gig/projects").expanduser()
    try:
        queue = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        reason = policy_skip_reason(queue, projects_root=projects_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"B2 queue gate unreadable: {exc}", file=sys.stderr)
        return 2
    if reason is None:
        return 1
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
