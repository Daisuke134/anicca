#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
from scripts.lib.storage import load_json, save_json
from scripts.lib.output import print_header, print_kv
from scripts.lib.schema import now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update TikTok account profile.")
    parser.add_argument("--niche", default="", help="Account niche")
    parser.add_argument("--audience", default="", help="Target audience")
    parser.add_argument("--goal", default="", help="Primary goal")
    parser.add_argument("--pillars", default="", help='Comma-separated content pillars, e.g. "stories,education,hot takes"')
    parser.add_argument("--tone", default="", help="Voice or tone")
    parser.add_argument("--notes", default="", help="Additional notes")

    args = parser.parse_args()

    profile = load_json("profile")

    if args.niche:
        profile["niche"] = args.niche.strip()
    if args.audience:
        profile["target_audience"] = args.audience.strip()
    if args.goal:
        profile["primary_goal"] = args.goal.strip()
    if args.pillars:
        profile["pillars"] = [p.strip() for p in args.pillars.split(",") if p.strip()]
    if args.tone:
        profile["tone"] = args.tone.strip()
    if args.notes:
        profile["notes"] = args.notes.strip()

    profile["updated_at"] = now_iso()
    save_json("profile", profile)

    print_header("✅ TIKTOK ACCOUNT PROFILE UPDATED")
    print_kv("Niche", profile.get("niche", ""))
    print_kv("Audience", profile.get("target_audience", ""))
    print_kv("Goal", profile.get("primary_goal", ""))
    print_kv("Pillars", ", ".join(profile.get("pillars", [])))
    print_kv("Tone", profile.get("tone", ""))
    print_kv("Updated At", profile.get("updated_at", ""))


if __name__ == "__main__":
    main()
