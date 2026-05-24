#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
from scripts.lib.storage import load_json
from scripts.lib.output import print_header


def matches(item: dict, item_type: str, topic: str, tag: str) -> bool:
    if item_type and item.get("type") != item_type:
        return False
    if topic and topic.lower() not in item.get("topic", "").lower():
        return False
    if tag and tag.lower() not in [t.lower() for t in item.get("tags", [])]:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="List saved TikTok content assets.")
    parser.add_argument("--type", default="", choices=["", "idea", "hook", "script", "caption", "note"], help="Filter by type")
    parser.add_argument("--topic", default="", help="Filter by topic contains")
    parser.add_argument("--tag", default="", help="Filter by tag")
    parser.add_argument("--limit", type=int, default=20, help="Max items to show")

    args = parser.parse_args()

    bank = load_json("content_bank")
    items = [item for item in bank.get("items", []) if matches(item, args.type, args.topic, args.tag)]
    items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)[: args.limit]

    print_header("📚 SAVED CONTENT")
    if not items:
        print("No matching content found.")
        return

    for idx, item in enumerate(items, start=1):
        print(f"\n{idx}. [{item.get('type', '').upper()}] {item.get('title', '')}")
        print(f"   ID: {item.get('id', '')}")
        print(f"   Topic: {item.get('topic', '')}")
        print(f"   Angle: {item.get('angle', '')}")
        print(f"   Tags: {', '.join(item.get('tags', []))}")
        print(f"   Created: {item.get('created_at', '')}")
        preview = item.get("content", "").replace("\n", " ")
        print(f"   Preview: {preview[:140]}{'...' if len(preview) > 140 else ''}")


if __name__ == "__main__":
    main()
