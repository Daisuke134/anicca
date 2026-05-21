#!/usr/bin/env python3
"""
バッチ投稿スクリプト
複数プラットフォームへの一括投稿
"""
import sys
import argparse
from typing import List, Optional
from post import post_to_platform
from config import ACCOUNTS


def batch_post(
    text: str,
    platforms: List[str],
    media_urls: Optional[List[str]] = None,
    title: Optional[str] = None,
    board_id: Optional[str] = None,
) -> dict:
    """
    Post to multiple platforms at once

    Args:
        text: Post text
        platforms: List of platforms to post to
        media_urls: List of media URLs
        title: Title for Pinterest/YouTube
        board_id: Pinterest board ID

    Returns:
        Dict of platform -> result/error
    """
    results = {}

    for platform in platforms:
        print(f"\n📤 Posting to {platform}...")
        try:
            result = post_to_platform(
                platform=platform,
                text=text,
                media_urls=media_urls,
                title=title,
                board_id=board_id,
            )
            results[platform] = {"success": True, "response": result}
            print(f"   ✅ Success")
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)}
            print(f"   ❌ Failed: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch post to multiple SNS platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Post to all platforms with media
  python batch_post.py "New video!" --media https://... --platforms all --title "Title"

  # Post to specific platforms
  python batch_post.py "Update!" --platforms x instagram tiktok

  # Text-only to X (only platform that allows text-only)
  python batch_post.py "Just shipped!" --platforms x
""",
    )
    parser.add_argument("text", help="Post text/caption")
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["x"],
        help="Platforms to post to (x, instagram, tiktok, pinterest, youtube, or 'all')",
    )
    parser.add_argument(
        "--media",
        action="append",
        dest="media_urls",
        help="Media URL (can be used multiple times)",
    )
    parser.add_argument("--title", help="Title (for Pinterest/YouTube)")
    parser.add_argument("--board-id", dest="board_id", help="Pinterest board ID")

    args = parser.parse_args()

    # Expand 'all' to all platforms
    if "all" in args.platforms:
        platforms = list(ACCOUNTS.keys())
    else:
        platforms = args.platforms

    # Validate: only X allows text-only posts
    if not args.media_urls:
        text_only_platforms = [p for p in platforms if p != "x"]
        if text_only_platforms:
            print(f"⚠️ Warning: {text_only_platforms} require media. Skipping these.")
            platforms = ["x"] if "x" in platforms else []

    if not platforms:
        print("❌ No valid platforms to post to")
        return 1

    print(f"🚀 Batch posting to: {', '.join(platforms)}")
    print(f"   Text: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
    if args.media_urls:
        print(f"   Media: {len(args.media_urls)} file(s)")

    results = batch_post(
        text=args.text,
        platforms=platforms,
        media_urls=args.media_urls,
        title=args.title,
        board_id=args.board_id,
    )

    # Summary
    print("\n" + "=" * 50)
    print("📊 Summary:")
    success = sum(1 for r in results.values() if r["success"])
    print(f"   ✅ Success: {success}/{len(results)}")
    for platform, result in results.items():
        status = "✅" if result["success"] else "❌"
        print(f"   {status} {platform}")

    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

