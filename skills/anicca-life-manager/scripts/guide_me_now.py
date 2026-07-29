#!/usr/bin/env python3
"""
guide_me_now — on-demand "where are you / get to your destination" call.

Reads Dais's LIVE location, reverse-geocodes it to a place name, computes the
real transit route + ETA to the destination (next calendar event, or an arg),
and places a realtime call where Anicca knows where he is and guides him there.

Usage:
  guide_me_now.py                 # destination = next calendar event
  guide_me_now.py "なかの芸能小劇場, 中野"   # explicit destination
"""
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # own scripts dir (self-contained skill)
import lateness_check as lc
import gcal_departures as gd

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


def env(n, d=""):
    m = re.search(rf"^{n}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else d)


def transit_route(origin, dest):
    """Google Directions transit: (minutes, human step summary)."""
    key = env("GOOGLE_API_KEY")
    q = urllib.parse.urlencode({"origin": origin, "destination": dest, "mode": "transit",
                                "language": "ja", "key": key})
    try:
        with urllib.request.urlopen(f"https://maps.googleapis.com/maps/api/directions/json?{q}", timeout=12) as r:
            j = json.loads(r.read().decode())
        leg = j["routes"][0]["legs"][0]
        mins = round(leg["duration"]["value"] / 60)
        steps = []
        for s in leg["steps"]:
            if s["travel_mode"] == "WALKING":
                steps.append("歩く")
            elif s["travel_mode"] == "TRANSIT":
                td = s["transit_details"]
                line = td["line"].get("short_name") or td["line"].get("name") or "電車"
                dep = td["departure_stop"]["name"]
                arr = td["arrival_stop"]["name"]
                steps.append(f"{dep}から{line}で{arr}")
        # compress consecutive 歩く
        summary = " → ".join([s for i, s in enumerate(steps) if not (s == "歩く" and i and steps[i-1] == "歩く")])
        return mins, summary
    except Exception as e:
        print(f"[guide] directions failed: {e}", file=sys.stderr)
        return None, None


def main():
    loc = lc.get_location()
    if not loc:
        print("no live location", file=sys.stderr); sys.exit(1)
    place = lc.reverse_geocode(loc) or "今いる場所"
    origin = f"{loc['lat']},{loc['lon']}"

    # destination: arg or next calendar event
    if len(sys.argv) > 1:
        dest = sys.argv[1]; summary = dest
    else:
        deps = gd.get_departures() if hasattr(gd, "get_departures") else gd.fetch_events()
        deps = [d for d in deps if d.get("location")]
        if not deps:
            print("no destination (no upcoming event with a location)", file=sys.stderr); sys.exit(1)
        dest = deps[0]["location"]; summary = deps[0]["summary"]

    # clean the event title for speech (strip emoji / [TENTATIVE] / venue suffix)
    clean = re.sub(r"[\U0001F000-\U0001FAFF☀-➿]", "", summary)
    clean = re.sub(r"\[[^\]]*\]", "", clean).split("@")[0].strip(" 　-")
    mins, route = transit_route(origin, dest)
    if mins is None:  # transit returned nothing -> fall back to the engine's estimator
        mins = gd.directions_travel_min(dest, origin)
    eta = f"約{mins}分" if mins else "それなりの時間"
    route_str = f"ルートは {route}。" if route else ""
    ctx = (f"今ダイスは{place}にいる。目的地は『{clean}』({dest})。"
           f"今いる場所からそこまで{eta}。{route_str}"
           f"今いる場所を起点に、最初の一歩(どの駅へ歩くか/どの線に乗るか)から具体的に案内して、迷わず着けるよう導いて。")
    print("CTX:", ctx)
    sid = lc.place_lateness_call(ctx)
    print(f"[guide] placed call sid={sid} from={place} to={dest} eta={mins}")


if __name__ == "__main__":
    main()
