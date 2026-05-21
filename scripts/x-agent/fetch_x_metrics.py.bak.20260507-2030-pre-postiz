"""
Fetch X Metrics — X API v2 で投稿メトリクスを取得し Railway DB に保存

Flow:
1. GET /api/admin/x/recent-posts?days=7 で直近7日のx_postsを取得
2. Blotato ID → 実ツイート ID の解決（x_post_id が null のレコード）
3. xPostId が非null のレコードのみ抽出
4. GET /2/tweets?ids=...&tweet.fields=public_metrics で X API v2 からメトリクス取得
5. PUT /api/admin/x/posts/:id/metrics で部分更新

X API v2 Free Tier:
- GET /2/tweets?ids=... のみ利用可能
- 月間読み取り上限あり
- 429 → 次回 cron に回す

Runs via GHA: .github/workflows/fetch-x-metrics.yml
"""
import os
import sys

import requests

from config import API_BASE_URL, API_AUTH_TOKEN, X_BEARER_TOKEN, BLOTATO_API_KEY, BLOTATO_BASE_URL


# ── API helpers ──────────────────────────────────────────────────────────────

def api_get(path, params=None):
    url = f"{API_BASE_URL}/api/admin{path}"
    headers = {"Authorization": f"Bearer {API_AUTH_TOKEN}", "Content-Type": "application/json"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_put(path, data):
    url = f"{API_BASE_URL}/api/admin{path}"
    headers = {"Authorization": f"Bearer {API_AUTH_TOKEN}", "Content-Type": "application/json"}
    resp = requests.put(url, headers=headers, json=data, timeout=30)
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


# ── Blotato ID resolution ────────────────────────────────────────────────────

def resolve_blotato_id(blotato_post_id):
    """Attempt to resolve a Blotato submission ID to the actual X tweet ID.

    Calls Blotato API GET /posts/{id} to check post status and extract platform post ID.
    Returns the real tweet ID string if found, or None.
    """
    if not BLOTATO_API_KEY or not blotato_post_id:
        return None

    try:
        url = f"{BLOTATO_BASE_URL}/posts/{blotato_post_id}"
        headers = {"blotato-api-key": BLOTATO_API_KEY, "Content-Type": "application/json"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        # Blotato may return platformPostId, externalId, or nested post data
        tweet_id = (
            data.get("platformPostId")
            or data.get("externalId")
            or data.get("post", {}).get("platformPostId")
            or data.get("post", {}).get("id_str")
        )
        if tweet_id and str(tweet_id).isdigit():
            return str(tweet_id)
        return None
    except Exception as e:
        print(f"  WARN: Blotato resolution failed for {blotato_post_id}: {e}")
        return None


# ── X API v2 ─────────────────────────────────────────────────────────────────

def fetch_metrics_by_ids(bearer_token, tweet_ids):
    """X API v2 GET /2/tweets?ids={id1},{id2},...&tweet.fields=public_metrics,created_at

    Free Tier: バッチ最大100 IDs/リクエスト
    Returns: { tweet_id: { impression_count, like_count, retweet_count, reply_count } }
    """
    if not tweet_ids:
        return {}

    # バッチ: 最大100 IDs
    results = {}
    for i in range(0, len(tweet_ids), 100):
        batch = tweet_ids[i:i + 100]
        ids_param = ",".join(batch)

        url = "https://api.x.com/2/tweets"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        params = {
            "ids": ids_param,
            "tweet.fields": "public_metrics,created_at",
        }

        resp = requests.get(url, headers=headers, params=params, timeout=30)

        if resp.status_code == 429:
            print("WARN: X API rate limited (429). Stopping — will retry next cron run.")
            record_ops_event("x_credits_depleted", {"reason": "rate_limited_429", "stage": "fetch_metrics"})
            return results  # 取得済み分だけ返す

        resp.raise_for_status()
        data = resp.json()

        for tweet in data.get("data", []):
            metrics = tweet.get("public_metrics", {})
            results[tweet["id"]] = {
                "impression_count": metrics.get("impression_count"),
                "like_count": metrics.get("like_count"),
                "retweet_count": metrics.get("retweet_count"),
                "reply_count": metrics.get("reply_count"),
            }

    return results


# ── Metrics update ───────────────────────────────────────────────────────────

def update_metrics(api_base_url, auth_token, db_record_id, metrics):
    """PUT /api/admin/x/posts/:id/metrics — 部分更新

    :id は DB レコードの主キー（x_posts.id）。xPostId（X投稿ID）ではない。
    送信されたフィールドのみ DB 更新。未送信フィールドは既存値維持。
    """
    # 欠落フィールドは送信しない（null 上書き防止）
    payload = {}
    for key in ("impression_count", "like_count", "retweet_count", "reply_count"):
        val = metrics.get(key)
        if val is not None:
            payload[key] = val

    if not payload:
        print(f"  WARN: All metrics fields missing for record {db_record_id}, skipping update")
        return

    api_put(f"/x/posts/{db_record_id}/metrics", payload)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Fetch X Metrics ===")

    if not X_BEARER_TOKEN:
        print("ERROR: X_BEARER_TOKEN not set. Exiting.")
        sys.exit(1)
    if not API_BASE_URL:
        print("ERROR: API_BASE_URL not set. Exiting.")
        sys.exit(1)

    # Step 1: GET /api/admin/x/recent-posts?days=7
    print("\n[1/4] Fetching recent X posts from DB (7 days)...")
    recent = api_get("/x/recent-posts", params={"days": 7})
    posts = recent.get("posts", [])
    print(f"  Found {len(posts)} post(s)")

    # Step 2: Resolve Blotato IDs → real tweet IDs for posts without x_post_id
    posts_needing_resolution = [
        p for p in posts
        if not p.get("x_post_id") and p.get("blotato_post_id")
    ]
    if posts_needing_resolution:
        print(f"\n[2/4] Resolving {len(posts_needing_resolution)} Blotato ID(s) to tweet IDs...")
        for p in posts_needing_resolution:
            tweet_id = resolve_blotato_id(p["blotato_post_id"])
            if tweet_id:
                print(f"  Resolved: blotato={p['blotato_post_id']} → tweet={tweet_id}")
                # Update DB with resolved tweet ID via metrics endpoint
                try:
                    api_put(f"/x/posts/{p['id']}/metrics", {"x_post_id": tweet_id})
                    p["x_post_id"] = tweet_id  # Update local record
                except Exception as e:
                    print(f"  ERROR updating x_post_id for {p['id']}: {e}")
            else:
                print(f"  SKIP: blotato={p['blotato_post_id']} — not yet resolved (post may be processing)")
    else:
        print("\n[2/4] No Blotato IDs to resolve.")

    # Step 3: xPostId が非null のレコードのみ
    posts_with_id = [p for p in posts if p.get("x_post_id")]
    if not posts_with_id:
        print("  No posts with xPostId. Nothing to fetch. Exiting.")
        return

    # xPostId → db_record_id のマッピング
    id_map = {}  # { xPostId: db_record_id }
    tweet_ids = []
    for p in posts_with_id:
        x_id = str(p["x_post_id"])
        id_map[x_id] = p["id"]
        tweet_ids.append(x_id)

    print(f"  {len(tweet_ids)} post(s) with xPostId")

    # Step 4: X API v2 でメトリクス取得
    print(f"\n[3/4] Fetching metrics from X API v2 ({len(tweet_ids)} IDs)...")
    metrics_map = fetch_metrics_by_ids(X_BEARER_TOKEN, tweet_ids)
    print(f"  Got metrics for {len(metrics_map)} tweet(s)")

    # マッチしなかった xPostId をログ
    for x_id in tweet_ids:
        if x_id not in metrics_map:
            print(f"  WARN: xPostId {x_id} not found in X API")

    # Step 5: DB 更新
    print(f"\n[4/4] Updating DB metrics...")
    updated = 0
    for x_id, metrics in metrics_map.items():
        db_id = id_map.get(x_id)
        if not db_id:
            continue
        try:
            update_metrics(API_BASE_URL, API_AUTH_TOKEN, db_id, metrics)
            updated += 1
            print(f"  Updated: {db_id} (xPostId={x_id})")
        except requests.HTTPError as e:
            print(f"  ERROR updating {db_id}: {e}")
        except Exception as e:
            print(f"  ERROR updating {db_id}: {e}")

    print(f"\n=== Done: {updated}/{len(metrics_map)} updated ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
