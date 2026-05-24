#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
from scripts.lib.storage import load_json, save_json
from scripts.lib.schema import make_video_log
from scripts.lib.output import print_header, print_kv


def non_negative_int(value: str) -> int:
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError("Value must be non-negative.")
    return ivalue


def completion_percent(value: str) -> float:
    fvalue = float(value)
    if fvalue < 0 or fvalue > 100:
        raise argparse.ArgumentTypeError("Completion rate must be between 0 and 100.")
    return fvalue


def main() -> None:
    parser = argparse.ArgumentParser(description="Log TikTok performance metrics locally.")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--topic", default="", help="Topic")
    parser.add_argument("--angle", default="", help="Angle")
    parser.add_argument("--hook-type", default="", help="Hook type used")
    parser.add_argument("--views", required=True, type=non_negative_int, help="Views")
    parser.add_argument("--likes", type=non_negative_int, default=0, help="Likes")
    parser.add_argument("--comments", type=non_negative_int, default=0, help="Comments")
    parser.add_argument("--shares", type=non_negative_int, default=0, help="Shares")
    parser.add_argument("--completion", required=True, type=completion_percent, help="Completion rate percent")
    parser.add_argument("--notes", default="", help="Notes")

    args = parser.parse_args()

    analytics = load_json("analytics")
    entry = make_video_log(
        video_title=args.title.strip(),
        topic=args.topic.strip(),
        angle=args.angle.strip(),
        hook_type=args.hook_type.strip(),
        views=args.views,
        likes=args.likes,
        comments=args.comments,
        shares=args.shares,
        completion_rate=args.completion,
        notes=args.notes.strip(),
    )

    analytics["videos"].append(entry)
    save_json("analytics", analytics)

    print_header("✅ PERFORMANCE LOGGED")
    print_kv("ID", entry["id"])
    print_kv("Title", entry["video_title"])
    print_kv("Views", str(entry["views"]))
    print_kv("Completion %", str(entry["completion_rate"]))
    print_kv("Logged At", entry["logged_at"])


if __name__ == "__main__":
    main()
