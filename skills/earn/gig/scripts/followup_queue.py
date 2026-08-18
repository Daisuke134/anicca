#!/usr/bin/env python3
"""Turn silent threads into queue items the existing reply machinery already knows how to send.

``reply_queue.build_queue`` only ever emits a thread whose newest message came from the
buyer. A follow-up is the opposite case by definition -- we spoke last and nobody answered
-- so no follow-up can enter through that door. This is the second door. Everything past it
is unchanged: the same outbox fencing, the same near-duplicate guard, the same idempotent
body hash, the same executor.

The one thing that must be right here is ``event_key``. The outbox folds items that share
one, so a key built from the thread alone would make follow-up #2 a duplicate of #1 and no
second message would ever go out. The count of previous follow-ups is therefore part of the
identity: 3 attempts, 3 distinct keys, and a re-run of the same pass still collapses into
one send.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

PLATFORM = "coconala"
# Below P1: a buyer waiting for an answer to a question they just asked outranks a buyer
# who has been quiet for a week.
PRIORITY = "P2"
EVENT_TYPE = "followup"
NEXT_ACTION = "followup"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def event_key(talkroom_id: Any, followups_sent: Any) -> str:
    """Identity of one follow-up attempt on one thread.

    Shaped as the outbox's existing message grammar --
    ``coconala:message:v1:<thread>:<message>`` -- rather than a new one. The validator
    that enforces it also binds the key to its thread, which is what stops a queue from
    writing into someone else's conversation; inventing a grammar to fit this lane would
    mean loosening that check for a message no more trustworthy than any other. Measured:
    the first shape tried here was rejected with ValueError("invalid event_key").

    The attempt number is part of the identity so the outbox does not fold attempt 2 into
    attempt 1, and the clock is excluded so re-running a pass does not send twice.
    """
    sent = followups_sent if isinstance(followups_sent, int) and followups_sent >= 0 else 0
    return f"{PLATFORM}:message:v1:{talkroom_id}:followup-{sent}"


def _talkroom_url(row: dict[str, Any], talkroom_id: str) -> str:
    url = row.get("talkroom_url")
    if isinstance(url, str) and url.startswith("https://coconala.com/"):
        return url
    return f"https://coconala.com/talkrooms/{talkroom_id}"


def build(candidates: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Queue items for the threads selected by ``followup_candidates.select``.

    A candidate without a thread id is dropped rather than guessed at: the failure mode of
    a guess here is a message delivered to the wrong buyer, which cannot be taken back.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    items: list[dict[str, Any]] = []
    for row in candidates or []:
        if not isinstance(row, dict):
            continue
        talkroom_id = row.get("talkroom_id") or row.get("thread_id")
        if talkroom_id in (None, ""):
            continue
        talkroom_id = str(talkroom_id)
        sent = row.get("followups_sent")
        sent = sent if isinstance(sent, int) and sent >= 0 else 0
        key = event_key(talkroom_id, sent)
        items.append({
            "platform": PLATFORM,
            "priority": PRIORITY,
            "event_type": EVENT_TYPE,
            "event_key": key,
            "coordination_key": f"{PLATFORM}:{talkroom_id}",
            "covered_event_keys": [key],
            "talkroom_id": talkroom_id,
            "talkroom_url": _talkroom_url(row, talkroom_id),
            "origin_at": _iso(current),
            "detected_at": _iso(current),
            "followups_sent": sent,
            "silent_days": row.get("silent_days"),
            "next_action": NEXT_ACTION,
        })
    # One item per thread. Two candidates for the same talkroom would otherwise queue two
    # messages to the same person in one pass.
    by_thread: dict[str, dict[str, Any]] = {}
    for item in items:
        by_thread.setdefault(item["coordination_key"], item)
    queued = sorted(by_thread.values(), key=lambda value: value["event_key"])
    return {
        "status": "ready" if queued else "queue_empty",
        "errors": [],
        "items": queued,
    }
