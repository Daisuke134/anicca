#!/usr/bin/env python3
"""
動画生成スクリプト
Fal.ai Seedance を使用
"""
import sys
import argparse
from datetime import datetime
from fal_ai import get_client
from config import VIDEOS_DIR


def main():
    parser = argparse.ArgumentParser(description="Generate videos with Fal.ai Seedance")
    parser.add_argument("prompt", help="Video generation prompt")
    parser.add_argument(
        "--aspect",
        default="9:16",
        choices=["9:16", "16:9", "1:1"],
        help="Aspect ratio (default: 9:16 for TikTok/Reels)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Video duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save video URL to file",
    )
    args = parser.parse_args()

    print(f"🎬 Generating video...")
    print(f"   Prompt: {args.prompt}")
    print(f"   Aspect: {args.aspect}")
    print(f"   Duration: {args.duration}s")
    print()

    try:
        client = get_client()
        result = client.generate_video(args.prompt, args.aspect, args.duration)
        video = result.get("video", {})
        url = video.get("url", "")

        if url:
            print(f"✅ Video: {url}")

            if args.save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = VIDEOS_DIR / f"video_{timestamp}.txt"
                filename.write_text(url)
                print(f"   Saved to: {filename}")
        else:
            print("❌ No video URL in response")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

