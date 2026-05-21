"""
TikTok → Instagram Cross-Poster

Main script. Detects new TikTok slideshows via Apify, extracts images,
uploads to Blotato storage, and schedules Instagram carousel posts.

Runs via GitHub Actions: .github/workflows/cross-post-tiktok-to-ig.yml
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

import requests

from config import (
    ACCOUNT_MAPPING,
    LOOKBACK_HOURS,
    POSTING_SLOTS_JST,
    SLACK_WEBHOOK_URL,
    STAGGER_MINUTES,
    validate_env,
)
from instagram_poster import strip_tiktok_hashtags, upload_and_post_carousel
from state import load_processed_ids, save_processed_id
from tiktok_scraper import fetch_new_slideshows

JST = timezone(timedelta(hours=9))


def next_posting_slot(now_utc: datetime, slot_index: int = 0) -> str:
    """Calculate the next posting slot in ISO 8601 UTC.

    Args:
        now_utc: Current UTC time
        slot_index: 0-based index for staggering (0 = exact slot, 1 = +30min, etc.)

    Returns:
        ISO 8601 UTC datetime string
    """
    now_jst = now_utc.astimezone(JST)
    stagger = timedelta(minutes=STAGGER_MINUTES * slot_index)

    for slot_hour in sorted(POSTING_SLOTS_JST):
        candidate = now_jst.replace(hour=slot_hour, minute=0, second=0, microsecond=0)
        candidate += stagger
        if candidate > now_jst:
            return candidate.astimezone(timezone.utc).isoformat()

    # All slots passed today → first slot tomorrow
    tomorrow = now_jst + timedelta(days=1)
    first_slot = tomorrow.replace(
        hour=POSTING_SLOTS_JST[0], minute=0, second=0, microsecond=0
    )
    first_slot += stagger
    return first_slot.astimezone(timezone.utc).isoformat()


def _parse_schedule_times(schedule_str: str, now_utc: datetime) -> list[str | None]:
    """Parse comma-separated schedule times.

    'now' = None (immediate), 'HH:MM' = JST time today, ISO 8601 = as-is.
    """
    times = []
    for t in schedule_str.split(","):
        t = t.strip()
        if t.lower() == "now":
            times.append(None)
        elif ":" in t and len(t) <= 5:
            hour, minute = int(t.split(":")[0]), int(t.split(":")[1])
            jst_time = now_utc.astimezone(JST).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            times.append(jst_time.astimezone(timezone.utc).isoformat())
        else:
            times.append(t)
    return times


def process_account(
    account_key: str,
    account_config: dict,
    now_utc: datetime,
    dry_run: bool = False,
    lookback_hours: int = LOOKBACK_HOURS,
    force: bool = False,
    schedule_times: list[str | None] | None = None,
) -> dict:
    """Process one account mapping (Apify scrape → Instagram post).

    Returns:
        Stats dict: {"detected": N, "posted": N, "skipped": N, "errors": N}
    """
    stats = {"detected": 0, "posted": 0, "skipped": 0, "errors": 0}
    tiktok_username = account_config["tiktok_username"]
    ig_account_id = account_config["ig_account_id"]

    print(f"\n{'='*60}")
    print(f"Processing [{account_key}] TikTok @{tiktok_username} → IG {ig_account_id}")
    print(f"{'='*60}")

    # 1. Fetch new slideshow posts via Apify
    since = now_utc - timedelta(hours=lookback_hours)
    try:
        posts = fetch_new_slideshows(tiktok_username, since)
    except Exception as e:
        print(f"  ERROR: Apify scrape failed: {e}")
        stats["errors"] += 1
        return stats

    stats["detected"] = len(posts)
    print(f"  Found {len(posts)} new slideshows (since {since.isoformat()})")

    if not posts:
        return stats

    # 2. Filter out already-processed posts (skip if --force)
    if force:
        new_posts = posts
        print(f"  Force mode: processing all {len(posts)} posts")
    else:
        processed_ids = load_processed_ids()
        new_posts = [p for p in posts if p["id"] not in processed_ids]
        stats["skipped"] = len(posts) - len(new_posts)

        if not new_posts:
            print(f"  All posts already processed. Skipping.")
            return stats

        print(f"  {len(new_posts)} new, {stats['skipped']} already processed")

    # 3. Post each slideshow to Instagram
    slot_index = 0
    for post in new_posts:
        tiktok_url = post["link"]
        images = post["images"]
        caption = strip_tiktok_hashtags(post["title"])

        # Use custom schedule or auto-calculate
        if schedule_times and slot_index < len(schedule_times):
            scheduled = schedule_times[slot_index]
        else:
            scheduled = next_posting_slot(now_utc, slot_index)

        time_label = "IMMEDIATE" if scheduled is None else scheduled
        print(f"  Posting {len(images)} images to IG ({time_label})")
        print(f"  Caption: {caption[:80]}...")

        if dry_run:
            print(f"  [DRY RUN] Would post to IG account {ig_account_id}")
            save_processed_id(tiktok_url)
            stats["posted"] += 1
            slot_index += 1
            continue

        try:
            result = upload_and_post_carousel(
                account_id=ig_account_id,
                caption=caption,
                image_urls=images,
                scheduled_time=scheduled,
            )
            print(f"  SUCCESS: {result}")
            save_processed_id(tiktok_url)
            stats["posted"] += 1
            slot_index += 1
        except Exception as e:
            print(f"  ERROR posting to IG: {e}")
            stats["errors"] += 1

    return stats


def send_slack_summary(all_stats: dict[str, dict]) -> None:
    """Send summary to Slack #agents channel."""
    if not SLACK_WEBHOOK_URL:
        print("  No Slack webhook configured, skipping notification")
        return

    lines = ["*TikTok→IG Cross-Post Report*"]
    total_posted = 0
    total_errors = 0

    for key, stats in all_stats.items():
        lang = ACCOUNT_MAPPING[key]["lang"]
        lines.append(
            f"- {lang}: {stats['detected']} detected, "
            f"{stats['posted']} posted, {stats['skipped']} skipped"
        )
        total_posted += stats["posted"]
        total_errors += stats["errors"]

    lines.append(f"- Errors: {total_errors}")

    payload = {"text": "\n".join(lines)}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"  WARNING: Slack notification failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Cross-post TikTok slideshows to Instagram")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually post")
    parser.add_argument("--account", choices=list(ACCOUNT_MAPPING.keys()), help="Process only this account")
    parser.add_argument("--lookback", type=int, default=LOOKBACK_HOURS, help="Lookback window in hours")
    parser.add_argument("--force", action="store_true", help="Ignore processed IDs cache")
    parser.add_argument("--schedule-times", type=str, default="", help="Custom schedule: 'now,17:00,22:00' (JST)")
    args = parser.parse_args()

    validate_env()

    now_utc = datetime.now(timezone.utc)
    print(f"Cross-poster started at {now_utc.isoformat()}")
    print(f"Dry run: {args.dry_run}")
    if args.account:
        print(f"Account filter: {args.account}")
    if args.lookback != LOOKBACK_HOURS:
        print(f"Custom lookback: {args.lookback}h")
    if args.force:
        print(f"Force mode: ignoring processed IDs")

    schedule_times = None
    if args.schedule_times:
        schedule_times = _parse_schedule_times(args.schedule_times, now_utc)
        print(f"Custom schedule: {schedule_times}")

    accounts = {args.account: ACCOUNT_MAPPING[args.account]} if args.account else ACCOUNT_MAPPING
    all_stats = {}
    for key, config in accounts.items():
        all_stats[key] = process_account(
            key, config, now_utc,
            dry_run=args.dry_run,
            lookback_hours=args.lookback,
            force=args.force,
            schedule_times=schedule_times,
        )

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for key, stats in all_stats.items():
        print(f"  [{key}] detected={stats['detected']} posted={stats['posted']} "
              f"skipped={stats['skipped']} errors={stats['errors']}")

    send_slack_summary(all_stats)

    # Exit with error if any errors occurred
    total_errors = sum(s["errors"] for s in all_stats.values())
    if total_errors > 0:
        print(f"\n{total_errors} error(s) occurred. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
