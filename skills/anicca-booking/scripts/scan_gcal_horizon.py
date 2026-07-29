#!/usr/bin/env python3
"""
scan_gcal_horizon — find empty 1h+ slots in the next 3 days (waking hours).
Output: list of {date, startIso, endIso, duration_min} sorted by startIso.

Used by anicca-booking to know WHERE to propose new events.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
STATE_HOME = Path(os.environ.get(
    "LIFE_MANAGER_STATE_HOME",
    Path.home() / ".local/state/life-manager",
)).expanduser()
sys.path.insert(0, str(REPO_ROOT / "skills/_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
HORIZON_DAYS = int(os.environ.get("BOOK_HORIZON_DAYS", "14"))
MIN_SLOT_MIN = int(os.environ.get("BOOK_MIN_SLOT_MIN", "60"))
WAKING_START_H = int(os.environ.get("BOOK_WAKING_START_H", "10"))  # don't propose pre-10am
WAKING_END_H = int(os.environ.get("BOOK_WAKING_END_H", "23"))      # don't propose post-23

ENV_PATH = STATE_HOME / ".env"
ENV = ENV_PATH.read_text() if ENV_PATH.is_file() else ""


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def fetch_events(start_date, end_date):
    acct = env("GOG_ACCOUNT", "") or prof.google_account()
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", start_date, "--to", end_date,
         "--all-pages", "--max", "500"],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
    )
    if out.returncode != 0:
        print(f"[scan] gog failed: {out.stderr[:200]}", file=sys.stderr)
        return []
    d = json.loads(out.stdout)
    return d if isinstance(d, list) else d.get("events", d.get("items", []))


def find_empty_slots():
    now = datetime.now(JST)
    horizon_end = now + timedelta(days=HORIZON_DAYS)
    events = fetch_events(now.strftime("%Y-%m-%d"), horizon_end.strftime("%Y-%m-%d"))

    # Extract busy intervals (skip all-day, skip past)
    busy = []
    for e in events:
        s_dt = e.get("start", {}).get("dateTime")
        e_dt = e.get("end", {}).get("dateTime")
        if not s_dt or not e_dt:
            continue
        s = datetime.fromisoformat(s_dt).astimezone(JST)
        end = datetime.fromisoformat(e_dt).astimezone(JST)
        if end < now:
            continue
        busy.append((max(s, now), end))
    busy.sort()

    # TRAVEL_BUFFER pad (must stay in sync with propose.py gate3 TRAVEL_BUFFER_MIN=30):
    # gate3 rejects any slot within +-30min of a busy event, so slots must be carved
    # from buffer-padded busy intervals or every gap-adjacent slot is born dead
    # (root cause of the 2026-07-10 25/25 physical_conflict block).
    TRAVEL_BUFFER_MIN = 30
    busy = [(max(s - timedelta(minutes=TRAVEL_BUFFER_MIN), now),
             e + timedelta(minutes=TRAVEL_BUFFER_MIN)) for s, e in busy]

    # Walk day-by-day in waking hours, find gaps
    slots = []
    for d_offset in range(HORIZON_DAYS):
        day = (now + timedelta(days=d_offset)).date()
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=JST).replace(hour=WAKING_START_H)
        day_end = datetime.combine(day, datetime.min.time(), tzinfo=JST).replace(hour=WAKING_END_H)
        if d_offset == 0 and now > day_start:
            day_start = now
        # Filter busy intervals intersecting this day
        day_busy = sorted([(max(s, day_start), min(e, day_end))
                           for s, e in busy if e > day_start and s < day_end])
        cursor = day_start
        for s, e in day_busy:
            if s > cursor and (s - cursor).total_seconds() >= MIN_SLOT_MIN * 60:
                slots.append({"date": day.isoformat(),
                              "startIso": cursor.isoformat(),
                              "endIso": s.isoformat(),
                              "duration_min": int((s - cursor).total_seconds() // 60)})
            cursor = max(cursor, e)
        if cursor < day_end and (day_end - cursor).total_seconds() >= MIN_SLOT_MIN * 60:
            slots.append({"date": day.isoformat(),
                          "startIso": cursor.isoformat(),
                          "endIso": day_end.isoformat(),
                          "duration_min": int((day_end - cursor).total_seconds() // 60)})
    return slots


if __name__ == "__main__":
    slots = find_empty_slots()
    print(json.dumps(slots, ensure_ascii=False, indent=2))
