#!/usr/bin/env python3
"""Record the retained ebook-producer inputs without changing them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


JP_ROOT = Path("/Users/anicca/anicca-monk-factory")
EN_IMAGE = JP_ROOT / "characters/en/icon_v2_full.png"
JP_VIDEO = JP_ROOT / "renders/jp_20260801_070000_final.mp4"
JP_SCRIPT = JP_ROOT / "state/current_jp.json"
JP_CAPTIONS = JP_ROOT / "renders/jp_20260801_070000/subs.ass"
JP_CLIPS = tuple(JP_ROOT / "state" / f"jp_kling_clip_{number}.mp4" for number in
                 ("02", "03", "04", "05", "06", "07", "08", "09", "10", "12", "13"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height",
         "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def entry(path: Path, *, media: bool = False) -> dict:
    item = {"path": str(path), "exists": path.is_file()}
    if item["exists"]:
        item.update({"bytes": path.stat().st_size, "sha256": digest(path)})
        if media:
            item["probe"] = probe(path)
    return item


def characterize() -> dict:
    jp_required = (JP_VIDEO, JP_SCRIPT, JP_CAPTIONS, *JP_CLIPS)
    jp_inventory_ready = all(path.is_file() for path in jp_required)
    return {
        "schema_version": "ebook-producer-characterization.v1",
        "products": {
            "ebook-ja": {
                "status": "retained_fixture_not_yet_replayed",
                "historical_fixture": entry(JP_VIDEO, media=True),
                "current_mutable_script_state": entry(JP_SCRIPT),
                "historical_fixture_captions": entry(JP_CAPTIONS),
                "locked_motion_clips": [entry(path, media=True) for path in JP_CLIPS],
                "missing_dependencies": [
                    *([] if jp_inventory_ready else [str(path) for path in jp_required if not path.is_file()]),
                    "immutable run manifest binding the historical fixture to its script and exact clip order",
                    "voice provider, voice ID, and audio hash for the historical fixture",
                    "fresh no-network replay with media/hash and visual-identity comparison",
                ],
            },
            "ebook-en": {
                "status": "blocked_free_runtime_reproduction",
                "retained_candidate_reference_image": entry(EN_IMAGE),
                "approved_artifact": {
                    "telegram_message_id": "4893",
                    "space": "alexnasa/OmniAvatar",
                    "space_revision": "e6a7899449e8a16003b0b01046ea6d29dbbd00c5",
                    "repository_revision": "1536bf31abaec74364fb7d5883470d5b23ffa7f8",
                    "known_result": "5.04s, 400x720, H.264/AAC, owner-approved",
                },
                "missing_dependencies": [
                    "durable local copy of Telegram artifact 4893",
                    "proof that Telegram artifact 4893 used the retained candidate image hash",
                    "working public Space session path that accepts orientation state and returns a render receipt",
                ],
                "explicitly_excluded": ["HeyGen", "paid renderer fallback"],
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(characterize(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
