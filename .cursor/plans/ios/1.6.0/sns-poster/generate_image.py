#!/usr/bin/env python3
"""
画像生成スクリプト
Fal.ai FLUX を使用
"""
import sys
import argparse
from datetime import datetime
from pathlib import Path
from fal_ai import generate_image, get_client
from config import IMAGES_DIR


def main():
    parser = argparse.ArgumentParser(description="Generate images with Fal.ai FLUX")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument(
        "--size",
        default="square_hd",
        choices=["square_hd", "landscape_16_9", "portrait_9_16"],
        help="Image size (default: square_hd)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of images to generate (default: 1)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save image URL to file",
    )
    args = parser.parse_args()

    print(f"🖼️ Generating {args.count} image(s)...")
    print(f"   Prompt: {args.prompt}")
    print(f"   Size: {args.size}")
    print()

    try:
        client = get_client()
        result = client.generate_image(args.prompt, args.size, args.count)
        images = result.get("images", [])

        for i, img in enumerate(images):
            url = img.get("url", "")
            print(f"✅ Image {i + 1}: {url}")

            if args.save and url:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = IMAGES_DIR / f"image_{timestamp}_{i + 1}.txt"
                filename.write_text(url)
                print(f"   Saved to: {filename}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

