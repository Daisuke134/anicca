"""
Anicca X Agent — Slot-based posting
Posts to X/Twitter using Commander Agent's daily output.

Flow:
1. Read POST_SLOT env (morning/evening) from GHA
2. Fetch pending xPosts for that slot (GET /api/admin/x/pending?slot=...)
3. Post via Blotato API (immediate — scheduling is handled by GHA cron)
4. Save records (POST /api/admin/x/posts)

Runs via GitHub Actions: .github/workflows/anicca-x-post.yml
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

from config import (
    BLOTATO_API_KEY, BLOTATO_BASE_URL,
    API_BASE_URL, API_AUTH_TOKEN, X_ACCOUNT_ID,
    MAX_POSTS_PER_RUN, validate_env,
)
from posting_policy import truncate_x_text, should_retry, backoff_seconds, classify_http_status

validate_env()

JST = timezone(timedelta(hours=9))


# ── API helpers ──────────────────────────────────────────────────────────────

def api_get(path, params=None):
    url = f"{API_BASE_URL}/api/admin{path}"
    headers = {"Authorization": f"Bearer {API_AUTH_TOKEN}", "Content-Type": "application/json"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(path, data):
    url = f"{API_BASE_URL}/api/admin{path}"
    headers = {"Authorization": f"Bearer {API_AUTH_TOKEN}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def record_ops_event(event_type: str, payload: dict):
    """Best-effort ops event recorder (never throws)."""
    try:
        api_post("/ops/events", {"eventType": event_type, "platform": "x", "payload": payload})
    except Exception as e:
        print(f"WARN: failed to record ops event {event_type}: {type(e).__name__}")


def blotato_post(text):
    """Post to X via Blotato API v2 (immediate)."""
    url = f"{BLOTATO_BASE_URL}/posts"
    headers = {"blotato-api-key": BLOTATO_API_KEY, "Content-Type": "application/json"}
    payload = {
        "post": {
            "accountId": X_ACCOUNT_ID,
            "content": {
                "text": text,
                "mediaUrls": [],
                "platform": "twitter",
            },
            "target": {
                "targetType": "twitter",
            },
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    slot = os.environ.get("POST_SLOT", "morning")
    print(f"=== Anicca X Agent ({slot} slot) ===")

    # Step 1: Fetch Commander-generated xPosts for this slot
    print(f"\n[1/2] Fetching pending X posts for slot={slot}...")
    pending = api_get("/x/pending", params={"slot": slot})
    candidates = pending.get("xPosts", [])

    if not candidates:
        print(f"No pending X posts for {slot} slot. Exiting.")
        return

    print(f"  Found {len(candidates)} candidate(s)")

    # Step 2: Post via Blotato + save records
    print("\n[2/2] Posting via Blotato...")
    now_jst = datetime.now(JST)

    for i, candidate in enumerate(candidates[:MAX_POSTS_PER_RUN]):
        text = truncate_x_text(candidate.get("text", ""))

        try:
            print(f"\n  Post {i+1}: immediate ({slot})")
            print(f"  Text: {text[:80]}...")

            result = None
            for attempt in range(0, 3):
                try:
                    result = blotato_post(text)
                    break
                except requests.HTTPError as e:
                    status = e.response.status_code if e.response is not None else None
                    classified = classify_http_status(status)
                    print(f"  ERROR posting (HTTP {status}) category={classified.category} retryable={classified.retryable}")
                    if not should_retry(status, attempt):
                        raise
                    wait = backoff_seconds(attempt)
                    print(f"  Retrying in {wait}s...")
                    import time as _time
                    _time.sleep(wait)

            if result is None:
                raise RuntimeError("Failed to post after retries")
            blotato_id = str(result.get("postSubmissionId", result.get("id", result.get("postId", ""))))

            print(f"  Blotato ID: {blotato_id}")

            # Save to Railway DB (blotato_post_id ≠ x_post_id; real tweet ID resolved later by fetch_x_metrics)
            api_post("/x/posts", {
                "text": text,
                "blotato_post_id": blotato_id if blotato_id else None,
                "agent_reasoning": candidate.get("reasoning", ""),
                "posted_at": now_jst.isoformat(),
                "slot": slot,
            })
            print("  Record saved.")

        except requests.HTTPError as e:
            print(f"  ERROR posting: {e}")
            print(f"  Response: {e.response.text if e.response else 'N/A'}")
            status = e.response.status_code if e.response is not None else None
            if status == 429:
                record_ops_event("x_credits_depleted", {"reason": "rate_limited_429", "slot": slot})
                print("WARN: rate limited (429). Pausing X posting for today.")
                return
            continue
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    print(f"\n=== X Agent ({slot}) complete ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
