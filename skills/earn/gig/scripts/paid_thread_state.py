#!/usr/bin/env python3
"""Read a paid talkroom well enough to prove we answered — spec §0.1.6 (P1a-9b).

Paid rooms and pre-purchase DMs are different pages in different URL families:
`/talkrooms/<id>` versus `/mypage/direct_message/<id>`. `coconala_reply_browser.thread_state`
hard-requires the second and raises `unexpected_url` on the first, so none of the existing
readback machinery could ever look at a paying customer's room. That single mismatch is a
large part of why the paid lane had no way to close anything.

The paid extractor that does exist keeps only `side === 'seller'` and carries no timestamps,
so "did we speak after the buyer" was not answerable from it either. DOM order is
chronological, and that is enough: if the last message which is not a platform notice is
ours, our answer sits below theirs where they will see it. Ordering, not clocks.

System rows are excluded from that judgement on purpose. Coconala injects 納品されました and
検収 notices into the thread; letting one of those count as us speaking would close a
liability nobody answered — the exact class of false comfort this whole lane exists to end.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

_HUMAN_SIDES = ("buyer", "seller")


class NotAPaidTalkroom(Exception):
    """Raised when the observed page is not the paid talkroom we asked for.

    Reading room B and closing room A's liability would be the worst available bug here, so
    identity is checked before anything is derived from the DOM.
    """


def paid_thread_state(dom: dict[str, Any], talkroom_id: str) -> dict[str, Any]:
    """Derive the readback primitive for one paid talkroom."""
    url = str(dom.get("url") or "")
    path = urlparse(url).path.rstrip("/")
    expected = f"/talkrooms/{talkroom_id}"
    if path != expected:
        raise NotAPaidTalkroom(
            f"observed {path!r} but the liability is for {expected!r} — refusing to derive "
            "an answer from a room we did not open"
        )

    raw = dom.get("messages")
    messages = [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
    human = [row for row in messages if row.get("side") in _HUMAN_SIDES]

    last_sender = human[-1].get("side") if human else None
    buyer_present = any(row.get("side") == "buyer" for row in human)

    fingerprint = hashlib.sha256(
        json.dumps(
            [
                {
                    "side": row.get("side"),
                    "text": row.get("text"),
                    "attachments": row.get("attachments") or [],
                }
                for row in messages
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    return {
        "talkroom_id": talkroom_id,
        "url": url,
        "last_sender": last_sender,
        # True only when a buyer has spoken at all and our message is the one below theirs.
        # A room where we have talked into the void proves nothing about answering anyone.
        "seller_after_buyer": bool(last_sender == "seller" and buyer_present),
        "message_count": len(messages),
        "human_message_count": len(human),
        "fingerprint": fingerprint,
    }
