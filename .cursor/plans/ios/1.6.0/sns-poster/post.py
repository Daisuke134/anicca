#!/usr/bin/env python3
"""
メイン投稿スクリプト
Cursorから直接呼び出し可能
"""
import sys
import argparse
from typing import List, Optional
from blotato import get_client as get_blotato_client, BlotatoClient
from config import ACCOUNTS, DEFAULT_HASHTAGS


def post_to_platform(
    platform: str,
    text: str,
    media_urls: Optional[List[str]] = None,
    title: Optional[str] = None,
    board_id: Optional[str] = None,
) -> dict:
    """
    Post to a specific platform

    Args:
        platform: x, instagram, tiktok, pinterest, youtube
        text: Post text/caption
        media_urls: List of media URLs (required for IG, TikTok, Pinterest, YouTube)
        title: Title (required for Pinterest, YouTube)
        board_id: Pinterest board ID (required for Pinterest)

    Returns:
        API response dict
    """
    client = get_blotato_client()

    if platform == "x":
        return client.post_to_x(text, media_urls)

    elif platform == "instagram":
        if not media_urls:
            raise ValueError("Instagram requires media")
        return client.post_to_instagram(text, media_urls)

    elif platform == "tiktok":
        if not media_urls:
            raise ValueError("TikTok requires media")
        return client.post_to_tiktok(text, media_urls)

    elif platform == "pinterest":
        if not media_urls:
            raise ValueError("Pinterest requires media")
        if not title:
            raise ValueError("Pinterest requires a title")
        if not board_id:
            # Try to get from config
            board_id = ACCOUNTS["pinterest"].get("board_id")
            if not board_id:
                raise ValueError("Pinterest requires a board_id")
        return client.post_to_pinterest(text, media_urls, title, board_id)

    elif platform == "youtube":
        if not media_urls:
            raise ValueError("YouTube requires media (video)")
        if not title:
            raise ValueError("YouTube requires a title")
        return client.post_to_youtube(text, media_urls, title)

    else:
        raise ValueError(f"Unknown platform: {platform}")


def main():
    parser = argparse.ArgumentParser(
        description="Post to SNS platforms via Blotato",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Post text to X
  python post.py x "Day 3: Building SNS automation! #buildinpublic"

  # Post with image to Instagram
  python post.py instagram "Check out Anicca!" --media https://example.com/image.jpg

  # Post video to TikTok
  python post.py tiktok "Meditation tips" --media https://example.com/video.mp4

  # Post to Pinterest
  python post.py pinterest "Description" --media https://... --title "Pin Title" --board-id 123

  # Post to YouTube
  python post.py youtube "Video description" --media https://... --title "Video Title"
""",
    )
    parser.add_argument(
        "platform",
        choices=["x", "instagram", "tiktok", "pinterest", "youtube"],
        help="Target platform",
    )
    parser.add_argument("text", help="Post text/caption")
    parser.add_argument(
        "--media",
        action="append",
        dest="media_urls",
        help="Media URL (can be used multiple times)",
    )
    parser.add_argument("--title", help="Title (for Pinterest/YouTube)")
    parser.add_argument("--board-id", dest="board_id", help="Pinterest board ID")
    parser.add_argument(
        "--hashtags",
        choices=["build_in_public", "marketing", "none"],
        default="none",
        help="Add default hashtags",
    )

    args = parser.parse_args()

    # Add hashtags if requested
    text = args.text
    if args.hashtags != "none":
        text = f"{text}\n\n{DEFAULT_HASHTAGS.get(args.hashtags, '')}"

    print(f"📤 Posting to {args.platform}...")
    print(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    if args.media_urls:
        print(f"   Media: {len(args.media_urls)} file(s)")
    print()

    try:
        result = post_to_platform(
            platform=args.platform,
            text=text,
            media_urls=args.media_urls,
            title=args.title,
            board_id=args.board_id,
        )
        print(f"✅ Posted successfully!")
        print(f"   Response: {result}")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

