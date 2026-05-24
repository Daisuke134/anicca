#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
from scripts.lib.storage import load_json, save_json
from scripts.lib.schema import make_content_item
from scripts.lib.output import print_header, print_kv


def main() -> None:
    parser = argparse.ArgumentParser(description="Save TikTok content asset to local bank.")
    parser.add_argument("--type", required=True, choices=["idea", "hook", "script", "caption", "note"], help="Content type")
    parser.add_argument("--title", required=True, help="Short title for the asset")
    parser.add_argument("--content", required=True, help="Main content body")
    parser.add_argument("--topic", default="", help="Topic")
    parser.add_argument("--angle", default="", help="Angle or framing")
    parser.add_argument("--tags", default="", help='Comma-separated tags, e.g. "dating,contrarian,hook"')
    parser.add_argument("--notes", default="", help="Extra notes")

    args = parser.parse_args()

    bank = load_json("content_bank")
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    item = make_content_item(
        item_type=args.type,
        title=args.title.strip(),
        content=args.content.strip(),
        topic=args.topic.strip(),
        angle=args.angle.strip(),
        tags=tags,
        notes=args.notes.strip(),
    )

    bank["items"].append(item)
    save_json("content_bank", bank)

    print_header("✅ CONTENT SAVED")
    print_kv("ID", item["id"])
    print_kv("Type", item["type"])
    print_kv("Title", item["title"])
    print_kv("Topic", item["topic"])
    print_kv("Angle", item["angle"])
    print_kv("Tags", ", ".join(item["tags"]))


if __name__ == "__main__":
    main()
