#!/usr/bin/env python3
"""Join Writer funnel events without losing product or artifact lineage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


LINEAGE_FIELDS = (
    "product_id",
    "run_id",
    "artifact_id",
    "variant_id",
    "click_id",
)
REWARD_RANK = {
    "impression": 1,
    "engaged_read": 2,
    "qualified_cta_click": 3,
    "activation": 4,
    "paid": 5,
}


class AttributionInvariant(ValueError):
    """An event set cannot be attributed to one immutable lineage."""


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise AttributionInvariant("occurred_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def attribute_events(
    events: list[dict[str, Any]],
    *,
    as_of: str,
    attribution_window_days: int,
) -> dict[str, Any]:
    """Return one reward receipt for events sharing the exact five-key lineage."""
    if not events:
        raise AttributionInvariant("events are required")

    lineage = {field: events[0].get(field) for field in LINEAGE_FIELDS}
    for field, value in lineage.items():
        if not isinstance(value, str) or not value:
            raise AttributionInvariant(f"{field} is required")
    event_ids: set[str] = set()
    for event in events:
        if any(event.get(field) != lineage[field] for field in LINEAGE_FIELDS):
            raise AttributionInvariant("events do not share one attribution lineage")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise AttributionInvariant("event_id is required")
        if event_id in event_ids:
            raise AttributionInvariant("event_id is duplicated")
        event_ids.add(event_id)
        if event.get("event_type") not in REWARD_RANK:
            raise AttributionInvariant("event_type is unsupported")
        if event["event_type"] == "paid" and (
            not isinstance(event.get("amount_minor"), int)
            or event["amount_minor"] < 0
            or not isinstance(event.get("currency"), str)
            or not event["currency"]
        ):
            raise AttributionInvariant(
                "paid event requires amount_minor and currency"
            )
        _parse_time(event["occurred_at"])

    ordered_types = [
        event_type
        for event_type in REWARD_RANK
        if any(event["event_type"] == event_type for event in events)
    ]
    best_type = max(ordered_types, key=REWARD_RANK.__getitem__)
    best_event = next(
        event for event in events if event["event_type"] == best_type
    )
    reward: dict[str, Any] = {
        "tier": best_type,
        "rank": REWARD_RANK[best_type],
    }
    if best_type == "paid":
        reward["amount_minor"] = best_event["amount_minor"]
        reward["currency"] = best_event["currency"]
    click = next(
        (
            event
            for event in events
            if event["event_type"] == "qualified_cta_click"
        ),
        None,
    )
    if click is None:
        return {
            **lineage,
            "status": "insufficient",
            "reason": "qualified_cta_click_missing",
            "reward": reward,
            "observed_event_types": ordered_types,
            "window_closes_at": None,
        }
    window_closes = _parse_time(click["occurred_at"]) + timedelta(
        days=attribution_window_days
    )
    if any(
        _parse_time(event["occurred_at"]) > window_closes
        for event in events
    ):
        raise AttributionInvariant("event is outside attribution window")

    observed_at = _parse_time(as_of)
    status = (
        "scorable"
        if best_type == "paid" or observed_at >= window_closes
        else "unknown"
    )
    return {
        **lineage,
        "status": status,
        "reward": reward,
        "observed_event_types": ordered_types,
        "window_closes_at": _format_time(window_closes),
    }
