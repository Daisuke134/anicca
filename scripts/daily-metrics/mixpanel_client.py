"""Mixpanel client for 7-day onboarding funnel counts."""

from __future__ import annotations

import json
import os
from typing import Optional

import httpx

from models import MixpanelMetrics
from window import ReportingWindow, default_reporting_window

MIXPANEL_EXPORT_URL = "https://data.mixpanel.com/api/2.0/export"

_EVENTS: tuple[str, ...] = (
    "onboarding_started",
    "onboarding_welcome_completed",
    "onboarding_struggles_completed",
    "onboarding_struggle_depth_completed",
    "onboarding_goals_completed",
    "onboarding_insight_completed",
    "onboarding_valueprop_completed",
    "onboarding_notifications_completed",
    "onboarding_completed",
    "paywall_primer_viewed",
    "paywall_plan_selection_viewed",
    "onboarding_paywall_purchased",
    "trial_started",
    "onboarding_paywall_dismissed_free",
)


def _basic_auth() -> tuple[str, str]:
    """Resolve Mixpanel Basic Auth credentials from env."""
    service_account = os.environ.get("MIXPANEL_SERVICE_ACCOUNT", "")
    if ":" in service_account:
        username, secret = service_account.split(":", 1)
        return username.strip(), secret.strip()
    raise KeyError("MIXPANEL_SERVICE_ACCOUNT")


async def fetch_mixpanel_metrics(window: Optional[ReportingWindow] = None) -> MixpanelMetrics:
    """Fetch 7-day unique user counts for onboarding funnel events."""
    if window is None:
        window = default_reporting_window()

    username, password = _basic_auth()

    params = {
        "from_date": window.start_date.isoformat(),
        "to_date": window.end_date.isoformat(),
        "event": json.dumps(list(_EVENTS), ensure_ascii=False),
    }

    unique_users: dict[str, set[str]] = {event: set() for event in _EVENTS}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            MIXPANEL_EXPORT_URL,
            params=params,
            auth=(username, password),
        )
        response.raise_for_status()

    for line in response.text.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        event_name = item.get("event")
        if event_name not in unique_users:
            continue
        properties = item.get("properties", {})
        distinct_id = _coalesce_distinct_id(properties)
        if distinct_id:
            unique_users[event_name].add(distinct_id)

    return MixpanelMetrics(
        onboarding_started=len(unique_users["onboarding_started"]),
        onboarding_welcome_completed=len(unique_users["onboarding_welcome_completed"]),
        onboarding_struggles_completed=len(unique_users["onboarding_struggles_completed"]),
        onboarding_struggle_depth_completed=len(unique_users["onboarding_struggle_depth_completed"]),
        onboarding_goals_completed=len(unique_users["onboarding_goals_completed"]),
        onboarding_insight_completed=len(unique_users["onboarding_insight_completed"]),
        onboarding_valueprop_completed=len(unique_users["onboarding_valueprop_completed"]),
        onboarding_notifications_completed=len(unique_users["onboarding_notifications_completed"]),
        onboarding_completed=len(unique_users["onboarding_completed"]),
        paywall_primer_viewed=len(unique_users["paywall_primer_viewed"]),
        paywall_plan_selection_viewed=len(unique_users["paywall_plan_selection_viewed"]),
        onboarding_paywall_purchased=len(unique_users["onboarding_paywall_purchased"]),
        trial_started=len(unique_users["trial_started"]),
        onboarding_paywall_dismissed_free=len(unique_users["onboarding_paywall_dismissed_free"]),
    )


def _coalesce_distinct_id(properties: dict) -> Optional[str]:
    """Resolve distinct user id from common Mixpanel keys."""
    candidates = (
        properties.get("distinct_id"),
        properties.get("$user_id"),
        properties.get("user_id"),
    )
    for value in candidates:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
