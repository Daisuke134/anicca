"""
Instagram Carousel Poster

Uploads images to Blotato storage (for CDN persistence) and posts carousels to Instagram.
"""
import re

import requests

from config import BLOTATO_API_KEY, BLOTATO_BASE_URL, TIKTOK_ONLY_HASHTAGS


def _headers() -> dict:
    """Build request headers with current BLOTATO_API_KEY value."""
    return {
        "blotato-api-key": BLOTATO_API_KEY,
        "Content-Type": "application/json",
    }


def upload_image_to_blotato(image_url: str) -> str:
    """Upload an image to Blotato storage for permanent hosting.

    Args:
        image_url: Source image URL (may be CDN with expiration)

    Returns:
        Permanent Blotato-hosted URL
    """
    resp = requests.post(
        f"{BLOTATO_BASE_URL}/media",
        headers=_headers(),
        json={"url": image_url},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["url"]


def upload_and_post_carousel(
    account_id: str,
    caption: str,
    image_urls: list[str],
    scheduled_time: str | None = None,
) -> dict:
    """Upload images to Blotato storage, then post carousel to Instagram.

    Args:
        account_id: Blotato Instagram account ID
        caption: Post caption (TikTok hashtags already stripped)
        image_urls: List of image URLs (from Apify scraper)
        scheduled_time: ISO 8601 UTC datetime for scheduled posting, or None for immediate

    Returns:
        Blotato API response dict
    """
    # Step 1: Upload all images to Blotato storage
    permanent_urls = []
    for url in image_urls:
        permanent_url = upload_image_to_blotato(url)
        permanent_urls.append(permanent_url)
        print(f"    Uploaded: {permanent_url[:60]}...")

    # Step 2: Post carousel to Instagram
    # mediaType is omitted - Blotato auto-creates carousel for multiple mediaUrls
    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": caption,
                "mediaUrls": permanent_urls,
                "platform": "instagram",
            },
            "target": {
                "targetType": "instagram",
            },
        },
    }
    if scheduled_time:
        payload["scheduledTime"] = scheduled_time

    resp = requests.post(
        f"{BLOTATO_BASE_URL}/posts",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def strip_tiktok_hashtags(caption: str) -> str:
    """Remove TikTok-specific hashtags from caption.

    Strips: #fyp, #foryou, #foryoupage, #tiktok, #viral, etc.
    Preserves other hashtags.
    """
    words = caption.split()
    filtered = [w for w in words if w.lower() not in TIKTOK_ONLY_HASHTAGS]
    result = " ".join(filtered)
    # Clean up multiple spaces
    return re.sub(r"\s+", " ", result).strip()
