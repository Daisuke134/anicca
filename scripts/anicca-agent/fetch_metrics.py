"""
Fetch TikTok Metrics
Runs daily via GitHub Actions (~25 hours after posting).

Flow:
1. Get posts with pending metrics (EP-5)
2. Scrape TikTok via Apify (clockworks/tiktok-scraper)
3. Match scraped data to DB posts (caption + timestamp matching)
4. Update metrics per post (EP-4)
5. Refresh aggregate hook_candidate stats (EP-6)

Spec references: Section 5.1, 11.2, 11.8, 11.11
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from config import API_ONLY_KEYS, validate_env

# Only require API keys (not OpenAI/Blotato/Fal/Exa)
validate_env(API_ONLY_KEYS)

from api_client import AdminAPIClient

APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
TIKTOK_USERNAME = "anicca.self"

api = AdminAPIClient()


def normalize_caption(caption: str) -> str:
    """Normalize caption for matching: remove hashtags, trim, lowercase, first 50 chars."""
    if not caption:
        return ""
    text = re.sub(r"#\S+", "", caption)
    text = text.strip().lower()
    return text[:50]


def scrape_tiktok_profile() -> list:
    """Scrape recent TikTok posts via Apify clockworks/tiktok-scraper."""
    print(f"🔍 Scraping TikTok @{TIKTOK_USERNAME} via Apify...")

    # Start Apify actor run
    resp = requests.post(
        "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs",
        params={"token": APIFY_API_TOKEN},
        json={
            "profiles": [TIKTOK_USERNAME],
            "resultsPerPage": 10,
            "shouldDownloadVideos": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    run_data = resp.json().get("data", {})
    run_id = run_data.get("id")
    print(f"  Apify run started: {run_id}")

    # Poll for completion (max 5 min)
    for _ in range(60):
        time.sleep(5)
        status_resp = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            params={"token": APIFY_API_TOKEN},
            timeout=15,
        )
        status_resp.raise_for_status()
        status = status_resp.json().get("data", {}).get("status", "")
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise Exception(f"Apify run {status}: {run_id}")
        print(f"  Apify status: {status}...")
    else:
        raise TimeoutError(f"Apify run timed out after 5 min: {run_id}")

    # Fetch results
    dataset_id = status_resp.json().get("data", {}).get("defaultDatasetId")
    items_resp = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        params={"token": APIFY_API_TOKEN},
        timeout=30,
    )
    items_resp.raise_for_status()
    items = items_resp.json()
    print(f"  Scraped {len(items)} TikTok posts")
    return items


def match_post(db_post: dict, scraped_posts: list) -> dict | None:
    """
    Match a DB post to a scraped TikTok post.
    Strategy (Spec 11.2, 11.8): posted_at ± 2hrs + normalized caption prefix 50 chars.
    Skip if multiple matches found.
    """
    db_caption_norm = normalize_caption(db_post.get("caption", ""))
    db_posted_at = datetime.fromisoformat(db_post["posted_at"].replace("Z", "+00:00"))
    time_window = timedelta(hours=2)

    matches = []
    for scraped in scraped_posts:
        # Parse scraped timestamp
        scraped_time_str = scraped.get("createTimeISO") or scraped.get("createTime")
        if not scraped_time_str:
            continue
        try:
            if isinstance(scraped_time_str, (int, float)):
                scraped_time = datetime.fromtimestamp(scraped_time_str, tz=timezone.utc)
            else:
                scraped_time = datetime.fromisoformat(scraped_time_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        # Time window check
        if abs((scraped_time - db_posted_at).total_seconds()) > time_window.total_seconds():
            continue

        # Caption prefix check
        scraped_caption_norm = normalize_caption(scraped.get("text", ""))
        if not db_caption_norm or not scraped_caption_norm:
            continue
        if db_caption_norm[:50] == scraped_caption_norm[:50]:
            matches.append(scraped)

    # Skip if ambiguous (multiple matches)
    if len(matches) != 1:
        if len(matches) > 1:
            print(f"  ⚠️ Multiple matches ({len(matches)}) for post {db_post['id']}, skipping")
        return None

    return matches[0]


def run():
    print("📊 [FetchMetrics] Starting TikTok metrics fetch")

    # Step 1: Get pending posts
    pending = api.get_pending_metrics_posts()
    posts = pending.get("posts", [])
    print(f"📋 Posts pending metrics: {len(posts)}")

    if not posts:
        print("✅ No pending posts. Done.")
        # Still refresh stats (idempotent - Spec 11.11)
        try:
            api.refresh_tiktok_stats()
            print("✅ Refreshed hook_candidate stats (no-op)")
        except Exception as e:
            print(f"⚠️ Failed to refresh stats: {e}")
        return

    # Step 2: Scrape TikTok
    try:
        scraped_posts = scrape_tiktok_profile()
    except Exception as e:
        print(f"❌ Apify scrape failed: {e}")
        # Still try to refresh stats (Spec 11.11)
        try:
            api.refresh_tiktok_stats()
        except Exception:
            pass
        sys.exit(1)

    # Step 3: Match and update
    updated = 0
    try:
        for db_post in posts:
            matched = match_post(db_post, scraped_posts)
            if not matched:
                print(f"  ❌ No match for post {db_post['id']}")
                continue

            metrics = {
                "view_count": int(matched.get("playCount", 0) or 0),
                "like_count": int(matched.get("diggCount", 0) or 0),
                "share_count": int(matched.get("shareCount", 0) or 0),
                "comment_count": int(matched.get("commentCount", 0) or 0),
            }
            tiktok_video_id = matched.get("id")

            api.update_post_metrics(db_post["id"], metrics, tiktok_video_id)
            updated += 1
            print(f"  ✅ Updated post {db_post['id']}: views={metrics['view_count']}, likes={metrics['like_count']}")
    finally:
        # Step 4: Always refresh aggregate stats (Spec 11.11 - try/finally)
        try:
            result = api.refresh_tiktok_stats()
            print(f"✅ Refreshed hook_candidate stats: {result}")
        except Exception as e:
            print(f"⚠️ Failed to refresh stats: {e}")

    print(f"\n🏁 [FetchMetrics] Done. Updated {updated}/{len(posts)} posts.")


if __name__ == "__main__":
    if not APIFY_API_TOKEN:
        print("❌ APIFY_API_TOKEN not set")
        sys.exit(1)

    try:
        run()
    except Exception as e:
        print(f"❌ [FetchMetrics] Fatal error: {e}")
        sys.exit(1)
