#!/usr/bin/env python3
"""Invoke the existing budgeted Agent runner only for one due judgment."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


TERMINAL = {"MODEL_CALLED", "RUNNER_INVALID"}


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _due(value: str, now: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("invalid Agent due time") from error
    if parsed.tzinfo is None or now.tzinfo is None:
        raise ValueError("Agent due time must be timezone-bound")
    return parsed <= now


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("Agent model-call receipt history is corrupt") from error
        if not isinstance(row, dict):
            raise ValueError("Agent model-call receipt history is corrupt")
        rows.append(row)
    return rows


def _append(path: Path, receipt: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        stream.write(_canonical(receipt) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run(
    state_root: Path,
    *,
    goal_id: str,
    job_id: str,
    next_due_at: str,
    now: datetime | None = None,
    invoke_budgeted_runner,
) -> dict:
    now = now or datetime.now(timezone.utc)
    event_id = hashlib.sha256(
        f"{goal_id}\0{job_id}\0{next_due_at}".encode()
    ).hexdigest()
    state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = state_root / "agent-model-calls.jsonl"
    lock_path = state_root / ".agent-model-call.lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        budget_day = now.astimezone(ZoneInfo("Asia/Tokyo")).date().isoformat()
        previous = next((
            row for row in reversed(_rows(path))
            if row.get("event_id") == event_id and (
                row.get("state") in TERMINAL
                or row.get("state") == "BUDGET_BLOCKED" and row.get("budget_day") == budget_day
            )
        ), None)
        if previous:
            return previous
        common = {
            "schema_version": 1,
            "receipt_type": "AFFILIATE_AGENT_MODEL_CALL",
            "event_id": event_id,
            "goal_id": goal_id,
            "job_id": job_id,
            "next_due_at": next_due_at,
            "observed_at": now.astimezone(timezone.utc).isoformat(),
            "budget_day": budget_day,
        }
        if not _due(next_due_at, now):
            receipt = {**common, "state": "NOT_DUE", "model_call_count": 0}
            _append(path, receipt)
            return receipt
        summary = invoke_budgeted_runner()
        summary = summary if isinstance(summary, dict) else {}
        budget = summary.get("budget") if isinstance(summary.get("budget"), dict) else {}
        attempts = summary.get("attempt_count")
        if budget.get("status") == "blocked" and attempts == 0:
            state = "BUDGET_BLOCKED"
            model_calls = 0
        elif budget.get("status") == "allowed" and attempts == 1:
            state = "MODEL_CALLED"
            model_calls = 1
        else:
            state = "RUNNER_INVALID"
            model_calls = attempts if isinstance(attempts, int) and attempts >= 0 else None
        receipt = {
            **common,
            "state": state,
            "model_call_count": model_calls,
            "runner_status": summary.get("status"),
            "budget_status": budget.get("status"),
            "budget_reason": budget.get("reason"),
            "reservation_tokens": budget.get("reservation_tokens"),
        }
        _append(path, receipt)
        return receipt
