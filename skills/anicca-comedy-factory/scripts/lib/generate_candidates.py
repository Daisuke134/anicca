#!/usr/bin/env python3
"""generate_candidates.py — city/date から open mic candidates JSON を生成。

Hardcoded venue DB (Tokyo / SF / LA) + 将来 firecrawl で enrichment。
出力: data/live-events/<city>-<date>.json

Phase 1 実装は hardcoded directory のみ。将来 lu.ma / sfstandup / mutiny を
firecrawl scrape して直近イベント検出するロジックを足す。

Usage:
  generate_candidates.py --city sf --date 2026-05-19 --out path.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path


# Hardcoded SF / Tokyo / LA Tuesday open mic directory (verified 2026-05-08).
DIRECTORY = {
    "sf": [
        {
            "rank": 1,
            "name": "OMG! Tuesday Open Mic @ Mutiny Radio",
            "venue": "Mutiny Radio",
            "address": "2781 21st Street, San Francisco, CA 94110 (Mission)",
            "weekday": "Tuesday (recurring)",
            "signup_method": "in_person_at_door",
            "signup_time": "Arrive 30-60 min early",
            "set_length_min": 5,
            "cost": "free for performers",
            "host_{{profile.lateness.stakeholders.channel}}": "mutinyradiofm@gmail.com",
            "host_phone": "(415) 550-0511",
            "eventbrite": "https://www.eventbrite.com/e/omg-tuesday-open-mic-tickets-648215930297",
            "schedule_page": "https://mutinyradio.fm/schedule",
            "notes": "Pam Benjamin runs the Mutiny comedy ecosystem. Email host 1 week ahead.",
        },
        {
            "rank": 2,
            "name": "The Lost Church Open Mic",
            "venue": "The Lost Church",
            "address": "65 Capp Street, San Francisco, CA 94103",
            "weekday": "Variable",
            "signup_method": "online_form_or_{{profile.lateness.stakeholders.channel}}",
            "calendar_url": "https://www.thelostchurch.com/calendar",
            "set_length_min": 5,
            "cost": "free for performers",
            "notes": "501(c)(3) arts non-profit. Check calendar 1-2 weeks ahead.",
        },
        {
            "rank": 3,
            "name": "Cynic Cave Open Mic",
            "venue": "Stork Club / Cynic Cave Oakland",
            "address": "2330 Telegraph Ave, Oakland, CA 94612",
            "weekday": "Tuesday (recurring weekly)",
            "signup_method": "in_person_at_door",
            "signup_time": "Sign-up 7:30pm, show 8pm",
            "set_length_min": 4,
            "cost": "free for performers",
            "notes": "Most reliable Tuesday open mic in the East Bay. 20 min BART from SF.",
        },
        {
            "rank": 4,
            "name": "Cheaper Than Therapy Open Mic",
            "venue": "Shelton Theater",
            "address": "533 Sutter St, San Francisco, CA 94102",
            "weekday": "Variable",
            "signup_method": "{{profile.lateness.stakeholders.channel}}_host",
            "set_length_min": 3,
            "cost": "free for performers",
            "notes": "Small black box theater in Union Square. Email host.",
        },
    ],
    "tokyo": [
        {
            "rank": 1,
            "name": "Tokyo Comedy Bar Open Mic",
            "venue": "Tokyo Comedy Bar",
            "address": "渋谷区道玄坂 (Dogenzaka)",
            "weekday": "Tuesday + Wednesday",
            "signup_method": "online_form",
            "signup_url": "https://www.tokyocomedybar.com/openmic",
            "set_length_min": 5,
            "cost": "free for performers",
            "notes": "Tokyo's main English-language comedy venue. JP+EN sets both welcome.",
        },
        {
            "rank": 2,
            "name": "Stand Up Tokyo Open Mic",
            "venue": "Good Heavens British Bar",
            "address": "下北沢 / Shimokitazawa",
            "weekday": "Sunday (also Tue rotation)",
            "signup_method": "in_person_at_door",
            "set_length_min": 5,
            "cost": "free",
            "notes": "Long-running English open mic. JP-bilingual welcome.",
        },
    ],
    "la": [
        {
            "rank": 1,
            "name": "The Comedy Store Belly Room Open Mic",
            "venue": "The Comedy Store",
            "address": "8433 W Sunset Blvd, West Hollywood, CA 90069",
            "weekday": "Sunday (Potluck)",
            "signup_method": "lottery",
            "set_length_min": 3,
            "cost": "free",
        },
        {
            "rank": 2,
            "name": "Westside Comedy Theater Open Mic",
            "venue": "Westside Comedy Theater",
            "address": "1323 3rd St Promenade, Santa Monica, CA 90401",
            "weekday": "Multiple",
            "signup_method": "online_form",
            "signup_url": "https://www.westsidecomedy.com/",
            "set_length_min": 5,
            "cost": "free",
        },
    ],
}


def primary_recommendation(city: str, weekday: str) -> dict:
    cands = DIRECTORY.get(city, [])
    # Prefer rank 1 if its weekday matches; else first one whose weekday matches; else rank 1.
    for c in cands:
        if c["rank"] == 1 and weekday.lower() in c["weekday"].lower():
            return {"venue": c["name"], "rationale": c["notes"], "fallback": cands[1]["name"] if len(cands) > 1 else ""}
    for c in cands:
        if weekday.lower() in c["weekday"].lower():
            return {"venue": c["name"], "rationale": c["notes"], "fallback": cands[0]["name"]}
    if cands:
        return {"venue": cands[0]["name"], "rationale": cands[0]["notes"], "fallback": cands[1]["name"] if len(cands) > 1 else ""}
    return {"venue": "(none)", "rationale": "no candidates", "fallback": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    weekday = datetime.date.fromisoformat(args.date).strftime("%A")
    cands = [c for c in DIRECTORY.get(args.city, []) if weekday.lower() in c["weekday"].lower()] \
        or DIRECTORY.get(args.city, [])
    primary = primary_recommendation(args.city, weekday)

    out = {
        "city": args.city,
        "date": args.date,
        "weekday": weekday,
        "researched_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "candidates": cands,
        "primary_recommendation": primary,
        "dais_action_items": [
            f"1. {primary['venue']} に 1 週間前 (1 week ahead) {{profile.lateness.stakeholders.channel}}/contact",
            f"2. 5-min set 準備 (skit-deliver-daily が cron で配信中)",
            f"3. 当日早めに到着 → door sign-up",
            f"4. set 録画 → post-live-process cron で Remotion 編集 + Postiz TikTok",
        ],
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"✅ generated {args.out}")


if __name__ == "__main__":
    main()
