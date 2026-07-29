#!/usr/bin/env python3
"""transit_lookup — geocode destination + transitous /api/v2/plan = itinerary.

Used by realtime_guide and lateness_check. Works identically in:
  - Anicca local (= mac mini, ~/.local/state/life-manager, this script invoked direct)
  - Anicca cloud (= Daytona sandbox per paying user, same script in $ANICCA_HOME)

BP cite:
  - https://github.com/public-transport/transitous (FOSS Japan-included)
  - https://api.transitous.org/api/v2/plan (LIVE public API)
  - Google Geocoding API (developers.google.com/maps/documentation/geocoding)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))

LIFE_MANAGER_HOME = Path(os.environ.get(
    "LIFE_MANAGER_HOME", str(Path.home() / ".local" / "state" / "life-manager"),
))
ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(LIFE_MANAGER_HOME)))
ENV_PATH = ANICCA_HOME / ".env"

# Load env (.env file) for GOOGLE_API_KEY etc.
if ENV_PATH.exists():
    for ln in ENV_PATH.read_text().splitlines():
        if "=" in ln and not ln.strip().startswith("#"):
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_ADDRESS_RE = __import__("re").compile(
    r"〒?\s*(\d{3}[-－]?\d{4})?\s*"
    r"(東京都|大阪府|京都府|北海道|"
    r"(?:神奈川|埼玉|千葉|茨城|栃木|群馬|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|"
    r"滋賀|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|"
    r"熊本|大分|宮崎|鹿児島|沖縄|青森|岩手|宮城|秋田|山形|福島)県)"
    r"[^、。\s]{3,60}"
)


def _google_geocode_raw(query: str, key: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode({
        "address": query, "language": "ja", "region": "jp", "key": key,
    })
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def _firecrawl_search_address(query: str, *, key: str) -> str | None:
    """Use Firecrawl search API to find a Japanese postal address for an
    ambiguous venue name (e.g. 'MUIT', 'itoushika yotsuya', 'muit').

    Returns the first plausible address string found in result snippets,
    or None if nothing matches. Pattern: optional 〒xxx-xxxx + 都道府県 + suffix.

    Works in BOTH:
      - LOCAL  (mac mini): same FIRECRAWL_API_KEY in ~/.local/state/life-manager/.env
      - CLOUD  (Daytona sandbox per user): same env, no CLI dependency
    """
    url = "https://api.firecrawl.dev/v1/search"
    body = json.dumps({"query": f"{query} 住所", "limit": 5}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    items = data.get("data") or data.get("web") or []
    for item in items[:10]:
        snippet = " ".join(filter(None, [
            item.get("description") or "",
            item.get("title") or "",
            item.get("markdown") or "",
            item.get("content") or "",
        ]))
        m = _ADDRESS_RE.search(snippet)
        if m:
            # Compose: postal (optional) + prefecture + locality
            return m.group(0).strip()
    return None


def geocode(query: str, *, key: str | None = None) -> tuple[float, float, str]:
    """address string -> (lat, lon, formatted_address).

    Chain (BP cite: spec §6 §11.5):
      1. Google Geocoding direct (= "銀座駅" 等 明確 名 で 即解決)
      2. on ZERO_RESULTS: Firecrawl search "<query> 住所"
         → extract first 〒/都道府県 address from snippets
         → re-feed to Google Geocoding
      3. raise if both fail

    Resolves "MUIT" → 中野セントラルパークサウス → lat/lon.
    """
    key = key or os.environ.get("GOOGLE_API_KEY_DIRECTIONS") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY (or *_DIRECTIONS) not set")

    data = _google_geocode_raw(query, key)
    if data.get("status") == "OK" and data.get("results"):
        best = data["results"][0]
        return best["geometry"]["location"]["lat"], best["geometry"]["location"]["lng"], best["formatted_address"]

    # Fallback: Firecrawl search → address extract → re-geocode.
    fc_key = os.environ.get("FIRECRAWL_API_KEY")
    if fc_key:
        addr = _firecrawl_search_address(query, key=fc_key)
        if addr:
            data2 = _google_geocode_raw(addr, key)
            if data2.get("status") == "OK" and data2.get("results"):
                best = data2["results"][0]
                return (
                    best["geometry"]["location"]["lat"],
                    best["geometry"]["location"]["lng"],
                    f"{best['formatted_address']} (= Firecrawl resolved '{query}' → '{addr}')",
                )

    raise RuntimeError(
        f"geocode failed for {query!r}: Google={data.get('status')}, Firecrawl={'no match' if fc_key else 'no API key'}"
    )


def plan_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    arrive_by: datetime,
    *,
    mode: str = "TRANSIT,WALK",
) -> dict[str, Any]:
    """Call transitous MOTIS planner. Returns first itinerary as dict.

    Itinerary structure (subset we use):
      {
        "duration": seconds,
        "startTime": iso8601 UTC,
        "endTime": iso8601 UTC,
        "transfers": int,
        "legs": [
          {
            "mode": "WALK"|"TRANSIT"|"BUS"|"RAIL"|...,
            "duration": seconds,
            "startTime": iso8601 UTC,
            "endTime": iso8601 UTC,
            "from": {"name": str, "lat": float, "lon": float},
            "to":   {"name": str, "lat": float, "lon": float},
            "routeShortName": str | None,
            "routeLongName":  str | None,
            "headsign":       str | None,
            "agencyName":     str | None,
            "intermediateStops": [...]   # optional
          }
        ]
      }
    """
    url = "https://api.transitous.org/api/v2/plan?" + urllib.parse.urlencode({
        "fromPlace": f"{origin_lat},{origin_lon}",
        "toPlace":   f"{dest_lat},{dest_lon}",
        "time":      arrive_by.isoformat(),
        "arriveBy":  "true",
        "mode":      mode,
    })
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    its = data.get("itineraries", [])
    if not its:
        raise RuntimeError(f"no itinerary: {data.get('debugOutput', {})}")
    return its[0]


def build_itinerary(query: str, origin_lat: float, origin_lon: float, arrive_by: datetime) -> dict[str, Any]:
    """Composed pipeline: query -> geocode -> plan_route -> persistable dict."""
    dlat, dlon, dformatted = geocode(query)
    it = plan_route(origin_lat, origin_lon, dlat, dlon, arrive_by)
    return {
        "query":             query,
        "dest_address":      dformatted,
        "dest_lat":          dlat,
        "dest_lon":          dlon,
        "arrive_by_iso":     arrive_by.isoformat(),
        "origin_lat":        origin_lat,
        "origin_lon":        origin_lon,
        "itinerary":         it,
        "created_at":        int(time.time()),
    }


# ─── CLI for ad-hoc usage / testing ──────────────────────────────
def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="transit_lookup CLI")
    ap.add_argument("--from-lat", type=float, required=True)
    ap.add_argument("--from-lon", type=float, required=True)
    ap.add_argument("--to", required=True, help="destination query (e.g. '銀座駅')")
    ap.add_argument("--arrive-by", required=True, help="ISO datetime with TZ (e.g. 2026-06-08T09:00+09:00)")
    args = ap.parse_args()
    arr = datetime.fromisoformat(args.arrive_by)
    res = build_itinerary(args.to, args.from_lat, args.from_lon, arr)
    it = res["itinerary"]
    dur = it["duration"]
    st = datetime.fromisoformat(it["startTime"].replace("Z", "+00:00")).astimezone(JST)
    et = datetime.fromisoformat(it["endTime"].replace("Z", "+00:00")).astimezone(JST)
    print(f"DEST: {res['dest_address']}")
    print(f"  ({res['dest_lat']}, {res['dest_lon']})")
    print(f"ITIN: {dur//60} 分、 出発 {st.strftime('%H:%M')} 到着 {et.strftime('%H:%M')}、 乗換 {it.get('transfers',0)}")
    for leg in it.get("legs", []):
        mode = leg.get("mode", "?")
        ld = leg.get("duration", 0)
        f = leg.get("from", {}).get("name", "?")
        t = leg.get("to", {}).get("name", "?")
        rt = leg.get("routeShortName") or leg.get("routeLongName") or ""
        hs = leg.get("headsign", "")
        if mode == "WALK":
            print(f"  🚶 徒歩 {ld//60} 分: {f} → {t}")
        else:
            print(f"  🚇 {rt} ({hs}): {f} → {t}  ({ld//60} 分)")


if __name__ == "__main__":
    _cli()
