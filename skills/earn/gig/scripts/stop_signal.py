#!/usr/bin/env python3
"""Decide whether a buyer has told us to stop.

A follow-up sent after a refusal is the thing the platform's 迷惑行為 clause exists to
punish, and it is also simply rude. This is the last gate before a thread is contacted
again, and it runs on the buyer's own words.

Grounded in one measured refusal, quoted exactly (~/gig/reply-transcripts.jsonl):

    まだ、最終的な話までしてませんが。 それで先に請求画面って？ 他の方探して下さい。

One sample is thin, and the lexicon below is wider than one sample can justify -- so it is
built to fail in the harmless direction. A phrase is listed only when it cannot plausibly
mean anything but "no". Everything else is left out, because the cost of the two errors is
not symmetric: a missed refusal sends one unwanted message, while a false refusal silently
deletes a live buyer from the pipeline and nothing ever reports it.

That asymmetry is why 検討します is deliberately **not** a stop signal. "I'll think about
it" is the exact state a follow-up exists to serve; treating it as a refusal would remove
the majority of the pipeline. 24 of 25 replied threads are silent, and silence after
検討します is the normal shape of a deal that is still alive.
"""
from __future__ import annotations

import re
from typing import Any

# Each entry must be unambiguous on its own. 「今回は」 is absent: it opens both
# 「今回は見送ります」 and 「今回はお願いしたいです」.
_STOP = (
    # The measured one: the buyer sent us to a competitor.
    ("other_seller", re.compile(r"(他の方|他社|別の方|他のかた).{0,6}(探|依頼|お願い|決め|発注)")),
    ("declined", re.compile(r"(お断り|辞退|見送(り|ら|ります)|お見送り)")),
    # Before no_thanks: 「連絡は不要です」 matches both, and the more specific reason is the
    # one worth reporting when a thread leaves the pipeline.
    ("stop_contact", re.compile(r"(連絡(は)?(不要|しないで|やめて)|返信(は)?不要|送らないで)")),
    ("no_thanks", re.compile(r"(結構です|不要です|必要ありません|必要ないです|遠慮(し|させて))")),
    ("not_interested", re.compile(r"興味(は)?(ありません|ないです|無いです)")),
    ("cancelled", re.compile(r"(キャンセル|取り下げ|中止(し|に)|募集(を)?(終了|締め切))")),
    ("already_solved", re.compile(r"(解決(しま|済)|自分で(やり|対応)|社内で(対応|やる))")),
)

# Checked before the stop list. A buyer who is still deciding must survive this gate even
# when the same sentence carries a word that looks like a refusal.
_STILL_OPEN = re.compile(
    r"(検討(します|中|させて)|考えて(みます|おきます)|相談(して|します)|"
    r"少し(お)?時間|後ほど|改めて(ご)?連絡)"
)


def stop_reason(text: Any) -> str | None:
    """Why this message ends the conversation, or None to keep it open.

    Returns the reason rather than a bool so a thread dropped from the pipeline can say
    which words dropped it -- an exclusion nobody can explain is indistinguishable from
    a bug that eats buyers.
    """
    if not isinstance(text, str):
        return None
    body = text.strip()
    if not body:
        return None
    for reason, pattern in _STOP:
        if not pattern.search(body):
            continue
        # A refusal and a "still thinking" in one message is a person being polite about
        # a maybe. Read the maybe: the reverse reading loses a buyer permanently.
        if _STILL_OPEN.search(body):
            return None
        return reason
    return None


def is_stopped(conversation: Any) -> bool:
    """True when the buyer has refused anywhere in this conversation.

    Scans every buyer turn, not only the newest. A refusal followed by our own two
    messages is still a refusal, and the newest turn in a dead thread is usually ours.
    """
    return bool(stopped_by(conversation))


def stopped_by(conversation: Any) -> dict[str, str] | None:
    """The buyer turn that ended it, with its reason -- or None."""
    turns = conversation
    if isinstance(conversation, dict):
        turns = conversation.get("messages") or conversation.get("turns") or []
    if not isinstance(turns, (list, tuple)):
        return None
    for turn in turns:
        if isinstance(turn, str):
            text, is_buyer = turn, True
        elif isinstance(turn, dict):
            sender = str(turn.get("sender") or turn.get("from") or "").lower()
            # Our own words never stop a thread: the loop quoting a refusal back, or
            # writing 「見送り」 about something else, would silently exclude the buyer.
            is_buyer = sender not in {"seller", "us", "self", "assistant"}
            text = turn.get("text") or turn.get("body") or ""
        else:
            continue
        if not is_buyer:
            continue
        reason = stop_reason(text)
        if reason:
            return {"reason": reason, "text": str(text).strip()[:200]}
    return None
