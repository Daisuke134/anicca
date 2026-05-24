#!/usr/bin/env python3
"""
lateness check — the core of the never-be-late loop.

Combines (a) gcal departure times [gcal_departures.py] with (b) Dais's live
location [loco /loc/latest] and decides whether to fire a realtime "you must
leave NOW" phone call.

Decision (pure, unit-tested in decide()):
  late risk  ⟺  the next event's departBy is within LEAD minutes (or past)
                AND Dais is still home (within radius) AND not moving.

On late risk: place a realtime lateness-mode call (Twilio <-> Gemini Live, the
imokenet bridge) with a context string describing the event + deadline, and
report to Slack. (Stakeholder renraku = task #18, layered on top.)
"""
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ENV = (Path.home() / ".openclaw" / ".env").read_text()
URL_FILE = Path.home() / ".openclaw" / "workspace" / "imokenet" / "state" / "public_url.txt"
DEPART_SCRIPT = Path.home() / ".openclaw" / "skills" / "lateness-guard" / "scripts" / "gcal_departures.py"

# Home base + all personal data come from the per-user profile (OSS-general).
sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

_hlat, _hlon = prof.home_latlon()
HOME_LAT = float(os.environ.get("LATE_HOME_LAT") or _hlat)
HOME_LON = float(os.environ.get("LATE_HOME_LON") or _hlon)
HOME_RADIUS_M = float(os.environ.get("LATE_HOME_RADIUS_M", "300"))
LEAD_MIN = int(os.environ.get("LATE_LEAD_MIN", "8"))         # call ~this far before the real leave time
NUDGE_MIN = int(os.environ.get("LATE_NUDGE_MIN", "20"))      # gentle Slack nudge this far before
MOVING_VEL = float(os.environ.get("LATE_MOVING_VEL", "0.8")) # m/s -> considered moving
STALE_MIN = int(os.environ.get("LATE_STALE_MIN", "12"))      # location older than this = stale (no leave-call on stale data)


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def decide(now, location, departures, home=None, home_radius_m=None):
    """Pure decision. Returns dict {action, reason, event}.
    action in {'call', 'ok', 'no-events', 'no-location', 'stale-location'}.
    home=(lat,lon) overrides the module HOME_* (multi-tenant: pass the subscriber's home)."""
    if not departures:
        return {"action": "no-events", "reason": "no upcoming events", "event": None}
    if not location:
        return {"action": "no-location", "reason": "no location fix", "event": None}

    home_lat, home_lon = home if home else (HOME_LAT, HOME_LON)
    radius = home_radius_m if home_radius_m is not None else HOME_RADIUS_M
    nxt = departures[0]  # earliest departBy
    depart = datetime.fromisoformat(nxt["departByIso"]).astimezone(JST)
    mins = (depart - now).total_seconds() / 60
    dist = haversine_m(home_lat, home_lon, location["lat"], location["lon"])
    at_home = dist <= radius
    vel = location.get("vel")
    moving = vel is not None and vel >= MOVING_VEL
    age_min = (now.timestamp() - location["tst"]) / 60

    # FRESHNESS GATE — fixes the 2026-05-24 "出発しろ" misfire while he was already
    # at the <training-school>. A "leave now / you're late" decision must be based on a FRESH
    # fix. If the location is stale we genuinely don't know where he is, so we never
    # tell him to leave — guessing on an old at-home fix is exactly what went wrong.
    if age_min > STALE_MIN:
        return {"action": "stale-location",
                "reason": f"location {int(age_min)}m old — won't guess (need fresh fix; set OwnTracks=Move)",
                "event": nxt}

    # Already left home / moving / en route -> he's on his way. Don't tell him to
    # leave. (If he left the house, is on the train, or has arrived, no call.)
    if moving or not at_home:
        return {"action": "ok",
                "reason": f"en route — atHome={at_home}({int(dist)}m) moving={moving}, no leave-call",
                "event": nxt}

    # At home, FRESH fix, not moving -> the only state where "leave now" is valid.
    if mins <= LEAD_MIN:
        return {"action": "call",
                "reason": f"departBy in {int(mins)}m, still home ({int(dist)}m), fresh+not moving",
                "event": nxt}
    if mins <= NUDGE_MIN:
        return {"action": "nudge",
                "reason": f"departBy in {int(mins)}m, still home — gentle reminder",
                "event": nxt}
    return {"action": "ok",
            "reason": f"departBy in {int(mins)}m, atHome={at_home}({int(dist)}m), moving={moving}",
            "event": nxt}


# ---- IO ----
def get_location():
    base = "http://127.0.0.1:8788"
    auth = base64.b64encode(f"{env('OWNTRACKS_USER')}:{env('OWNTRACKS_PASS')}".encode()).decode()
    req = urllib.request.Request(f"{base}/loc/latest", headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def reverse_geocode(loc):
    """lat/lon -> short JP place name (for a location-aware call message)."""
    key = env("GOOGLE_API_KEY")
    if not (loc and key):
        return None
    try:
        q = urllib.parse.urlencode({"latlng": f"{loc['lat']},{loc['lon']}", "key": key, "language": "ja"})
        with urllib.request.urlopen(f"https://maps.googleapis.com/maps/api/geocode/json?{q}", timeout=8) as r:
            j = json.loads(r.read().decode())
        comps = j["results"][0]["address_components"]
        # prefer ward + neighbourhood (新宿区 + <your-address>) over full address
        parts = [c["long_name"] for c in comps
                 if any(t in c["types"] for t in ("sublocality_level_1", "sublocality_level_2", "locality"))]
        return "".join(parts[-2:]) if parts else j["results"][0]["formatted_address"]
    except Exception:
        return None


def get_departures():
    out = subprocess.run([sys.executable, str(DEPART_SCRIPT)], capture_output=True, text=True, timeout=120)
    try:
        return json.loads(out.stdout)
    except Exception:
        print(f"[late] departures parse failed: {out.stderr[:200]}", file=sys.stderr)
        return []


def place_lateness_call(ctx):
    base = URL_FILE.read_text().strip().rstrip("/")
    sid, token, frm = env("TWILIO_ACCOUNT_SID"), env("TWILIO_AUTH_TOKEN"), env("TWILIO_PHONE_NUMBER")
    to = os.environ.get("LATE_PHONE") or prof.phone()
    twiml_url = f"{base}/twiml?{urllib.parse.urlencode({'name': prof.name(), 'mode': 'lateness', 'ctx': ctx})}"
    data = urllib.parse.urlencode({"To": to, "From": frm, "Url": twiml_url, "Method": "GET"}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json", data=data, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("sid")


def slack(text):
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": env("SLACK_CHANNEL_ID"), "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {env('SLACK_BOT_TOKEN')}"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"[late] slack failed: {e}", file=sys.stderr)


def main():
    now = datetime.now(JST)
    loc_now = get_location()
    d = decide(now, loc_now, get_departures())
    print(json.dumps({k: (v if k != "event" else (v or {}).get("summary")) for k, v in d.items()}, ensure_ascii=False))
    if d["action"] == "nudge":
        e = d["event"]
        depart = datetime.fromisoformat(e["departByIso"]).astimezone(JST).strftime("%H:%M")
        once_path = Path(__file__).resolve().parent.parent / "state" / "nudge_sent.json"
        try:
            done = json.loads(once_path.read_text())
        except Exception:
            done = []
        key = f"{e['summary']}|{e['departByIso']}"
        if key not in done:
            loc = f"（{e['location']}）" if e.get("location") else ""
            slack(f"⏰ そろそろ準備を。『{e['summary']}』{loc}は {depart} に家を出る予定。")
            done.append(key)
            once_path.write_text(json.dumps(done, ensure_ascii=False))
            print(f"[late] nudge sent for {e['summary']}")

    if d["action"] == "call":
        e = d["event"]
        start = datetime.fromisoformat(e["startIso"]).astimezone(JST).strftime("%H:%M")
        depart_dt = datetime.fromisoformat(e["departByIso"]).astimezone(JST)
        depart = depart_dt.strftime("%H:%M")
        place = reverse_geocode(loc_now) or "今いる場所"
        travel = e.get("travelMin")
        travel_str = f"そこから約{travel}分、" if travel else ""
        ctx = (f"次の予定『{e['summary']}』は {start} 開始"
               + (f"、場所は {e['location']}" if e.get("location") else "")
               + f"。今ダイスは{place}にいて、{travel_str}{depart} までに出ないと間に合わない。"
               + "駅まで歩いて電車で向かうよう、一歩ずつ具体的に促して。")
        sid = place_lateness_call(ctx)
        slack(f"🏃 遅刻防止コール: {d['reason']} → {e['summary']} (call {sid})")
        print(f"[late] placed lateness call sid={sid}")

        # If departBy already passed and he's still home, he WILL be late.
        # Don't hard-code the recipient: emit a RENRAKU_NEEDED block with the
        # event's own context and let the agent (Anicca) find who to notify and
        # how, per this specific schedule. Emit once per event/day (dedup).
        mins_to_depart = (depart_dt - now).total_seconds() / 60
        if mins_to_depart <= 0:
            sent_path = Path(__file__).resolve().parent.parent / "state" / "renraku_sent.json"
            try:
                sent = json.loads(sent_path.read_text())
            except Exception:
                sent = []
            key = f"{e['summary']}|{e['departByIso']}"
            if key not in sent:
                minutes_late = max(5, int(-mins_to_depart))
                ctx = {
                    "summary": e["summary"], "location": e.get("location"),
                    "startIso": e["startIso"], "minutesLate": minutes_late,
                    "attendees": e.get("attendees") or [],
                    "organizer": e.get("organizer"),
                    "description": e.get("description") or "",
                    "htmlLink": e.get("htmlLink"),
                }
                print("RENRAKU_NEEDED " + json.dumps(ctx, ensure_ascii=False))
                sent.append(key)
                sent_path.write_text(json.dumps(sent, ensure_ascii=False))


if __name__ == "__main__":
    main()
