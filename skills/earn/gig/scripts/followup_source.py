#!/usr/bin/env python3
"""Build follow-up candidate rows from what a pass already collects.

The supply is the inbox snapshot the reply detector writes every pass. In the last one it
held 30 inquiries, 25 of them with our own message newest -- buyers who answered once and
then stopped. Those 25 are the pipeline this whole lane exists for.

Two things the snapshot does not contain, both of which change how the rest must behave:

**Knowing when we spoke took three sources.** ``buyer_sent_at`` is only populated when the
buyer spoke last, so for all 25 of these it is absent -- which is why the collector now
also records ``seller_sent_at``. Preference runs: ``reply-transcripts.jsonl`` (our own
record of the send), then ``seller_sent_at`` (read off the thread), then ``buyer_sent_at``
(an over-estimate, since our reply came after it, which sends follow-ups early). Every row
names which one it used, because a number whose provenance is invisible gets trusted more
than it deserves.

**It has no message text.** So ``stop_signal`` cannot run here for most threads: a buyer
who wrote 「他の方探して下さい。」 looks identical to one who is still thinking. That is not
a reason to skip the check -- it is the reason the check has to run again at send time,
against the live thread the browser reads before composing. Selection here is a shortlist,
never a permission.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

# We spoke last and nobody answered. The only shape a follow-up can have.
SELLER = "seller"


def _epoch(value: Any) -> int | None:
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def transcript_send_times(path: Any) -> dict[str, int]:
    """The newest moment we actually sent something, per thread.

    Never raises: a follow-up lane that dies because a log line is malformed is worse than
    one that falls back to the snapshot's coarser timestamp.
    """
    times: dict[str, int] = {}
    if not path or not os.path.exists(str(path)):
        return times
    try:
        with open(str(path), encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row, dict):
                    continue
                thread = str(row.get("talkroom_id") or "")
                sent_at = _epoch(row.get("sent_at"))
                if not thread or sent_at is None:
                    continue
                if sent_at > times.get(thread, 0):
                    times[thread] = sent_at
    except OSError:
        return times
    return times


def candidate_rows(
    snapshot: Any,
    *,
    followups_sent: Any = None,
    send_times: Any = None,
    now: Any = None,
) -> list[dict[str, Any]]:
    """Shortlist rows for ``followup_candidates.select``.

    Paid threads are excluded here rather than filtered later: a buyer who has already
    bought is in a delivery conversation, and a sales follow-up dropped into it reads as
    the loop having lost track of who it is talking to.
    """
    if not isinstance(snapshot, dict):
        return []
    sent_counts = followups_sent if isinstance(followups_sent, dict) else {}
    times = send_times if isinstance(send_times, dict) else {}
    paid = {
        str(order.get("talkroom_id"))
        for order in snapshot.get("orders") or []
        if isinstance(order, dict) and order.get("talkroom_id") is not None
    }
    inquiries = snapshot.get("inquiries") or snapshot.get("b1_inquiries") or []
    rows: list[dict[str, Any]] = []
    for row in inquiries:
        if not isinstance(row, dict):
            continue
        if row.get("last_message_side") != SELLER:
            continue
        thread = str(row.get("talkroom_id") or "")
        if not thread or thread in paid or row.get("contracted") is True:
            continue
        measured = times.get(thread)
        collected = _epoch(row.get("seller_sent_at"))
        approximate = _epoch(row.get("buyer_sent_at"))
        sent_at = measured
        source = "transcript"
        if sent_at is None:
            # The collector reads this off the thread itself, so it is exact for every
            # thread rather than only the ones answered since transcripts were wired.
            sent_at, source = collected, "seller_sent_at"
        if sent_at is None:
            sent_at, source = approximate, "buyer_sent_at"
        if sent_at is None:
            # No clock at all: this thread cannot be contacted, because contacting on an
            # assumed silence is the one mistake that cannot be taken back. It is still
            # emitted, with the clock left None so exclusion_reason returns no_send_time.
            # Dropping it here instead would have made the pass report "considered 0"
            # while 25 real threads went unexamined -- a filter with no timestamps and a
            # genuinely empty inbox would have looked identical.
            source = "unknown"
        rows.append({
            "thread_id": thread,
            "talkroom_id": thread,
            "talkroom_url": row.get("talkroom_url"),
            "title": row.get("title"),
            "last_seller_sent_at": sent_at,
            "sent_at_source": source,
            # Carried explicitly, not left for a later stage to recompute. Selection reads
            # last_seller_sent_at, but the queue item and therefore the prompt read this
            # field -- and when it was absent the first real run drafted three follow-ups
            # that each told the buyer they had been silent for 0 days.
            "silent_days": (
                (int(now) - float(sent_at)) / 86400.0
                if sent_at is not None and now is not None
                else None
            ),
            "followups_sent": int(sent_counts.get(thread, 0) or 0),
            "outcome": "silent",
            # Absent on purpose: the snapshot carries no message text, so stop_signal has
            # nothing to read until the browser opens the thread.
            "conversation": None,
        })
    return rows
