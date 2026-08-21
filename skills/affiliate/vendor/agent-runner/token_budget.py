#!/usr/bin/env python3
"""Crash-safe reservation ledger for per-pass and per-loop token budgets."""

from __future__ import annotations

import fcntl
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


class TokenBudgetError(ValueError):
    pass


def budget_day_for(now: datetime, tz_name: str) -> str:
    """Bucket an instant into the calendar day the budget resets on.

    The daily breaker bounds a *business* day of spend. The gig loop sells to
    Japanese buyers, so its day must roll over at JST midnight. Using UTC rolled
    the pool over at 09:00 JST and handed a runaway that started in the morning
    a second full allowance an hour later.
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(ZoneInfo(tz_name)).date().isoformat()


def daily_scope_of(event: dict[str, Any]) -> str:
    """Owner of the daily pool a ledger row belongs to.

    Rows written before daily_scope existed carry only ``loop``, and every gig
    LaunchAgent shared it. Falling back to ``loop`` keeps that history
    aggregating as it did rather than silently zeroing today's pool.
    """
    value = event.get("daily_scope")
    if isinstance(value, str) and value:
        return value
    return str(event.get("loop") or "")


class TokenBudgetLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    def _events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
        return events

    def _append(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _charges(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        settlements = {
            str(event.get("event_id")): int(event.get("charged_tokens") or 0)
            for event in events
            if event.get("type") == "settlement"
        }
        charges: list[dict[str, Any]] = []
        for event in events:
            if event.get("type") != "reservation" or event.get("status") != "allowed":
                continue
            row = dict(event)
            event_id = str(row.get("event_id") or "")
            row["charged_tokens"] = settlements.get(
                event_id, int(row.get("reservation_tokens") or 0)
            )
            charges.append(row)
        return charges

    def reserve(
        self,
        *,
        event_id: str,
        loop: str,
        scope_id: str,
        daily_scope: str,
        day: str,
        reservation_tokens: int,
        pass_limit: int,
        daily_limit: int,
    ) -> dict[str, Any]:
        if (
            not event_id or not loop or not scope_id or not daily_scope or not day
            or reservation_tokens <= 0 or pass_limit <= 0 or daily_limit <= 0
        ):
            raise TokenBudgetError("token budget inputs must be nonempty and positive")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            events = self._events()
            # The daily pool belongs to one owner (one LaunchAgent), not to the
            # whole loop. Sharing it across owners let a low-limit owner be
            # evaluated against a high-spend owner's consumption and stay dead
            # blocked all day.
            charges = [
                row for row in self._charges(events)
                if daily_scope_of(row) == daily_scope and row.get("day") == day
            ]
            pass_consumed = sum(
                int(row["charged_tokens"])
                for row in charges
                if row.get("scope_id") == scope_id
            )
            daily_consumed = sum(int(row["charged_tokens"]) for row in charges)
            reason = None
            if pass_consumed + reservation_tokens > pass_limit:
                reason = "pass_token_budget_exceeded"
            elif daily_consumed + reservation_tokens > daily_limit:
                reason = "loop_daily_token_budget_exceeded"
            decision = {
                "version": 1,
                "type": "reservation",
                "event_id": event_id,
                "timestamp": int(time.time()),
                "loop": loop,
                "scope_id": scope_id,
                "daily_scope": daily_scope,
                "day": day,
                "status": "blocked" if reason else "allowed",
                "reason": reason,
                "reservation_tokens": reservation_tokens,
                "pass_limit_tokens": pass_limit,
                "daily_limit_tokens": daily_limit,
                "pass_consumed_tokens": pass_consumed,
                "daily_consumed_tokens": daily_consumed,
            }
            self._append(decision)
            return decision

    def settle(
        self,
        *,
        event_id: str,
        actual_tokens: int,
        measurement: str,
    ) -> dict[str, Any]:
        if not event_id or actual_tokens < 0:
            raise TokenBudgetError("invalid token budget settlement")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            events = self._events()
            reservation = next((
                event for event in reversed(events)
                if event.get("type") == "reservation"
                and event.get("event_id") == event_id
                and event.get("status") == "allowed"
            ), None)
            if reservation is None:
                raise TokenBudgetError("settlement lacks an allowed reservation")
            row = {
                "version": 1,
                "type": "settlement",
                "event_id": event_id,
                "timestamp": int(time.time()),
                "measurement": measurement,
                "charged_tokens": actual_tokens,
            }
            self._append(row)
            charges = self._charges(self._events())
            same_loop_day = [
                charge for charge in charges
                if daily_scope_of(charge) == daily_scope_of(reservation)
                and charge.get("day") == reservation.get("day")
            ]
            row["pass_consumed_after_tokens"] = sum(
                int(charge["charged_tokens"])
                for charge in same_loop_day
                if charge.get("scope_id") == reservation.get("scope_id")
            )
            row["daily_consumed_after_tokens"] = sum(
                int(charge["charged_tokens"]) for charge in same_loop_day
            )
            return row
