#!/usr/bin/env python3
"""Keep what we said to a buyer, next to what they said to us.

On 2026-08-06 two conversations explained the entire difference between revenue and
silence: one answered "可能です" and gated the work on purchase and closed; the other
promised to send the deliverable for free and the buyer went quiet. The loop could read
neither. connector_intents stores only outgoing_hash, reply-lane-result.json has no body,
and pre-purchase DMs were persisted nowhere -- so "learn from the conversations that won"
was not a hard problem, it was an impossible one.

Pure functions. The caller supplies everything; nothing here touches a browser or a queue.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _conversation(context: Any) -> list[dict[str, str]]:
    rows = context.get("conversation") if isinstance(context, dict) else None
    if not isinstance(rows, list):
        return []
    kept: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        side = str(row.get("side") or "")
        if side not in ("buyer", "seller"):
            continue
        # The rows this loop actually produces carry the message under "text"; measured
        # 2026-08-06 on a live b1-context, reading only "body" stored 27 rows whose every
        # body was empty and a buyer_last_said of "" -- a transcript proving a reply
        # happened while hiding everything worth learning from it. "body" stays accepted
        # so fixtures and any other caller keep working.
        text = row.get("text")
        if not isinstance(text, str) or not text:
            text = row.get("body")
        kept.append({"side": side, "body": str(text or "")})
    return kept


def transcript_row(
    *,
    talkroom_id: str,
    context: Any,
    outgoing_body: str,
    outgoing_hash: str,
    sent_at: int,
    status: str,
) -> dict[str, Any]:
    """One reply, with the exchange that produced it.

    ``outcome`` is deliberately None: at send time nobody knows whether this converted, and
    writing a guess would poison the dataset this exists to build. A later pass labels it.
    """
    conversation = _conversation(context)
    buyer_lines = [row["body"] for row in conversation if row["side"] == "buyer"]
    return {
        "talkroom_id": str(talkroom_id),
        "sent_at": int(sent_at),
        "status": str(status),
        "outgoing_body": str(outgoing_body),
        "outgoing_hash": str(outgoing_hash),
        "buyer_last_said": buyer_lines[-1] if buyer_lines else "",
        "conversation": conversation,
        "service_id": str(context.get("official_service_id"))
        if isinstance(context, dict) and str(context.get("official_service_id") or "").isdigit()
        else None,
        "outcome": None,
    }


def append_transcript(path: Path | str, row: dict[str, Any]) -> bool:
    """Append one row. Returns whether it landed; never raises.

    This runs on the send path. A recorder that threw would cost a real reply to a real
    buyer, and the observation must never outrank the revenue it observes -- so every
    failure is swallowed and reported as False.

    0o600 because these are buyers' own words, matching the permission the rest of the
    evidence tree already uses (application_parent.py:1041).
    """
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        descriptor = os.open(target, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except Exception:
        return False
