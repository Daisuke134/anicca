#!/usr/bin/env python3
"""Turn observed talkroom state into permission to close a liability — §0.1.6 (P1a-9a).

`coconala_reply_browser.thread_state()` already derives the right primitive from live DOM:
when the seller last spoke, when the buyer last spoke, and a fingerprint over every message
in the room. Nothing consumed it for paid rooms, which is why `close()` had no reachable
input and the disposer could only ever refuse — and why my first replay over real history
produced 77 refusals and read them as a measurement instead of as an empty channel.

Closing requires both halves, and neither alone is enough.

An intent without a landing is "we tried". The send may have been rejected; this loop
recorded `submit_rejected_sending_unavailable` earlier today. Treating an attempt as an
answer is how a customer waits while the ledger says they were served.

A landing without an intent is someone else's message, or our own from an earlier pass.
Claiming it would close a liability that nothing answered.

Timestamps decide rather than `last_sender`, because the buyer can speak again after us
within a single observation, and the ordering is what they actually experience.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def _closing_actions() -> frozenset[str]:
    spec = importlib.util.spec_from_file_location(
        "silence_liability", _HERE / "silence_liability.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CLOSING_ACTIONS


def _instant(value: Any) -> datetime | None:
    """Parse an ISO timestamp, or return None rather than guessing.

    A room whose clock we cannot read is a room we cannot make claims about. Guessing here
    would let a malformed timestamp close a real customer's liability.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def decide_readbacks(
    open_liabilities: list[dict[str, Any]],
    *,
    thread_states: dict[str, dict[str, Any]],
    intents: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Return the readbacks the disposer may close on, keyed by liability_key.

    Absence is the default. Every path that cannot prove the buyer heard from us after they
    spoke simply omits the key, and the liability stays open with a typed refusal instead.
    """
    closing = _closing_actions()
    readbacks: dict[str, dict[str, Any]] = {}

    for row in open_liabilities:
        key = row.get("liability_key")
        action = intents.get(key)
        if action not in closing:
            continue

        state = thread_states.get(str(row.get("talkroom_id")))
        if not state:
            continue

        # Two rooms, two kinds of proof. Pre-purchase DMs carry timestamps, so they are
        # compared as clocks. Paid talkrooms do not — the page has no times at all — so
        # `paid_thread_state` reduces DOM order to the same question and answers it as
        # `seller_after_buyer`. Both mean "our message sits below theirs".
        if "seller_after_buyer" in state:
            if state.get("seller_after_buyer") is not True:
                continue
        else:
            spoke_at = _instant(state.get("seller_sent_at"))
            buyer_at = _instant(state.get("latest_buyer_sent_at"))
            if spoke_at is None or buyer_at is None:
                continue
            if spoke_at <= buyer_at:
                continue

        readbacks[key] = {
            "action": action,
            "posted_at": state.get("seller_sent_at"),
            "buyer_spoke_at": state.get("latest_buyer_sent_at"),
            "last_sender": state.get("last_sender"),
            "talkroom_id": state.get("talkroom_id"),
            "url": state.get("url"),
            # The fingerprint covers every message in the room, so the ledger records which
            # exact conversation state was observed when the liability was closed.
            "fingerprint": state.get("fingerprint"),
        }

    return readbacks
