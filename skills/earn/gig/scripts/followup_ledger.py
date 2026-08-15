#!/usr/bin/env python3
"""Count how many times we have followed up, so the cap on it is real.

followup_candidates refuses a fourth message to any thread, but the count it reads was
hard-wired to zero. Wiring a sender before this ledger existed would have let one buyer
receive an unbounded stream -- exactly the 迷惑行為 the cap was chosen to avoid
(https://coconala-support.zendesk.com/hc/ja/articles/10003536321049). A limit nobody
counts against is not a limit.

Append-only, and undercounting is the dangerous direction: a lost row means we send again.
So recording reports failure rather than raising, and the caller decides.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def followups_sent(path: Path | str) -> dict[str, int]:
    """How many follow-ups each thread has already received.

    A corrupt line is skipped rather than fatal: one unreadable row must not erase the
    memory of every message we have sent to everyone else.
    """
    counts: dict[str, int] = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        thread_id = str(row.get("thread_id") or "").strip()
        if thread_id:
            counts[thread_id] = counts.get(thread_id, 0) + 1
    return counts


def record_followup(path: Path | str, *, thread_id: str, sent_at: int) -> bool:
    """Record that one follow-up went out. Returns whether it landed; never raises.

    0o600 because these are buyers' identities, matching the rest of the evidence tree.
    """
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            {"thread_id": str(thread_id), "sent_at": int(sent_at)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        descriptor = os.open(target, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except Exception:
        return False
