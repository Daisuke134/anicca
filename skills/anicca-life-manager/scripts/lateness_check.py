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
DEPART_SCRIPT = Path.home() / ".openclaw" / "skills" / "anicca-life-manager" / "scripts" / "gcal_departures.py"
LOCATION_STATE_DIR = Path.home() / ".openclaw" / "state" / "location"

# Routine event summaries that always happen at home — when gcal location is empty,
# auto-resolve to profile.identity.homeAddress instead of letting the LLM fabricate
# a station name (the "Shinagawa 駅 行って sleep" bug, 2026-05-31).
ROUTINE_AT_HOME_PATTERNS = (
    "sleep", "睡眠", "就寝", "寝る",
    "wake", "起床",
    "meditat", "瞑想", "座禅",
    "breakfast", "朝食", "朝ごはん",
    "lunch", "昼食", "昼ごはん",
    "dinner", "夕食", "晩ごはん",
    "meal", "食事",
)


def is_routine_at_home(summary: str) -> bool:
    s = (summary or "").lower()
    return any(p in s for p in ROUTINE_AT_HOME_PATTERNS)


ADDR_PATTERNS = (
    re.compile(r"(〒\d{3}-\d{4}\s*[^,;()\n　]+)"),
    re.compile(r"((?:北海道|東京都|京都府|大阪府|[^\s]{1,3}県)[^\s,;()\n　]{2,40})"),
    re.compile(r"((?:NAIST|MUIT|MUFG)\s+〒?\d{0,3}-?\d{0,4}\s*[^\s,;()\n　]+)"),
    re.compile(r"([一-龯ぁ-んァ-ヶ]{2,8}駅)"),
)


def _extract_address(text):
    if not text:
        return None
    for pat in ADDR_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def resolve_event_destination(event):
    """Return (address, kind) for the event's destination.
      kind = 'explicit'           → gcal event had a location field
             'home_routine'       → routine event (sleep/wake/etc), forced to home
             'summary_extracted'  → regex-pulled JP address from summary/desc
             'unknown'            → no location; LLM must ASK, not fabricate
    """
    loc = (event or {}).get("location") or ""
    if loc.strip():
        return loc.strip(), "explicit"
    if is_routine_at_home(event.get("summary", "")):
        return prof.home_address(), "home_routine"
    extracted = (
        _extract_address(event.get("summary", ""))
        or _extract_address(event.get("description", ""))
    )
    if extracted:
        return extracted, "summary_extracted"
    return None, "unknown"

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
STALE_MIN = int(os.environ.get("LATE_STALE_MIN", "10"))      # Telegram Live Location updates 1-5s while sharing; >10m stale = bot died or user stopped sharing


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


def arrival_radius_for(dest_addr, default=400):
    """Event-type aware "you have arrived" threshold (meters)."""
    if not dest_addr:
        return default
    a = dest_addr
    if "駅" in a:
        return 200            # station — within walking distance of any platform
    if any(k in a for k in ("新宿区南元町", )):
        return 100            # home  ─ matched by string contains
    if any(k in a for k in ("空港", "Airport", "airport")):
        return 800            # airport terminal — wide
    if any(k in a for k in ("〒", "丁目", "番地")):
        return 80             # specific street address — building-level
    return default


def decide(now, location, departures, home=None, home_radius_m=None, dest=None, arrive_radius_m=400):
    """Pure decision. Returns dict {action, reason, event}.
    action in {'call', 'ok', 'no-events', 'no-location', 'stale-location'}.
    home=(lat,lon) overrides module HOME_*; dest=(lat,lon) of the next event lets us
    detect 'already arrived' (so we don't nag once he's there)."""
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

    # STALE-LOCATION RULE (Telegram Live Location source, 2026-05-31).
    # Telegram publishes every 1-5s while user is sharing Live Location.
    # Stale > STALE_MIN → bot died OR user stopped sharing.
    # NEVER silent-skip (causes missed events). Always CALL to confirm where user is.
    # Trade-off: occasional false call vs guaranteed miss. Dais 厳命 = 誤発火許容.
    if age_min > STALE_MIN:
        return {"action": "call",
                "reason": f"location {int(age_min)}m stale — Telegram Live Location may be off; calling to confirm where Dais is",
                "event": nxt}

    # UNIFIED model: departBy is computed from his CURRENT location's ETA (not home),
    # so this works wherever he is. "Leave now" = it's time to leave THIS spot to
    # arrive on time. (gcal_departures sets travelMin/departBy from current_origin.)
    travel = nxt.get("travelMin")

    # Already at / near the destination -> nothing to do. (Use real distance to dest,
    # NOT travelMin, since travelMin=0 also happens for 'baked' 出発: events.)
    if dest:
        dist_dest = haversine_m(dest[0], dest[1], location["lat"], location["lon"])
        if dist_dest <= arrive_radius_m:
            return {"action": "ok", "reason": f"arrived ({int(dist_dest)}m from dest)", "event": nxt}

    # Actively moving toward it (on foot/train). If departBy already passed he's
    # running behind → fire a realtime GUIDE call (Google-Maps-style "you won't make
    # it, hurry"). Otherwise he's on track → reassess next tick.
    if moving:
        if mins <= 0:
            return {"action": "guide",
                    "reason": f"移動中だが departBy を {int(-mins)}m 超過 — 間に合わせるため急かす",
                    "event": nxt}
        return {"action": "ok", "reason": f"en route, moving (vel={vel}) — 間に合う見込み", "event": nxt}

    # Stationary + fresh: if it's time to leave from where he is now, call & guide.
    if mins <= LEAD_MIN:
        return {"action": "call",
                "reason": f"departBy in {int(mins)}m — must leave now (travel {travel}m from current location)",
                "event": nxt}
    if mins <= NUDGE_MIN:
        return {"action": "nudge",
                "reason": f"departBy in {int(mins)}m — get ready to leave soon",
                "event": nxt}
    return {"action": "ok",
            "reason": f"departBy in {int(mins)}m, travel {travel}m, moving={moving}",
            "event": nxt}


# ---- IO ----
def get_location():
    """Read latest Telegram Live Location fix from ~/.openclaw/state/location/<user_id>.json.

    Bot writes one file per user (key = telegram user id). If multiple files exist
    we take the freshest. None = no Live Location sharing active → upstream calls
    will trigger a stale-location call asking user to /share location.

    Freshness semantics:
      tst         = the *measurement* timestamp Telegram tagged on this fix
      received_at = wall-clock time the bot last saved a signal
    For "is the share alive?" we use received_at (= bot got a message), because
    msg.edit_date can be stale or None on edited_message live updates.
    We expose received_at as the canonical age in 'tst' so the rest of the code
    treats stale = bot stopped getting signals.
    """
    if not LOCATION_STATE_DIR.exists():
        return None
    files = sorted(LOCATION_STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        rec = json.loads(files[0].read_text())
        signal_ts = rec.get("received_at") or rec["tst"]
        return {
            "lat": rec["lat"],
            "lon": rec["lon"],
            "tst": signal_ts,            # = received_at, the right thing for staleness
            "measured_at": rec["tst"],   # raw Telegram measurement timestamp (info only)
            "vel": None,
            "acc": rec.get("accuracy_m"),
        }
    except Exception:
        return None


def geocode_place(address):
    """Address/place string -> (lat, lon) for arrival detection. None on failure."""
    key = env("GOOGLE_API_KEY")
    if not (address and key):
        return None
    try:
        q = urllib.parse.urlencode({"address": address, "key": key, "language": "ja"})
        with urllib.request.urlopen(f"https://maps.googleapis.com/maps/api/geocode/json?{q}", timeout=8) as r:
            j = json.loads(r.read().decode())
        loc = j["results"][0]["geometry"]["location"]
        return (loc["lat"], loc["lng"])
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
        # prefer ward + neighbourhood (新宿区 + 南元町) over full address
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
    """Fire the lateness-mode call.

    New (#20, 2026-05-29): goes through the Pipecat outbound /dialout endpoint
    instead of the old imokenet bridge. The persona + ctx splicing happens inside
    the bot (see anicca-oss-pipecat/skills/anicca-phone/outbound/bot.py).

    Source of the dial-out endpoint:
      1. ANICCA_PHONE_DIALOUT_URL env var (preferred — set by launchd / cron config)
      2. ~/.openclaw/state/anicca_phone_url.txt (matches the imokenet URL_FILE pattern)
      3. http://127.0.0.1:7860/dialout (local default during dev)
    """
    base = (
        os.environ.get("ANICCA_PHONE_DIALOUT_URL")
        or _read_url_file(Path.home() / ".openclaw" / "state" / "anicca_phone_url.txt")
        or "http://127.0.0.1:7860"
    ).rstrip("/")
    to = os.environ.get("LATE_PHONE") or prof.phone()
    from_number = env("TWILIO_PHONE_NUMBER") or "+13366526842"
    body = json.dumps({
        "to_number": to,
        "from_number": from_number,
        "mode": "lateness",
        "ctx": ctx,
        "name": prof.name(),
    }).encode()
    req = urllib.request.Request(
        f"{base}/dialout",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode())
    return resp.get("call_sid")


def _read_url_file(p: Path) -> str:
    try:
        return p.read_text().strip()
    except Exception:
        return ""


def slack(text):
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": env("SLACK_CHANNEL_ID"), "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {env('SLACK_BOT_TOKEN')}"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"[late] slack failed: {e}", file=sys.stderr)


def _in_quiet_hours(now):
    """Return True if `now` falls inside the user's quiet window.

    profile.alarm.quietHoursStart / quietHoursEnd are "HH:MM" strings (JST).
    Window can cross midnight (e.g. 23:30 -> 05:30).
    Defaults: no quiet hours = always active.
    """
    try:
        start = prof.get("alarm.quietHoursStart", "")
        end = prof.get("alarm.quietHoursEnd", "")
    except Exception:
        return False
    if not start or not end:
        return False
    try:
        sh, sm = (int(x) for x in start.split(":"))
        eh, em = (int(x) for x in end.split(":"))
    except Exception:
        return False
    cur_min = now.hour * 60 + now.minute
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    if start_min <= end_min:                # same-day window (e.g. 13:00-15:00)
        return start_min <= cur_min < end_min
    return cur_min >= start_min or cur_min < end_min  # cross-midnight


def main():
    now = datetime.now(JST)
    if _in_quiet_hours(now):
        # Quiet hours are how the user tells us "I'm asleep / leave me alone".
        # Critical events still trigger (handled inside decide), but the
        # default routine-event polling is silenced here to save Twilio cost
        # and not wake the user mid-sleep.
        print(json.dumps({"action": "quiet-hours", "reason": "user is asleep"}, ensure_ascii=False))
        return
    loc_now = get_location()
    deps = get_departures()
    dest_addr, dest_kind = (None, "unknown")
    if deps:
        dest_addr, dest_kind = resolve_event_destination(deps[0])
    dest = geocode_place(dest_addr) if dest_addr else None
    radius = arrival_radius_for(dest_addr)
    d = decide(now, loc_now, deps, dest=dest, arrive_radius_m=radius)
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

    if d["action"] == "guide":
        # Moving but behind schedule → realtime Google-Maps-style hurry-up call.
        e = d["event"]
        guide_addr, _ = resolve_event_destination(e)
        try:
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "guide_me_now.py"), guide_addr or ""], timeout=120)
            slack(f"🧭 移動中催促コール: {d['reason']} → {e['summary']}")
            print(f"[late] guide call fired for {e['summary']}")
        except Exception as ex:
            print(f"[late] guide failed: {ex}")

    if d["action"] == "call":
        e = d["event"]
        # Race lock: a single 5-min cron tick should not fire two POST /dialouts
        # for the same event. Also prevents 'overlapping cron x cron' (= cron
        # 06:50 still running when 06:55 fires) from double-ringing the phone.
        # We keep a per-event timestamp; entries older than RACE_LOCK_SEC are
        # treated as expired (= next tick can legitimately call again).
        lock_path = Path(__file__).resolve().parent.parent / "state" / "active_call_loop.json"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            locks = json.loads(lock_path.read_text())
        except Exception:
            locks = {}
        RACE_LOCK_SEC = int(os.environ.get("LATE_RACE_LOCK_SEC", "60"))
        lock_key = f"{e['summary']}|{e['departByIso']}"
        last_ts = locks.get(lock_key, 0)
        if (now.timestamp() - last_ts) < RACE_LOCK_SEC:
            print(json.dumps({
                "action": "ok",
                "reason": f"race-lock active ({int(now.timestamp() - last_ts)}s ago)",
                "event_summary": e["summary"],
            }, ensure_ascii=False))
            return
        locks[lock_key] = int(now.timestamp())
        # Trim stale entries so the file doesn't grow forever
        cutoff = now.timestamp() - 86400
        locks = {k: v for k, v in locks.items() if v >= cutoff}
        lock_path.write_text(json.dumps(locks, ensure_ascii=False, indent=2))

        start = datetime.fromisoformat(e["startIso"]).astimezone(JST).strftime("%H:%M")
        depart_dt = datetime.fromisoformat(e["departByIso"]).astimezone(JST)
        depart = depart_dt.strftime("%H:%M")
        place = reverse_geocode(loc_now) if loc_now else None
        place = place or "現在地不明"
        travel = e.get("travelMin")
        travel_str = f"そこから約{travel}分、" if travel else ""

        # Resolve destination explicitly. Routine events at home get
        # profile.home_address() so the LLM never fabricates a station name
        # (the "Shinagawa 駅 for sleep" bug, Dais 2026-05-31).
        dest_addr, dest_kind = resolve_event_destination(e)

        # Pre-compute the actual transit route via Google Maps Web. Skip when
        # destination unknown (would just hallucinate). For home_routine we look
        # it up against the home address.
        route_block = ""
        if loc_now and dest_addr:
            try:
                origin_str = f"{loc_now['lat']},{loc_now['lon']}"
                r = subprocess.run(
                    [sys.executable,
                     str(Path(__file__).resolve().parent / "route_lookup.py"),
                     "--origin", origin_str,
                     "--destination", dest_addr],
                    capture_output=True, text=True, timeout=45,
                )
                if r.returncode == 0:
                    route = json.loads(r.stdout)
                    if route.get("ok") and route.get("summary"):
                        bits = [f"推奨ルート(Google Maps): {route['summary']}"]
                        if route.get("duration_min"):
                            bits.append(f"所要 {route['duration_min']}分")
                        if route.get("fare_yen"):
                            bits.append(f"運賃 {route['fare_yen']}円")
                        if route.get("departure_time"):
                            bits.append(f"次発 {route['departure_time']}")
                        route_block = "。" + "、".join(bits)
            except Exception as exn:
                print(f"[late] route_lookup failed: {exn}", file=sys.stderr)

        # Destination phrasing — never let the LLM guess.
        if dest_kind == "explicit":
            dest_line = f"、場所は {dest_addr}"
        elif dest_kind == "home_routine":
            dest_line = f"、場所は自宅 ({dest_addr})"
        else:
            dest_line = (
                "、場所は Google カレンダーに未記入。"
                " ダイスに直接『どこでやる予定?』と聞いてから案内すること。"
                " 駅名や住所を勝手に推測してはいけない"
            )

        # Action phrasing depends on event type — home-routine events don't
        # require leaving anywhere; they require waking up / starting the
        # activity. Travel-required events require physical movement.
        if dest_kind == "home_routine":
            ev_kind = (e.get("summary") or "").lower()
            if any(k in ev_kind for k in ("sleep", "睡眠", "就寝")):
                action_line = (
                    f"。今は寝る時刻。 まだ起きてるなら寝床へ行くよう促す。"
                    f" {depart} までに横にならないとパフォーマンス落ちる。"
                )
            elif any(k in ev_kind for k in ("wake", "起床", "🛏")):
                action_line = (
                    f"。これは起床コール。 まだ寝てるなら今すぐ起き上がるよう促す。"
                    f" 上半身を起こす → 水を飲む → 顔を洗う、 ステップごと案内。"
                )
            elif any(k in ev_kind for k in ("meditat", "瞑想", "座禅")):
                action_line = (
                    f"。瞑想開始時刻が近い。 自宅にいるなら瞑想スペースへ。"
                    f" すでに座ってるなら呼吸に集中するよう促す。"
                )
            elif any(k in ev_kind for k in ("running", "🏃", "jog")):
                action_line = (
                    f"。ランニング開始時刻。 自宅にいるなら靴履いて玄関へ。"
                    f" 今出れば {start} に走り始められる。"
                )
            elif any(k in ev_kind for k in ("meal", "breakfast", "朝食", "朝ごはん",
                                            "lunch", "昼食", "昼ごはん",
                                            "dinner", "夕食", "晩ごはん", "食事")):
                action_line = (
                    f"。食事時刻。 何を食べる予定か聞いて、 ステップを促す。"
                )
            else:
                action_line = (
                    f"。自宅で行う予定。 場所は自宅、 移動は不要。"
                    f" 何を始めるべきか聞いて促す。"
                )
            ctx = (
                f"次の予定『{e['summary']}』は {start} 開始"
                + dest_line
                + f"。今ダイスは{place}にいる"
                + action_line
                + " 自宅にいない場合は自宅へ戻るよう促す (= 自宅予定なので)。"
            )
        else:
            ctx = (
                f"次の予定『{e['summary']}』は {start} 開始"
                + dest_line
                + f"。今ダイスは{place}にいて、{travel_str}{depart} までに出ないと間に合わない"
                + route_block
                + "。出発地は『家』ではなく上記の現在地。そこから出発するよう案内する。"
                + " 場所が自宅なら自宅へ戻る案内、explicit なら最寄駅まで歩いて電車で。"
                + " ルート情報は Google Maps の実データ — 駅名と線名はそのまま使い、"
                + " 自分の記憶で言い換えない。"
            )
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
