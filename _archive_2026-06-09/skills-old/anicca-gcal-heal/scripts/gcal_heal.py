#!/usr/bin/env python3
"""anicca-gcal-heal — PATCH event.location for events that have it empty.

Scans gcal next HORIZON_DAYS. For each event with `location == ""`:
  - if summary matches routine_at_home → set location = home address
  - elif summary/description has a JP-address pattern → set location = extracted
  - else: leave it (we don't fabricate)

Idempotent: state/healed.json tracks {event_id: address_set}. Re-running after
gog acknowledges the update is harmless because ev.location is no longer empty.
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
ENV = (Path.home() / ".openclaw" / ".env").read_text()
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "healed.json"
HORIZON_DAYS = int(os.environ.get("HEAL_HORIZON_DAYS", "14"))

ROUTINE_AT_HOME_PATTERNS = (
    "sleep", "睡眠", "就寝", "寝る",
    "wake", "起床",
    "meditat", "瞑想", "座禅",
    "breakfast", "朝食", "朝ごはん",
    "lunch", "昼食", "昼ごはん",
    "dinner", "夕食", "晩ごはん",
    "meal", "食事",
    "running", "🏃", "jog",
)
TRAVEL_SUMMARY_PREFIX = ("🚆", "🚌", "🚶", "🚇", "移動")
ADDR_PATTERNS = (
    re.compile(r"(〒\d{3}-\d{4}\s*[^,;()\n　]+)"),
    re.compile(r"((?:北海道|東京都|京都府|大阪府|[^\s]{1,3}県)[^\s,;()\n　]{2,40})"),
    re.compile(r"((?:||MUFG)\s+〒?\d{0,3}-?\d{0,4}\s*[^\s,;()\n　]+)"),
    re.compile(r"([一-龯ぁ-んァ-ヶ]{2,8}駅)"),
)


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def is_routine_at_home(summary):
    s = (summary or "").lower()
    return any(p in s for p in ROUTINE_AT_HOME_PATTERNS)


def is_travel(summary):
    s = (summary or "").strip()
    return any(s.startswith(p) for p in TRAVEL_SUMMARY_PREFIX)


def extract_address(text):
    if not text:
        return None
    for pat in ADDR_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def resolve(event):
    if is_routine_at_home(event.get("summary", "")):
        return prof.home_address(), "home_routine"
    addr = extract_address(event.get("summary", "")) or extract_address(event.get("description", ""))
    if addr:
        return addr, "summary_extracted"
    return None, "unknown"


def list_events(days):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = (datetime.now(JST) + timedelta(days=days)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", "today", "--to", to,
         "--all-pages", "--max", "250"],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=60,
    )
    if out.returncode != 0:
        print(f"[heal] gog list failed: {out.stderr[:200]}", file=sys.stderr)
        return []
    d = json.loads(out.stdout)
    items = d if isinstance(d, list) else d.get("events", d.get("items", []))
    return items


def patch_location(event_id, addr):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "update", "primary", event_id, "-j",
         "--account", acct, "--location", addr],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=30,
    )
    if out.returncode != 0:
        print(f"[heal] update failed for {event_id}: {out.stderr[:200]}",
              file=sys.stderr)
        return False
    return True


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))


def main():
    state = load_state()
    events = list_events(HORIZON_DAYS)
    summary = {"checked": 0, "patched": 0,
               "skipped_has_location": 0,
               "skipped_unknown": 0,
               "skipped_travel": 0,
               "errors": 0}
    patched_log = []
    for ev in events:
        s = ev.get("start", {})
        if not s.get("dateTime"):
            continue
        if is_travel(ev.get("summary", "")):
            summary["skipped_travel"] += 1
            continue
        summary["checked"] += 1
        if (ev.get("location") or "").strip():
            summary["skipped_has_location"] += 1
            continue
        addr, kind = resolve(ev)
        if not addr:
            summary["skipped_unknown"] += 1
            continue
        if patch_location(ev["id"], addr):
            summary["patched"] += 1
            state[ev["id"]] = addr
            patched_log.append({
                "summary": ev.get("summary", "")[:50],
                "kind": kind,
                "addr": addr,
            })
        else:
            summary["errors"] += 1
    save_state(state)
    print(json.dumps({"summary": summary, "patched": patched_log},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
