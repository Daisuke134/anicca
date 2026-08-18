#!/usr/bin/env python3
"""Refuse to say the same thing twice to a buyer who said nothing new.

kiki_1115, 2026-08-06: a full proposal went out at 11:46 and a near-identical one at
13:01. Between them the buyer wrote only 「宜しくお願い致します。」 -- no new request. The
existing guard compares outgoing_hash exactly and the two bodies are not byte-identical
(measured 0.741), so both shipped. The buyer went silent and the thread joined the 24 of
30 nobody will touch again.

Deterministic by construction: a judgement about whether to spend a model call must not
itself cost one, and a suppression rule that varies run to run cannot be audited.
"""
from __future__ import annotations

import difflib
from typing import Any


# Measured, not guessed. The pair that actually shipped scores 0.741; an unrelated job
# scores 0.13 and a follow-up that builds on the previous message scores 0.079. The two
# clusters are far apart, so 0.60 has margin on both sides. An earlier draft said 0.85,
# which would have let the real duplicate through.
NEAR_DUPLICATE_RATIO = 0.60


def similarity(left: Any, right: Any) -> float:
    """How alike two bodies read, ignoring surrounding whitespace."""
    a = str(left or "").strip()
    b = str(right or "").strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def is_near_duplicate(outgoing_body: Any, seller_messages: Any) -> bool:
    """Would sending this repeat what we last said in this thread?

    Only our own most recent message is compared. Comparing against the whole history
    makes suppression run away -- in a long thread almost anything resembles something
    said earlier -- and the failure being prevented is specifically saying the same thing
    twice in a row.
    """
    if not isinstance(seller_messages, (list, tuple)) or not seller_messages:
        return False
    last = seller_messages[-1]
    if isinstance(last, dict):
        last = last.get("body") or last.get("text")
    return similarity(outgoing_body, last) >= NEAR_DUPLICATE_RATIO
