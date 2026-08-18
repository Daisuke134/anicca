#!/usr/bin/env python3
"""Choose which silent conversations deserve one more message.

26 threads sit with our own words last and next_action=observe, so nobody ever acts on
them. Some fell silent because of what we said -- kiki_1115 was promised the deliverable
free, with no reason to buy -- and they have been waiting since.

The numbers are not taste. Yesware's study of 10M threads
(https://www.yesware.com/blog/sales-follow-up-statistics/) finds the cadence that earns
replies is roughly six touches across three weeks, that "waiting more than four days
typically decreases reply", and that reply rates fall under 10% after the seventh.

Coconala forbids follow-ups to 不特定多数
(https://coconala-support.zendesk.com/hc/ja/articles/10003722830105). These threads are
not that -- the buyer opened every one -- but the spirit of the rule is why the cap here
is three rather than six, and why a pass sends a handful rather than a backlog.

Pure functions. Deciding who to contact must not itself cost a model call.
"""
from __future__ import annotations

from typing import Any

import os
import sys

# Loaded dynamically by reply_lane, which uses spec_from_file_location and does not
# put this directory on the path. Importing a sibling then fails with
# ModuleNotFoundError -- measured, not guessed. Running as a script happens to work
# because sys.path[0] is already here, and depending on that is depending on how the
# caller was launched.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stop_signal


# Below four days a follow-up measurably lowers the reply rate, so three is the earliest
# point at which sending helps rather than hurts.
MIN_SILENT_DAYS = 3.0
# Yesware's data allows six. Three, because an over-eager loop on Coconala is an account
# risk under 迷惑行為, not merely an ineffective one.
MAX_FOLLOWUPS_PER_THREAD = 3
# A backlog of 17 must not become 17 messages in one hour.
DEFAULT_PER_PASS_LIMIT = 3


def silent_days(row: Any, now: int) -> float | None:
    """Days since we last spoke, or None when we cannot know."""
    if not isinstance(row, dict):
        return None
    sent_at = row.get("last_seller_sent_at")
    if not isinstance(sent_at, (int, float)) or sent_at <= 0:
        return None
    return (int(now) - float(sent_at)) / 86400.0


def exclusion_reason(row: Any, *, now: int) -> str | None:
    """Why this thread is not contacted, or None when it should be.

    Every exclusion names itself. A thread that quietly leaves the pipeline is
    indistinguishable from a thread the code lost by accident, and the refusal check below
    runs on a lexicon measured against exactly one real refusal -- so its mistakes have to
    be visible in the report rather than assumed absent.
    """
    if not isinstance(row, dict):
        return "not_a_thread"
    days = silent_days(row, now)
    if days is None:
        return "no_send_time"
    if days < MIN_SILENT_DAYS:
        return "too_soon"
    if str(row.get("outcome") or "") == "won":
        return "already_won"
    sent = row.get("followups_sent")
    sent = int(sent) if isinstance(sent, int) else 0
    if sent >= MAX_FOLLOWUPS_PER_THREAD:
        return "followup_limit"
    # Last, and hardest: a buyer who said no. Sending after a refusal is the behaviour
    # 迷惑行為 exists to punish, so it outranks every reason to make contact.
    stopped = stop_signal.stopped_by(row.get("conversation") or row.get("messages"))
    if stopped:
        return "stopped:" + stopped["reason"]
    return None


def is_candidate(row: Any, *, now: int) -> bool:
    """Should this thread receive one more message?

    A thread with no recorded send time is never guessed at: contacting a buyer on an
    assumption is the one mistake that cannot be taken back.
    """
    return exclusion_reason(row, now=now) is None


def select(
    rows: Any, *, now: int, limit: int = DEFAULT_PER_PASS_LIMIT
) -> list[dict[str, Any]]:
    """The threads to contact this pass, longest silence first.

    Longest first because the buyer who has waited most is closest to being lost for good.
    """
    candidates = [row for row in (rows or []) if is_candidate(row, now=now)]
    candidates.sort(key=lambda row: silent_days(row, now) or 0.0, reverse=True)
    return candidates[: max(0, int(limit))]
