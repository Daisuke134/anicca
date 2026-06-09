#!/usr/bin/env python3
"""anicca-schedule-template — INSERT a default daily routine into empty days.

Algorithm per day in horizon:
  1. List existing gcal events on that day
  2. If count >= EMPTY_DAY_MIN_EVENTS → skip
  3. Walk the template slots
  4. For each slot, if no overlapping event exists → INSERT
  5. Record state/template_inserted.json so re-runs skip same-day work
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
HOME = Path.home() / ".openclaw"
ENV = (HOME / ".env").read_text()
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "template_inserted.json"
HORIZON_DAYS = int(os.environ.get("TEMPLATE_HORIZON_DAYS", "7"))
EMPTY_DAY_MIN_EVENTS = int(os.environ.get("TEMPLATE_EMPTY_THRESHOLD", "2"))
FILL_WEEKENDS = os.environ.get("TEMPLATE_FILL_WEEKENDS", "0") == "1"


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def parse_hm(s, default_hh, default_mm):
    """Parse 'HH:MM' string → (hh, mm), fallback on bad input."""
    if not s:
        return default_hh, default_mm
    try:
        hh, mm = s.split(":")
        return int(hh), int(mm)
    except Exception:
        return default_hh, default_mm


def add_min(hh, mm, delta):
    total = hh * 60 + mm + delta
    return (total // 60) % 24, total % 60


def home_addr():
    return prof.home_address() or ""


def slot(label, summary, hh, mm, duration_min, location):
    return {"label": label, "summary": summary,
            "hh": hh, "mm": mm,
            "duration_min": duration_min,
            "location": location}


def build_template(wake_hh, wake_mm):
    """Return list of slots for one day."""
    home = home_addr()
    s = []
    s.append(slot("wake",        "🛏 Wake up",            wake_hh, wake_mm,                       15, home))
    h, m = add_min(wake_hh, wake_mm, 30)
    s.append(slot("meditation",  "🧘 Meditation",         h, m,                                  30, home))
    h, m = add_min(wake_hh, wake_mm, 60)
    s.append(slot("running",     "🏃 Running",            h, m,                                  30, home))
    h, m = add_min(wake_hh, wake_mm, 90)
    s.append(slot("breakfast",   "🍳 Breakfast",          h, m,                                  30, home))
    h, m = add_min(wake_hh, wake_mm, 150)
    s.append(slot("deep_work",   "💼 Deep work",          h, m,                                 180, home))
    s.append(slot("lunch",       "🍱 Lunch",              12, 0,                                 60, home))
    h, m = add_min(wake_hh, wake_mm, 690)  # +11.5h
    s.append(slot("walk",        "🚶 Walk",               h, m,                                  30, home))
    s.append(slot("dinner",      "🍲 Dinner",             19, 0,                                 60, home))
    s.append(slot("winddown",    "📚 Wind down",          21, 0,                                 60, home))
    # Sleep wraps to next day, modelled as end_of_day-ish 23:00 → end
    s.append(slot("sleep",       "😴 Sleep",              23, 0,                                420, home))
    return s


def list_events(date_str):
    """List events for a single day. date_str = YYYY-MM-DD."""
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = (datetime.fromisoformat(date_str) + timedelta(days=1)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", date_str, "--to", to,
         "--all-pages", "--max", "100"],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=45,
    )
    if out.returncode != 0:
        return []
    try:
        d = json.loads(out.stdout)
        items = d if isinstance(d, list) else d.get("events", d.get("items", []))
    except Exception:
        return []
    rows = []
    for ev in items:
        s = (ev.get("start") or {}).get("dateTime")
        e = (ev.get("end") or {}).get("dateTime")
        if not (s and e):
            continue
        rows.append({
            "summary": ev.get("summary") or "",
            "start": datetime.fromisoformat(s).astimezone(JST),
            "end": datetime.fromisoformat(e).astimezone(JST),
        })
    return rows


def overlaps(start, end, events):
    for ev in events:
        if start < ev["end"] and end > ev["start"]:
            return True
    return False


def insert_event(start_dt, end_dt, summary, location):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "create", "primary", "-j",
         "--account", acct,
         "--summary", summary,
         "--from", start_dt.isoformat(),
         "--to", end_dt.isoformat(),
         "--location", location,
         "--description", "Auto-inserted by anicca-schedule-template. "
                          "Adjust freely; this default exists so the routine "
                          "skills have something to anchor on."],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=30,
    )
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)["event"]["id"]
    except Exception:
        return None


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))


def main():
    now = datetime.now(JST)
    wake_str = prof.get("alarm.wakeTime", "07:00") if hasattr(prof, "get") else "07:00"
    wake_hh, wake_mm = parse_hm(wake_str, 7, 0)
    template = build_template(wake_hh, wake_mm)
    state = load_state()
    summary = {"days_checked": 0, "days_skipped_nonempty": 0,
               "days_skipped_weekend": 0, "days_filled": 0, "slots_inserted": 0}
    inserted_log = []

    for offset in range(HORIZON_DAYS):
        d = (now + timedelta(days=offset)).date()
        date_str = d.isoformat()
        if state.get(date_str):
            summary["days_skipped_nonempty"] += 1
            continue
        if not FILL_WEEKENDS and d.weekday() >= 5:
            summary["days_skipped_weekend"] += 1
            continue
        summary["days_checked"] += 1
        existing = list_events(date_str)
        if len(existing) >= EMPTY_DAY_MIN_EVENTS:
            summary["days_skipped_nonempty"] += 1
            state[date_str] = {"reason": "nonempty", "count": len(existing)}
            continue

        day_inserts = []
        for s in template:
            start_dt = datetime(d.year, d.month, d.day, s["hh"], s["mm"], tzinfo=JST)
            end_dt = start_dt + timedelta(minutes=s["duration_min"])
            if overlaps(start_dt, end_dt, existing):
                continue
            ins_id = insert_event(start_dt, end_dt, s["summary"], s["location"])
            if ins_id:
                day_inserts.append({"slot": s["label"], "id": ins_id,
                                    "start": start_dt.isoformat()})
                summary["slots_inserted"] += 1
        if day_inserts:
            summary["days_filled"] += 1
            state[date_str] = {"inserted": day_inserts}
            inserted_log.append({"date": date_str, "count": len(day_inserts)})

    save_state(state)
    print(json.dumps({"summary": summary, "inserted_by_day": inserted_log},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
