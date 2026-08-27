#!/usr/bin/env python3
"""Lease-owned browser mutation boundary with no login or account switching."""

from __future__ import annotations

import datetime as dt

from intent_store import IntentStore


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "native timestamp timezone required")
    return parsed


def unique_native_match(intent: dict, items: list[dict], *, expected_handle: str,
                        window_seconds: int = 900) -> dict | None:
    scheduled = parse_time(intent["scheduled_at"])
    matches = []
    for item in items:
        if item.get("native_handle", "").casefold() != expected_handle.casefold():
            continue
        if intent["attribution_token"] not in str(item.get("caption") or ""):
            continue
        try:
            published = parse_time(str(item.get("published_at") or ""))
        except ValueError:
            continue
        if abs((published - scheduled).total_seconds()) <= window_seconds:
            matches.append(item)
    if len(matches) > 1:
        raise ValueError("multiple native candidates")
    return matches[0] if matches else None


class BrowserAdapter:
    """The injected driver may snapshot and submit only; it receives no login method."""

    def __init__(self, store: IntentStore, driver):
        self.store = store
        self.driver = driver

    def preflight(self, publish_key: str, owner: str, fence: int, *,
                  expected_handle: str, now: str) -> dict:
        self.store.assert_lease(publish_key, owner, fence, now)
        existing = self.store.browser_preflight(publish_key)
        if existing:
            require(existing["expected_handle"].casefold() == expected_handle.casefold(),
                    "conflicting browser expected handle")
            return existing
        intent = self.store.get(publish_key)["intent"]
        require(intent["native_handle"].casefold() == expected_handle.casefold(),
                "browser expected handle differs from immutable intent")
        snapshot = self.driver.snapshot(intent)
        require(snapshot.get("logged_in") is True, "browser session is not verified logged in")
        require(str(snapshot.get("native_handle") or "").casefold() == expected_handle.casefold(),
                "browser native handle mismatch")
        profile_url = str(snapshot.get("profile_url") or "")
        require(profile_url.startswith("https://"), "browser profile URL missing")
        return self.store.record_browser_preflight(publish_key, expected_handle,
                                                   snapshot, now)

    def submit(self, publish_key: str, owner: str, fence: int, *, now: str) -> dict:
        preflight = self.store.browser_preflight(publish_key)
        require(preflight is not None, "browser preflight snapshot missing")
        intent = self.store.get(publish_key)["intent"]
        request = {"account_id": intent["account_id"], "asset_sha256": intent["asset_sha256"],
                   "caption_sha256": intent["caption_sha256"],
                   "attribution_token": intent["attribution_token"]}
        attempt = self.store.begin_dispatch(publish_key, owner=owner, fence=fence,
                                            operation="browser_submit", request=request, now=now)
        if not attempt["created"]:
            return attempt
        try:
            response = self.driver.submit(intent)
        except (TimeoutError, ConnectionError, OSError) as exc:
            return self.store.mark_uncertain(attempt["attempt_id"],
                                             f"{type(exc).__name__}: {exc}", now=now)
        try:
            require(str(response.get("native_handle") or "").casefold() ==
                    preflight["expected_handle"].casefold(), "browser response handle mismatch")
            return self.store.record_native_response(attempt["attempt_id"], response, now=now)
        except ValueError as exc:
            self.store.mark_rejected(attempt["attempt_id"], str(exc), now=now,
                                     intent_state="browser_rejected")
            raise
