#!/usr/bin/env python3
"""
gcal departures engine — for each upcoming calendar event, compute the time
the user must LEAVE BY, working backwards from the event start:

    departBy = event_start - travel_time(origin -> location) - prep_buffer

Travel-time aware. Home base + all personal data come from the per-user profile
(identity/profile.json). Travel uses the Google Directions API (transit) when
available, and falls back to a conservative per-area estimate otherwise.

Outputs JSON to stdout: a list of {summary, startIso, location, travelMin,
prepMin, departByIso, travelSource} sorted by departBy.
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
HOME = prof.home_address()
PREP_MIN = int(os.environ.get("LATE_PREP_MIN", "15"))        # get-ready buffer (home day-blocks)
ARRIVE_EARLY_MIN = int(os.environ.get("LATE_ARRIVE_EARLY_MIN", "5"))  # be there N min early
HORIZON_H = int(os.environ.get("LATE_HORIZON_H", "18"))     # look-ahead window
ENV = (Path.home() / ".openclaw" / ".env").read_text()
JST_RE = re.compile(r"出発[:：]\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}|\d{1,2}:\d{2})")


def parse_departure(desc, start):
    """If Anicca already baked a departure time into the event description
    (HARD RULE #7: '出発:HH:MM ... 開始:HH:MM'), trust it as the leave-by time."""
    if not desc:
        return None
    m = JST_RE.search(desc)
    if not m:
        return None
    raw = m.group(1)
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).astimezone(JST)
        hh, mm = map(int, raw.split(":"))
        return start.replace(hour=hh, minute=mm, second=0, microsecond=0)
    except Exception:
        return None


def current_origin():
    """Travel origin = the user's live location (so evening events route from where he
    actually is, not home). Falls back to HOME if no fresh fix."""
    try:
        import base64
        auth = base64.b64encode(f"{env('OWNTRACKS_USER')}:{env('OWNTRACKS_PASS')}".encode()).decode()
        req = urllib.request.Request("http://127.0.0.1:8788/loc/latest", headers={"Authorization": f"Basic {auth}"})
        with urllib.request.urlopen(req, timeout=6) as r:
            d = json.loads(r.read().decode())
        age_min = (datetime.now(JST).timestamp() - d["tst"]) / 60
        if age_min <= 45:
            return f"{d['lat']},{d['lon']}"
    except Exception:
        pass
    return HOME

# Conservative transit minutes from home to common Tokyo areas (fallback only).
AREA_ESTIMATE = {
    "新宿": 15, "信濃町": 8, "四谷": 12, "渋谷": 28, "中野": 32, "大塚": 38,
    "池袋": 30, "中野坂上": 25, "なかの": 32, "高田馬場": 20, "東京": 30,
}
DEFAULT_TRAVEL_MIN = 45


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def fetch_events():
    acct = env("GOG_ACCOUNT", "") or prof.google_account()
    to = (datetime.now(JST) + timedelta(hours=HORIZON_H)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", "today", "--to", to],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
    )
    if out.returncode != 0:
        print(f"[gcal] gog failed: {out.stderr[:200]}", file=sys.stderr)
        return []
    d = json.loads(out.stdout)
    return d if isinstance(d, list) else d.get("events", d.get("items", []))


def _directions(dest, mode, key, origin, extra=None):
    params = {"origin": origin, "destination": dest, "mode": mode, "language": "ja", "key": key}
    if extra:
        params.update(extra)
    url = "https://maps.googleapis.com/maps/api/directions/json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=15) as r:
        d = json.loads(r.read().decode())
    if d.get("status") == "OK":
        return d["routes"][0]["legs"][0]["duration"]["value"] // 60
    return None


def directions_travel_min(dest, origin):
    """Real travel minutes origin->dest. Prefer transit; if the (legacy) transit
    feed has no route, fall back to driving x a Tokyo transit factor (walk+wait+
    train ~1.4x drive). Returns None to let the caller use the area estimate."""
    key = env("GOOGLE_API_KEY")
    if not key or not dest:
        return None
    try:
        t = _directions(dest, "transit", key, origin, {"departure_time": "now"})
        if t is not None:
            return t
    except Exception:
        pass
    try:
        d = _directions(dest, "driving", key, origin)
        if d is not None:
            return max(5, round(d * 1.4))
    except Exception:
        pass
    return None


def estimate_travel_min(text):
    for area, mins in AREA_ESTIMATE.items():
        if area in (text or ""):
            return mins
    return DEFAULT_TRAVEL_MIN


def travel_min(location, summary, origin):
    api = directions_travel_min(location, origin)
    if api is not None:
        return api, "api"
    return estimate_travel_min(f"{location or ''} {summary or ''}"), "estimate"


def main():
    now = datetime.now(JST)
    origin = current_origin()
    rows = []
    for e in fetch_events():
        s = e.get("start", {})
        dt = s.get("dateTime")
        if not dt:
            continue  # skip all-day blocks
        start = datetime.fromisoformat(dt).astimezone(JST)
        if start < now or start > now + timedelta(hours=HORIZON_H):
            continue
        loc = e.get("location")
        summary = e.get("summary") or ""
        desc = e.get("description") or ""

        baked = parse_departure(desc, start)
        if baked is not None:
            # Anicca already computed the leave time (HARD RULE #7) — trust it,
            # do NOT subtract travel again (that was the "called too early" bug).
            depart = baked
            tmin, src = 0, "baked"
        else:
            # Compute the real leave time from where the user IS now, arriving early.
            tmin, src = travel_min(loc, summary, origin)
            buf = ARRIVE_EARLY_MIN if loc else PREP_MIN  # located event: arrive early; home-block: prep
            depart = start - timedelta(minutes=tmin + buf)
        att = [a.get("email") for a in (e.get("attendees") or []) if a.get("email")]
        rows.append({
            "summary": summary, "startIso": start.isoformat(), "location": loc,
            "travelMin": tmin, "travelOrigin": origin, "prepMin": (0 if baked else (ARRIVE_EARLY_MIN if loc else PREP_MIN)),
            "departByIso": depart.isoformat(), "travelSource": src,
            "minutesUntilDepart": int((depart - now).total_seconds() // 60),
            # context for dynamic renraku (who to notify, found per event)
            "description": (e.get("description") or "")[:600],
            "attendees": att,
            "organizer": (e.get("organizer") or {}).get("email"),
            "htmlLink": e.get("htmlLink"),
        })
    rows.sort(key=lambda r: r["departByIso"])
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
