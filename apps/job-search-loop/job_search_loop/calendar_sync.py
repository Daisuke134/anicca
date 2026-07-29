from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta


def event_key(thread_id: str, start: datetime) -> str:
    value = f"{thread_id}\n{start.astimezone().isoformat()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def prep_windows(now: datetime, start: datetime) -> tuple[str, ...]:
    remaining = start - now
    if remaining > timedelta(days=3):
        return ("three_day", "one_day")
    if remaining > timedelta(days=1):
        return ("three_day", "one_day")
    return ("immediate",)


def create_interview_event(
    *,
    account: str,
    thread_id: str,
    summary: str,
    start: datetime,
    end: datetime,
    description: str,
) -> dict:
    key = event_key(thread_id, start)
    argv = [
        "gog",
        "calendar",
        "create",
        "primary",
        "--account",
        account,
        "--json",
        "--no-input",
        "--summary",
        summary,
        "--from",
        start.isoformat(),
        "--to",
        end.isoformat(),
        "--description",
        description,
        "--private-prop",
        f"anicca_job_event={key}",
        "--reminder",
        "popup:3d",
        "--reminder",
        "popup:1d",
    ]
    completed = subprocess.run(argv, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)
