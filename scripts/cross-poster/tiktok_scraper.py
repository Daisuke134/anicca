"""
TikTok Slideshow Scraper

Uses Apify clockworks~tiktok-scraper to detect new slideshow posts and extract images.
Replaces the previous RSS.app-based detection (removed due to 402 Payment Required).
"""
from datetime import datetime, timezone

import requests

from config import APIFY_API_TOKEN, APIFY_ACTOR_ID, APIFY_RESULTS_PER_PAGE


def fetch_new_slideshows(
    tiktok_username: str,
    since: datetime,
) -> list[dict]:
    """Scrape a TikTok profile and return new slideshow posts with images.

    Args:
        tiktok_username: TikTok username without @
        since: Only return posts created after this datetime (UTC)

    Returns:
        List of dicts: {"id": url, "title": text, "pub_date": iso, "link": url, "images": [url]}
    """
    scraped = _run_apify_scraper(tiktok_username)
    results = []

    for post in scraped:
        post_url = post.get("webVideoUrl") or post.get("url") or ""
        if not post_url:
            continue

        # Filter by date
        post_date = _parse_post_date(post)
        if post_date and post_date <= since:
            continue

        # Only slideshows (skip videos)
        if not post.get("isSlideshow"):
            continue

        images = _extract_slideshow_images(post)
        if not images:
            continue

        results.append({
            "id": post_url,
            "title": post.get("text") or "",
            "link": post_url,
            "pub_date": post_date.isoformat() if post_date else "",
            "images": images,
        })

    return results


def _parse_post_date(post: dict) -> datetime | None:
    """Parse post creation date from Apify data."""
    # Try ISO format first (createTimeISO)
    iso_str = post.get("createTimeISO")
    if iso_str:
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            pass

    # Fall back to Unix timestamp (createTime)
    ts = post.get("createTime")
    if ts:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

    return None


def _run_apify_scraper(username: str) -> list[dict]:
    """Run Apify TikTok scraper on a profile and return results."""
    run_url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/runs"
    headers = {"Authorization": f"Bearer {APIFY_API_TOKEN}"}

    run_input = {
        "profiles": [username],
        "resultsPerPage": APIFY_RESULTS_PER_PAGE,
        "shouldDownloadSlideshowImages": True,
    }

    print(f"  Scraping TikTok @{username} via Apify...")
    resp = requests.post(
        run_url,
        json=run_input,
        headers=headers,
        params={"waitForFinish": 300},
        timeout=360,
    )
    resp.raise_for_status()
    run_data = resp.json().get("data", {})
    dataset_id = run_data.get("defaultDatasetId")

    if not dataset_id:
        print(f"  WARNING: No dataset returned for @{username}")
        return []

    return _fetch_dataset(dataset_id, headers)


def _fetch_dataset(dataset_id: str, headers: dict) -> list[dict]:
    """Fetch results from an Apify dataset."""
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
    resp = requests.get(dataset_url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _extract_slideshow_images(post: dict) -> list[str]:
    """Extract all slideshow image URLs from a scraped post.

    Prefers downloadLink (persistent) over tiktokLink (CDN, expires).
    """
    images = []
    for img in post.get("slideshowImageLinks", []):
        url = img.get("downloadLink") or img.get("tiktokLink")
        if url:
            images.append(url)
    return images
