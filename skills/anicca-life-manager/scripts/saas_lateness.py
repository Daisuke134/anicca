#!/usr/bin/env python3
"""
saas_lateness — multi-tenant never-be-late for aniccaai.com/alarm subscribers.

For each active subscriber (Supabase subscriber_profiles) who connected a calendar
(ics_url) and location (loco-ingest), compute ETA from their CURRENT location to
their next event and, like the personal lateness-guard, nudge / call / renraku.
Runs every ~15 min (launchd). Pure decision reused from lateness_check.decide().
"""
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))  # own scripts dir (self-contained skill)
import lateness_check as lc  # decide(), haversine_m(), slack
import gcal_departures as gd  # directions_travel_min(dest, origin)

LIFE_MANAGER_HOME = Path(os.environ.get(
    "LIFE_MANAGER_HOME", str(Path.home() / ".local" / "state" / "life-manager"),
))
ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(LIFE_MANAGER_HOME)))
ENV_PATH = Path(os.environ.get("LIFE_MANAGER_ENV_FILE", str(ANICCA_HOME / ".env")))
ENV = ENV_PATH.read_text() if ENV_PATH.is_file() else ""
URL_FILE = Path(os.environ.get(
    "LIFE_MANAGER_CALL_BRIDGE_URL_FILE",
    str(ANICCA_HOME / "state" / "call-bridge" / "public_url.txt"),
))
STATE = ANICCA_HOME / "state" / "saas-lateness" / "sent.json"
ARRIVE_EARLY = 5


def env(n, d=""):
    m = re.search(rf"^{n}=(.*)$", ENV, re.M); return (m.group(1).strip().strip('"').strip("'") if m else d)


def supa_get(path):
    url = env("SUPABASE_URL"); key = env("SUPABASE_SERVICE_ROLE_KEY")
    req = urllib.request.Request(f"{url}/rest/v1/{path}", headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())


def supa_patch(path, body):
    url = env("SUPABASE_URL"); key = env("SUPABASE_SERVICE_ROLE_KEY")
    req = urllib.request.Request(f"{url}/rest/v1/{path}", data=json.dumps(body).encode(), method="PATCH",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json", "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.status


def geocode(address):
    """Address -> (lat, lon) via Google Geocoding (key from env). None on failure."""
    key = env("GOOGLE_API_KEY")
    if not (address and key):
        return None
    q = urllib.parse.urlencode({"address": address, "key": key})
    try:
        with urllib.request.urlopen(f"https://maps.googleapis.com/maps/api/geocode/json?{q}", timeout=12) as r:
            j = json.loads(r.read().decode())
        loc = j["results"][0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])
    except Exception:
        return None


def resolve_home(s):
    """Subscriber home (lat,lon): stored, else geocode home_address once and persist."""
    if s.get("home_lat") is not None and s.get("home_lon") is not None:
        return (s["home_lat"], s["home_lon"])
    g = geocode(s.get("home_address"))
    if g:
        try:
            supa_patch(f"subscriber_profiles?user_id=eq.{s['user_id']}", {"home_lat": g[0], "home_lon": g[1]})
        except Exception:
            pass
    return g


def fetch_ics_events(ics_url, now, horizon_h=18):
    """Minimal ICS parser: upcoming VEVENTs (start within horizon) with summary+location."""
    try:
        with urllib.request.urlopen(ics_url, timeout=15) as r:
            raw = r.read().decode("utf-8", "replace")
    except Exception:
        return []
    # unfold folded lines
    raw = re.sub(r"\r\n[ \t]", "", raw)
    events = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", raw, re.S):
        def field(name):
            m = re.search(rf"^{name}(?:;[^:\r\n]*)?:(.+)$", block, re.M)
            return m.group(1).strip() if m else None
        dt = field("DTSTART")
        if not dt:
            continue
        try:
            s = dt.strip()
            if s.endswith("Z"):
                start = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            elif "T" in s:
                start = datetime.strptime(s[:15], "%Y%m%dT%H%M%S").replace(tzinfo=now.tzinfo)
            else:
                continue
        except Exception:
            continue
        if now <= start <= now + timedelta(hours=horizon_h):
            events.append({"summary": field("SUMMARY") or "予定", "location": field("LOCATION"), "start": start})
    events.sort(key=lambda e: e["start"])
    return events


def fetch_composio_events(user_id, now, horizon_h=18):
    """Real-time Google Calendar via Composio (managed OAuth). Same shape as fetch_ics_events.
    user_id = subscriber phone (the Composio user id used at connect time)."""
    key = env("COMPOSIO_API_KEY")
    if not key:
        return []
    body = json.dumps({"user_id": user_id, "arguments": {
        "calendarId": "primary", "singleEvents": True, "orderBy": "startTime",
        "timeMin": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeMax": (now + timedelta(hours=horizon_h)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }}).encode()
    req = urllib.request.Request(
        "https://backend.composio.dev/api/v3/tools/execute/GOOGLECALENDAR_EVENTS_LIST",
        data=body, method="POST", headers={"x-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        print(f"[saas-late] composio events failed: {e}", file=sys.stderr)
        return []
    if not j.get("successful"):
        print(f"[saas-late] composio not connected for {user_id}: {str(j.get('error'))[:80]}", file=sys.stderr)
        return []
    data = j.get("data") or {}
    items = data.get("items") or data.get("events") or []
    events = []
    for e in items:
        st = (e.get("start") or {})
        raw = st.get("dateTime")   # timed events only; skip all-day (date-only) — no leave time
        if not raw:
            continue
        try:
            start = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=now.tzinfo)
        except Exception:
            continue
        if now <= start <= now + timedelta(hours=horizon_h):
            events.append({"summary": e.get("summary") or "予定", "location": e.get("location"), "start": start})
    events.sort(key=lambda e: e["start"])
    return events


def send_sms(to, body):
    sid, token, frm = env("TWILIO_ACCOUNT_SID"), env("TWILIO_AUTH_TOKEN"), env("TWILIO_PHONE_NUMBER")
    data = urllib.parse.urlencode({"To": to, "From": frm, "Body": body}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("sid")


def send_renraku(stakeholders, summary, depart_hm):
    """報連相: notify matching stakeholders (SMS) that the subscriber may be late."""
    if not stakeholders:
        return 0
    sent = 0
    for st in stakeholders:
        match = (st.get("match") or "").strip()
        if not match or match not in (summary or ""):
            continue
        if st.get("channel") == "sms" and st.get("toField"):
            body = f"【自動通知】『{summary}』に遅れる可能性があります（{depart_hm}までに出発できていません）。追って本人より連絡します。— Anicca"
            try:
                send_sms(st["toField"], body); sent += 1
            except Exception as e:
                print(f"[saas-late] renraku sms failed: {e}", file=sys.stderr)
    return sent


def place_lateness_call(phone, ctx, name):
    base = URL_FILE.read_text().strip().rstrip("/")
    sid, token, frm = env("TWILIO_ACCOUNT_SID"), env("TWILIO_AUTH_TOKEN"), env("TWILIO_PHONE_NUMBER")
    twiml = f"{base}/twiml?{urllib.parse.urlencode({'name': name or 'there', 'mode': 'lateness', 'ctx': ctx})}"
    data = urllib.parse.urlencode({"To": phone, "From": frm, "Url": twiml, "Method": "GET"}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json", data=data, method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("sid")


def main():
    try:
        subs = supa_get("subscriber_profiles?status=eq.active"
                        "&select=user_id,phone,tz,location_lat,location_lon,location_vel,location_tst,"
                        "ics_url,calendar_provider,stakeholders,home_lat,home_lon,home_address")
    except Exception as e:
        print(f"[saas-late] supabase read failed: {e}", file=sys.stderr); return
    try:
        sent = json.loads(STATE.read_text())
    except Exception:
        sent = {}

    for s in subs:
        if not (s.get("location_lat") and s.get("location_tst")):
            continue
        tz = s.get("tz") or "Asia/Tokyo"
        now = datetime.now(ZoneInfo(tz))
        loc = {"lat": s["location_lat"], "lon": s["location_lon"], "vel": s.get("location_vel"), "tst": s["location_tst"]}
        # calendar source: Composio (real-time Google Calendar) preferred; ICS fallback (legacy)
        if s.get("calendar_provider") == "composio_gcal":
            events = fetch_composio_events(s["phone"], now)
        elif s.get("ics_url"):
            events = fetch_ics_events(s["ics_url"], now)
        else:
            continue
        # build departures (ETA from CURRENT location to each event)
        origin = f"{loc['lat']},{loc['lon']}"
        deps = []
        for e in events:
            tmin = gd.directions_travel_min(e["location"], origin) if e.get("location") else None
            from_est = tmin if tmin is not None else 45
            depart = e["start"] - timedelta(minutes=from_est + ARRIVE_EARLY)
            deps.append({"summary": e["summary"], "location": e.get("location"),
                         "startIso": e["start"].isoformat(), "departByIso": depart.isoformat(),
                         "travelMin": from_est, "attendees": []})
        deps.sort(key=lambda d: d["departByIso"])
        home = resolve_home(s)
        d = lc.decide(now, loc, deps, home=home)
        if d["action"] not in ("call", "nudge"):
            continue
        ev = d["event"]; key = f"{s['user_id']}|{ev['summary']}|{ev['departByIso']}|{d['action']}"
        if sent.get(key):
            continue
        depart_hm = datetime.fromisoformat(ev["departByIso"]).astimezone(ZoneInfo(tz)).strftime("%H:%M")
        if d["action"] == "call":
            ctx = f"次の予定『{ev['summary']}』へ、今いる場所から出ないと間に合わない（{depart_hm}までに出発）。"
            sid = place_lateness_call(s["phone"], ctx, None)
            n_renraku = send_renraku(s.get("stakeholders") or [], ev["summary"], depart_hm)
            print(f"[saas-late] call {s['user_id'][:8]} -> {ev['summary']} sid={sid} renraku={n_renraku}")
        else:
            print(f"[saas-late] nudge {s['user_id'][:8]} -> {ev['summary']} departBy {depart_hm}")
        sent[key] = now.strftime("%Y-%m-%dT%H:%M")

    STATE.write_text(json.dumps(sent, ensure_ascii=False))


if __name__ == "__main__":
    main()
