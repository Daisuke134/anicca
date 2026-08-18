#!/usr/bin/env python3
"""Choose an interview time from the owner's real calendar, with no human in it.

A4 (2026-07-30). The first design here was "send Dais the candidate slots and let
him pick".  That was rejected: the agent can read his calendar, so picking is the
agent's job.  The whole point of this loop is that nobody is waiting on a human --
including for scheduling.  So this module has exactly two outcomes, accept and
counter_propose, and no third one that routes a decision to a person.  Telegram
hears about it afterwards, as a report, never as a question.

Availability comes from `gog calendar events` (gog 0.17.0, Homebrew).  The flag is
--max, not --max-results; --max-results does not exist and silently fails the call.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


JST = timezone(timedelta(hours=9))
GOG = "gog"

ACCEPT = "accept"
COUNTER_PROPOSE = "counter_propose"
# The complete set. There is deliberately no human-escalation outcome.
DECISIONS: frozenset[str] = frozenset({ACCEPT, COUNTER_PROPOSE})

# The offered slots are the client's own grid, so padding them only manufactures
# conflicts that are not real -- taking 19:00 after a meeting that ends at 19:00 is
# ordinary. The knob stays for callers who want breathing room; the default does
# not spend the client's availability on our own comfort.
DEFAULT_BUFFER_MINUTES = 0
# Enough notice to actually join a call, not enough to throw away today.
DEFAULT_MIN_LEAD_MINUTES = 15
DEFAULT_COUNTER_PROPOSALS = 3
DEFAULT_COUNTER_LOOKAHEAD_DAYS = 10

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed


def _event_bounds(event: dict[str, Any]) -> tuple[datetime, datetime] | None:
    """Return an event's busy interval, or None when it does not consume time."""
    if not isinstance(event, dict):
        return None
    if str(event.get("status") or "").lower() == "cancelled":
        return None
    if str(event.get("transparency") or "").lower() == "transparent":
        return None
    start = event.get("start") or {}
    end = event.get("end") or {}
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    start_value = start.get("dateTime") or start.get("date")
    end_value = end.get("dateTime") or end.get("date")
    if not start_value or not end_value:
        return None
    try:
        first = _parse(start_value)
        last = _parse(end_value)
    except ValueError:
        return None
    if _ISO_DATE.fullmatch(str(start_value)):
        # An all-day entry blocks the whole local day, not midnight-to-midnight UTC.
        first = first.replace(tzinfo=JST)
        last = last.replace(tzinfo=JST)
    if last <= first:
        return None
    return first, last


def busy_intervals(events: Iterable[dict[str, Any]]) -> list[tuple[datetime, datetime]]:
    """Collapse calendar events into sorted, merged busy intervals."""
    bounds = [interval for interval in map(_event_bounds, events or []) if interval]
    bounds.sort(key=lambda interval: interval[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in bounds:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _free(
    start: datetime,
    end: datetime,
    busy: list[tuple[datetime, datetime]],
    *,
    buffer_minutes: int,
) -> bool:
    padding = timedelta(minutes=buffer_minutes)
    for busy_start, busy_end in busy:
        if start < busy_end + padding and busy_start - padding < end:
            return False
    return True


def candidate_slots(offer: dict[str, Any]) -> list[dict[str, str]]:
    """Split each offered window into the fixed slots the platform's modal shows.

    Verified live: an offered 18:00~20:00 window with 面談時間 30分 renders as
    18:00~18:30 / 18:30~19:00 / 19:00~19:30 / 19:30~20:00 radio options.
    """
    duration = int(offer["duration_minutes"])
    if duration <= 0:
        raise ValueError("invalid interview duration")
    step = timedelta(minutes=duration)
    slots: list[dict[str, str]] = []
    for window in offer.get("windows", []):
        start = _parse(window["start"])
        window_end = _parse(window["end"])
        while start + step <= window_end:
            slots.append({
                "start": start.isoformat(),
                "end": (start + step).isoformat(),
            })
            start += step
    return slots


def _band(offer: dict[str, Any]) -> tuple[int, int]:
    """The time-of-day band the client themselves asked for, in local minutes."""
    starts, ends = [], []
    for window in offer.get("windows", []):
        first = _parse(window["start"]).astimezone(JST)
        last = _parse(window["end"]).astimezone(JST)
        starts.append(first.hour * 60 + first.minute)
        ends.append(last.hour * 60 + last.minute)
    if not starts:
        return (9 * 60, 18 * 60)
    return (min(starts), max(ends))


def counter_proposals(
    *,
    offer: dict[str, Any],
    busy: list[tuple[datetime, datetime]],
    now: datetime,
    limit: int = DEFAULT_COUNTER_PROPOSALS,
    lookahead_days: int = DEFAULT_COUNTER_LOOKAHEAD_DAYS,
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
    min_lead_minutes: int = DEFAULT_MIN_LEAD_MINUTES,
) -> list[dict[str, str]]:
    """Offer real free time back, inside the band the client already named."""
    duration = timedelta(minutes=int(offer["duration_minutes"]))
    band_start, band_end = _band(offer)
    offered_days = {
        _parse(window["start"]).astimezone(JST).date()
        for window in offer.get("windows", [])
    }
    earliest = now.astimezone(JST) + timedelta(minutes=min_lead_minutes)
    day = earliest.date()
    proposals: list[dict[str, str]] = []
    for offset in range(lookahead_days + 1):
        current_day = day + timedelta(days=offset)
        if current_day in offered_days:
            continue  # those are already known-conflicting; do not re-offer them
        cursor = datetime.combine(current_day, datetime.min.time(), tzinfo=JST) + timedelta(
            minutes=band_start
        )
        limit_of_day = datetime.combine(
            current_day, datetime.min.time(), tzinfo=JST
        ) + timedelta(minutes=band_end)
        while cursor + duration <= limit_of_day:
            if cursor >= earliest and _free(
                cursor, cursor + duration, busy, buffer_minutes=buffer_minutes
            ):
                proposals.append({
                    "start": cursor.isoformat(),
                    "end": (cursor + duration).isoformat(),
                })
                break  # at most one proposal per day, so the client gets a spread
            cursor += duration
        if len(proposals) >= limit:
            break
    return proposals[:limit]


def choose_slot(
    *,
    offer: dict[str, Any],
    events: Iterable[dict[str, Any]],
    now: datetime,
    buffer_minutes: int = DEFAULT_BUFFER_MINUTES,
    min_lead_minutes: int = DEFAULT_MIN_LEAD_MINUTES,
) -> dict[str, Any]:
    """Accept the earliest offered slot that is genuinely free, else counter-propose.

    Never returns a request for human input: if every offered slot conflicts we owe
    the client alternatives, not Dais a question.
    """
    busy = busy_intervals(events)
    earliest = now.astimezone(JST) + timedelta(minutes=min_lead_minutes)
    conflicts: list[dict[str, str]] = []
    for slot in candidate_slots(offer):
        start = _parse(slot["start"])
        end = _parse(slot["end"])
        if start < earliest:
            conflicts.append({**slot, "reason": "too_soon"})
            continue
        if not _free(start, end, busy, buffer_minutes=buffer_minutes):
            conflicts.append({**slot, "reason": "calendar_conflict"})
            continue
        return {
            "decision": ACCEPT,
            "slot": slot,
            "reason": "earliest_free_offered_slot",
            "rejected": conflicts,
        }
    return {
        "decision": COUNTER_PROPOSE,
        "slot": None,
        "reason": "every_offered_slot_conflicts",
        "rejected": conflicts,
        "proposals": counter_proposals(
            offer=offer,
            busy=busy,
            now=now,
            buffer_minutes=buffer_minutes,
            min_lead_minutes=min_lead_minutes,
        ),
    }


def counter_proposal_message(proposals: list[dict[str, str]]) -> str:
    """Japanese counter-offer built from free time, sent to the client not to Dais."""
    if not proposals:
        return (
            "ご提示いただいた候補日時が既存の予定と重なっており、恐れ入りますが"
            "別日程のご提示をお願いできますでしょうか。"
        )
    weekdays = "月火水木金土日"
    lines = []
    for proposal in proposals:
        start = _parse(proposal["start"]).astimezone(JST)
        end = _parse(proposal["end"]).astimezone(JST)
        lines.append(
            f"・{start.month}月{start.day}日（{weekdays[start.weekday()]}）"
            f"{start:%H:%M}〜{end:%H:%M}"
        )
    return (
        "ご連絡ありがとうございます。ご提示いただいた候補日時がいずれも既存の予定と"
        "重なっておりました。恐れ入りますが、下記でしたら対応可能です。\n"
        + "\n".join(lines)
        + "\nご都合のよい日時をお知らせいただけますと幸いです。"
    )


def calendar_events_argv(
    *, account: str, start: datetime, end: datetime, max_results: int = 250
) -> list[str]:
    """`gog calendar events` with the flags that exist in gog 0.17.0."""
    return [
        GOG, "calendar", "events",
        "-a", str(account),
        "--json",
        "--from", start.astimezone(JST).isoformat(),
        "--to", end.astimezone(JST).isoformat(),
        "--max", str(int(max_results)),
        "--all-pages",
    ]


def calendar_create_argv(
    *,
    account: str,
    slot: dict[str, str],
    summary: str,
    description: str,
    booking_key: str,
    calendar_id: str = "primary",
) -> list[str]:
    """Create the interview, tagged with the booking key that makes it idempotent."""
    return [
        GOG, "calendar", "create", str(calendar_id),
        "-a", str(account),
        "--json",
        "--summary", str(summary),
        "--from", str(slot["start"]),
        "--to", str(slot["end"]),
        "--start-timezone", "Asia/Tokyo",
        "--end-timezone", "Asia/Tokyo",
        "--description", str(description),
        "--private-prop", f"gig_booking_key={booking_key}",
        "--send-updates", "none",
    ]


def calendar_readback_argv(
    *, account: str, booking_key: str, calendar_id: str = "primary"
) -> list[str]:
    """Authoritative check that the interview is already on the calendar exactly once."""
    return [
        GOG, "calendar", "events", str(calendar_id),
        "-a", str(account),
        "--json",
        "--private-prop-filter", f"gig_booking_key={booking_key}",
        "--max", "10",
        "--all-pages",
    ]
