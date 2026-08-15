#!/usr/bin/env python3
"""Silence as a row that ages, not as an absence of rows — spec §0.1.6 (P1a-4).

Through 24 consecutive hourly passes on 2026-08-04 the loop wrote `queue_selected` and
nothing else while a paying customer waited. Every log was clean, because "did nothing"
produces no record. This module inverts that: a waiting buyer becomes a row, the row gets
older every pass, and nothing except an action with a readback removes it.

What is deliberately not a close condition: `observed`, `no_work_required`,
`not_my_lane`, `observed_no_action`. Each of those was a true statement the loop made
while the customer waited. A statement about our own attention is not evidence that the
buyer heard from us.

An action alone is also not enough. The send may have failed, and on 2026-08-05 we
measured a notifier that recorded "sent" on an HTTP 502 body. Only a readback showing the
message is posted closes the row.

If the lane cannot act, it must say why in a form a machine can read: a code from a closed
enum plus the concrete blocker. An untyped silent skip is the original bug, so it is not
representable here. The refusal does not close the liability — it explains why it is still
open, which is what makes `awaiting_human_authority` firing 24 times legible as a defect
rather than as a legitimate wait.

Storage is an append-only JSONL event log, replayed to derive state. State is never
rewritten in place, so the history of a silence survives whatever the loop believes today.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

# What ends a silence. Anything else is not a close condition.
#
# The first four came from ideation about moves the lane initiates, and they are the ones
# `compose_reply` can render from an artifact. Wiring the real evidence revealed that the two
# most common ways a silence actually ends were missing from that list: we answered the
# buyer's question (`mode: "answer"` in paid-queue-evidence.json), or we delivered the work.
# Leaving them out would have marked a genuinely answered customer as waiting forever — the
# same lie as the original bug, pointing the other way.
#
# Widening this set does not readmit the excuses. `observed`, `no_work_required`,
# `not_my_lane` and `observed_no_action` remain outside it, because each was a true statement
# about our own attention made while the customer waited.
CLOSING_ACTIONS: frozenset[str] = frozenset(
    {
        "ask_buyer",
        "request_extension",
        "cancel_request",
        "end_subscription",
        "answer",
        "formal_delivery",
    }
)

# A refusal must be one of these. The enum is closed on purpose: a free-text reason is
# indistinguishable from a shrug, and cannot be mined later for structural deadlocks.
REFUSAL_CODES: frozenset[str] = frozenset(
    {
        "no_artifact_yet",
        "awaiting_human_authority",
        "buyer_message_unparsed",
        "quota_exhausted",
        # Added 2026-08-05. paid_work_validation_failed fired 44 times; running the validator
        # on the real ledger gives one reason — artifact_version_not_newer_than_project_state.
        # The project holds one artifact, v12, and the manifest re-declares v12: the work was
        # delivered by hand the day before and there is nothing new to build, while the pass
        # architecture insists PAID_WORK produce a newer version and dies when it cannot.
        #
        # The validator is right; weakening it would let the same artifact be re-delivered as
        # new. What was missing is a way for the lane to say "there is nothing to build here"
        # without that becoming a way to say nothing — this is a refusal, so the liability
        # stays open and the conversation still owes the buyer an answer.
        "no_new_work_required",
    }
)


class NotACloseCondition(Exception):
    """Raised when something that is not an evidenced action tries to close a liability."""


class UntypedRefusal(Exception):
    """Raised when a refusal has no code from the enum, or names no concrete blocker."""


def _append(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _events(path: Path) -> Iterable[dict[str, Any]]:
    if not Path(path).is_file():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # A corrupt line must not hide the liabilities around it. On 2026-08-04 a single
            # broken row in lessons.jsonl killed the whole verifier every hour.
            continue
    return rows


def _state(path: Path) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for event in _events(path):
        key = event.get("liability_key")
        if not key:
            continue
        kind = event.get("event")
        if kind == "observed":
            row = state.get(key)
            if row is None:
                state[key] = {
                    "liability_key": key,
                    "talkroom_id": event.get("talkroom_id"),
                    "title": event.get("title"),
                    "order_value_jpy": event.get("order_value_jpy"),
                    "opened_at_pass": event.get("pass_id"),
                    "passes": [event.get("pass_id")],
                    "closed": False,
                    "last_refusal": None,
                    "dispositions": {},
                }
            elif not row["closed"] and event.get("pass_id") not in row["passes"]:
                row["passes"].append(event.get("pass_id"))
        elif kind == "closed" and key in state:
            state[key]["closed"] = True
            state[key]["dispositions"][event.get("pass_id")] = "closed"
        elif kind == "refused" and key in state:
            state[key]["last_refusal"] = {
                "code": event.get("code"),
                "blocker_id": event.get("blocker_id"),
                "pass_id": event.get("pass_id"),
            }
            state[key]["dispositions"][event.get("pass_id")] = "refused"
    return state


def observe(path: Path, rooms: list[dict[str, Any]], *, pass_id: str) -> None:
    """Record this pass's sighting of every room that has a buyer waiting.

    Rooms reported as not open are not recorded, so they neither open nor age a liability.
    They also do not close one: only an evidenced action does that.
    """
    path = Path(path)
    state = _state(path)
    for room in rooms:
        if not room.get("liability_open"):
            continue
        key = room.get("liability_key")
        if not key or state.get(key, {}).get("closed"):
            continue
        _append(
            path,
            {
                "event": "observed",
                "liability_key": key,
                "talkroom_id": room.get("talkroom_id"),
                "title": room.get("title"),
                "order_value_jpy": room.get("order_value_jpy"),
                "pass_id": pass_id,
            },
        )


def close(
    path: Path,
    liability_key: str,
    *,
    action: str,
    outbound_readback: dict[str, Any] | None,
    pass_id: str,
) -> None:
    """Close a liability, but only on an action whose readback shows we posted."""
    if action not in CLOSING_ACTIONS:
        raise NotACloseCondition(
            f"{action!r} is not one of {sorted(CLOSING_ACTIONS)} — a statement about our own "
            "attention is not evidence the buyer heard from us"
        )
    if not outbound_readback:
        raise NotACloseCondition(
            f"{action!r} has no outbound readback — the send may have failed, and only the "
            "readback proves the buyer can see it"
        )
    _append(
        Path(path),
        {
            "event": "closed",
            "liability_key": liability_key,
            "action": action,
            "outbound_readback": outbound_readback,
            "pass_id": pass_id,
        },
    )


def refuse(path: Path, liability_key: str, *, code: str, blocker_id: str, pass_id: str) -> None:
    """Record why this pass could not act. Does not close the liability."""
    if code not in REFUSAL_CODES:
        raise UntypedRefusal(
            f"{code!r} is not one of {sorted(REFUSAL_CODES)} — an untyped skip is the bug"
        )
    if not (blocker_id or "").strip():
        raise UntypedRefusal(f"refusal {code!r} names no concrete blocker")
    _append(
        Path(path),
        {
            "event": "refused",
            "liability_key": liability_key,
            "code": code,
            "blocker_id": blocker_id,
            "pass_id": pass_id,
        },
    )


def open_liabilities(path: Path) -> list[dict[str, Any]]:
    """Every liability still open, oldest first, with how many passes it has survived."""
    rows = []
    for row in _state(Path(path)).values():
        if row["closed"]:
            continue
        rows.append(
            {
                "liability_key": row["liability_key"],
                "talkroom_id": row["talkroom_id"],
                "title": row["title"],
                "order_value_jpy": row["order_value_jpy"],
                "age_passes": len(row["passes"]),
                "last_refusal": row["last_refusal"],
            }
        )
    rows.sort(key=lambda r: -r["age_passes"])
    return rows


def undisposed(path: Path, *, pass_id: str) -> list[str]:
    """Open liabilities this pass neither closed nor refused.

    Step 5 turns a non-empty result into a non-zero exit. A pass that ends leaving a paying
    customer unanswered and unexplained is the failure this whole module exists to name.
    """
    return [
        row["liability_key"]
        for row in _state(Path(path)).values()
        if not row["closed"] and pass_id not in row["dispositions"]
    ]
