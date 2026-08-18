#!/usr/bin/env python3
"""How many times in a row the question to this buyer failed to leave.

``~/gig/ask-buyer.jsonl`` answers "has this buyer been asked", and it answers it only
after the browser verified the send -- that is the whole reason it exists.  It is
therefore silent about the other outcome.  A send that fails writes nothing there, and
nothing anywhere else either, so every pass rediscovers the same broken send from
scratch: compose, fail, forget.  Order 91000001 did exactly that, and would have done it
hourly until Coconala cancelled the order at 2026-08-09 23:00.

This is the missing half.  It is a separate ledger rather than a second row shape inside
ask-buyer.jsonl on purpose: ``ask_buyer_pass._asked_keys`` treats *any* row carrying a
blocker_key as "already asked", so a failure row written there would silence the buyer
permanently -- the precise bug this module exists to bound.

Shape copied from cbc29d23 (the reply lane's dead-letter), because the situation is the
same one:

* counted **consecutive**, not lifetime.  Three failures across a week is a flaky
  browser; three in a row is a defect that will not fix itself.
* keyed per (talkroom, blocker_key, failure class).  A different error is a different
  story and starts its own count; the blocker_key is what stays constant while the buyer
  has not replied, so a recomposed question does not reset the bound.
* reset by any success.  One verified send clears the history for that target.
* durable, in its own file, so it survives the pass boundary the counter is meant to
  outlive.
* escalated exactly once, on the transition that reaches the limit.  A pass that already
  knows it is over the bound must be quiet, or the escalation becomes the new hourly
  noise.

Nothing observed by a browser is stored.  ``reason`` is matched against this repository's
own failure vocabulary and normalised away when it does not match, for the same reason
delivery_attempt.py does it: an append-only row must not become a place where remote text
lands.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

_REASON = re.compile(r"[a-z0-9_]{1,64}")
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_KEY = re.compile(r"[0-9a-f]{16,64}")

UNKNOWN_REASON = "unknown_send_failure"
OUTCOME_FAILED = "failed"
OUTCOME_SENT = "sent"

# Hourly passes and a platform that cancels an unanswered order at the 48-hour mark: three
# consecutive hours of a send that will not leave is already the longest silence this order
# can afford. Same number, and the same reasoning, as delivery_attempt.DEFAULT_MAX_ATTEMPTS,
# which bounds the other way of putting something in front of this same buyer.
DEFAULT_MAX_ATTEMPTS = 3


def max_attempts() -> int:
    raw = str(os.environ.get("GIG_ASK_BUYER_MAX_SEND_ATTEMPTS") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS
    return value if value > 0 else DEFAULT_MAX_ATTEMPTS


def normalize_reason(value: Any) -> str:
    text = str(value or "").strip()
    return text if _REASON.fullmatch(text) else UNKNOWN_REASON


def _identifier(value: Any) -> str:
    text = str(value or "").strip()
    return text if _ID.fullmatch(text) else ""


def _blocker_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _KEY.fullmatch(text) else ""


def read_rows(path: str | Path | None) -> tuple[list[dict[str, Any]], bool]:
    """Every readable row, and whether the ledger was there at all.

    ★ A count of zero says how it was counted. ★ "No ledger yet" and "a ledger that says
    this target has never failed" are the same integer and different facts, so the caller
    is told which one it got instead of having to guess.
    """
    rows: list[dict[str, Any]] = []
    if not path:
        return rows, False
    try:
        lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows, False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows, True


def consecutive_failures(
    rows: list[dict[str, Any]], talkroom_id: str, blocker_key: str
) -> tuple[int, str]:
    """Trailing failures of one class for one target, newest first, stopped by a success."""
    talkroom = _identifier(talkroom_id)
    key = _blocker_key(blocker_key)
    if not talkroom or not key:
        return 0, ""
    count = 0
    failure_class = ""
    for row in reversed(rows):
        if _identifier(row.get("talkroom_id")) != talkroom:
            continue
        if _blocker_key(row.get("blocker_key")) != key:
            continue
        outcome = str(row.get("outcome") or "")
        if outcome == OUTCOME_SENT:
            break
        if outcome != OUTCOME_FAILED:
            continue
        reason = normalize_reason(row.get("reason"))
        if failure_class and reason != failure_class:
            break
        failure_class = reason
        count += 1
    return count, failure_class


def verdict(
    path: str | Path | None, talkroom_id: str, blocker_key: str
) -> dict[str, Any]:
    rows, present = read_rows(path)
    count, failure_class = consecutive_failures(rows, talkroom_id, blocker_key)
    limit = max_attempts()
    return {
        "talkroom_id": _identifier(talkroom_id),
        "blocker_key": _blocker_key(blocker_key),
        "consecutive_failures": count,
        "failure_class": failure_class,
        "limit": limit,
        "exhausted": count >= limit,
        "ledger_present": present,
        "rows_scanned": len(rows),
    }


def append(path: str | Path, row: dict[str, Any]) -> None:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def record(
    path: str | Path,
    *,
    talkroom_id: str,
    blocker_key: str,
    outcome: str,
    reason: Any = None,
    pass_id: Any = None,
) -> dict[str, Any]:
    """Append one outcome and say what it means for the bound.

    ``escalate`` is true only on the transition that reaches the limit.  Later passes read
    ``exhausted`` from ``verdict`` and stay quiet; the alternative is an hourly durable
    failure about a send nobody is attempting any more.
    """
    talkroom = _identifier(talkroom_id)
    key = _blocker_key(blocker_key)
    if not talkroom or not key:
        return {"ok": False, "error": "unusable_target"}
    outcome = OUTCOME_SENT if str(outcome) == OUTCOME_SENT else OUTCOME_FAILED
    before = verdict(path, talkroom, key)
    entry = {
        "ts": int(time.time()),
        "talkroom_id": talkroom,
        "blocker_key": key,
        "outcome": outcome,
        "reason": normalize_reason(reason) if outcome == OUTCOME_FAILED else "",
        "pass_id": _identifier(pass_id),
    }
    append(path, entry)
    after = verdict(path, talkroom, key)
    after["ok"] = True
    after["outcome"] = outcome
    after["escalate"] = (
        outcome == OUTCOME_FAILED
        and after["consecutive_failures"] >= after["limit"]
        and before["consecutive_failures"] < after["limit"]
    )
    return after


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--ledger", required=True)
    check.add_argument("--talkroom-id", required=True)
    check.add_argument("--blocker-key", required=True)

    write = sub.add_parser("record")
    write.add_argument("--ledger", required=True)
    write.add_argument("--talkroom-id", required=True)
    write.add_argument("--blocker-key", required=True)
    write.add_argument("--outcome", required=True, choices=[OUTCOME_FAILED, OUTCOME_SENT])
    write.add_argument("--reason", default="")
    write.add_argument("--pass-id", default="")

    args = parser.parse_args(argv)
    if args.command == "check":
        payload = verdict(args.ledger, args.talkroom_id, args.blocker_key)
    else:
        payload = record(
            args.ledger,
            talkroom_id=args.talkroom_id,
            blocker_key=args.blocker_key,
            outcome=args.outcome,
            reason=args.reason,
            pass_id=args.pass_id,
        )
    json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
