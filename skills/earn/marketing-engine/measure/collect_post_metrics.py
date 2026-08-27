#!/usr/bin/env python3
"""collect_post_metrics.py — attach real numbers to posts that already went out.

account-history.jsonl carries 797 posts whose views_6h/24h/48h are all null: the loop
has been publishing blind. Postiz's public API returns the released URL and the state
but no engagement, so the numbers are fetched from the platforms themselves through the
Apify actors already paid for on the free tier.

  TikTok    clockworks~tiktok-scraper   postURLs
  Instagram apify~instagram-scraper     directUrls

Also surfaces what nobody was watching: posts stuck in ERROR state.

  collect_post_metrics.py [--days 3] [--limit 40] [--platform tiktok|instagram|all]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

STATE = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_POST_METRICS_STATE",
    "~/.openclaw/state/content-library/post-metrics.jsonl")))
ENV_FILE = pathlib.Path(os.path.expanduser("~/.openclaw/.env"))
POSTIZ = "https://api.postiz.com/public/v1"
ACTORS = {
    "tiktok": ("clockworks~tiktok-scraper", "postURLs"),
    "instagram": ("apify~instagram-scraper", "directUrls"),
}


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(errors="replace").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    return env


def http_json(url: str, headers: dict, data: bytes | None = None, method: str = "GET"):
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def platform_of(post: dict) -> str:
    integ = post.get("integration") or {}
    ident = integ.get("providerIdentifier", "") if isinstance(integ, dict) else ""
    if "tiktok" in ident:
        return "tiktok"
    if "instagram" in ident:
        return "instagram"
    if "youtube" in ident:
        return "youtube"
    return ident or "unknown"


def fetch_posts(env, days: int) -> list[dict]:
    key = env.get("POSTIZ_API_KEY")
    if not key:
        raise SystemExit("FATAL: POSTIZ_API_KEY missing")
    now = dt.datetime.now(dt.timezone.utc)
    q = urllib.parse.urlencode({
        "startDate": (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59.000Z"),
        "limit": 200,
    })
    body = http_json(f"{POSTIZ}/posts?{q}", {"Authorization": key})
    return body if isinstance(body, list) else body.get("posts", [])


def scrape(env, platform: str, urls: list[str]) -> list[dict]:
    """Fetch engagement for our own posts.

    Instagram's Postiz releaseURL is a real post URL, so it can be fetched directly.
    TikTok's releaseURL is only the profile (`https://www.tiktok.com/@handle`), which
    `postURLs` rejects with a 400 — so TikTok is collected by walking the profile's
    recent videos and matching them back to our posts by caption.
    """
    token = env.get("APIFY_API_TOKEN")
    if not token:
        raise SystemExit("FATAL: APIFY_API_TOKEN missing")
    actor, field = ACTORS[platform]
    payload: dict = {field: urls}
    if platform == "instagram":
        payload["resultsType"] = "posts"
        payload["resultsLimit"] = 1
    if platform == "tiktok":
        payload = {"profiles": [u.rstrip("/").split("@")[-1] for u in urls],
                   "resultsPerPage": 10,
                   "shouldDownloadVideos": False,
                   "shouldDownloadCovers": False}
    return http_json(
        f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
        f"?token={token}&timeout=600",
        {"Content-Type": "application/json"},
        data=json.dumps(payload).encode(), method="POST")


def normalise(platform: str, item: dict) -> dict:
    """Different actors, different field names; unavailable stays None, never 0."""
    if platform == "tiktok":
        return {
            "url": item.get("webVideoUrl"),
            "views": item.get("playCount"),
            "likes": item.get("diggCount"),
            "comments": item.get("commentCount"),
            "shares": item.get("shareCount"),
        }
    return {
        "url": item.get("url"),
        "views": item.get("videoPlayCount") or item.get("videoViewCount"),
        "likes": item.get("likesCount"),
        "comments": item.get("commentsCount"),
        "shares": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--limit", type=int, default=40, help="max URLs per platform per run")
    ap.add_argument("--platform", default="all", choices=["all", "tiktok", "instagram"])
    a = ap.parse_args()

    env = load_env()
    posts = fetch_posts(env, a.days)
    published = [p for p in posts if p.get("state") == "PUBLISHED" and p.get("releaseURL")]
    errored = [p for p in posts if p.get("state") == "ERROR"]
    print(f"POSTIZ window={a.days}d posts={len(posts)} published={len(published)} "
          f"errored={len(errored)}")

    wanted = ["tiktok", "instagram"] if a.platform == "all" else [a.platform]
    by_url = {}
    for p in published:
        plat = platform_of(p)
        if plat in wanted:
            by_url[p["releaseURL"]] = p

    now = dt.datetime.now(dt.timezone.utc)
    written = 0
    STATE.parent.mkdir(parents=True, exist_ok=True)

    for plat in wanted:
        urls = [u for u, p in by_url.items() if platform_of(p) == plat][:a.limit]
        if not urls:
            print(f"{plat}: no published URLs in window")
            continue
        try:
            items = scrape(env, plat, urls)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
            print(f"{plat}: scrape failed: {str(e)[:160]}", file=sys.stderr)
            continue

        # TikTok items come back from a profile walk, so they are matched to our posts
        # by the opening of the caption rather than by URL.
        caption_index = {}
        if plat == "tiktok":
            for u, p in by_url.items():
                if platform_of(p) != "tiktok":
                    continue
                head = "".join((p.get("content") or "").split())[:40]
                if head:
                    caption_index[head] = p

        got = 0
        with open(STATE, "a") as f:
            for item in items:
                m = normalise(plat, item)
                post = by_url.get(m["url"] or "")
                if post is None and plat == "tiktok":
                    head = "".join((item.get("text") or "").split())[:40]
                    post = caption_index.get(head)
                if not post:
                    continue
                published_at = post.get("publishDate")
                age_h = None
                if published_at:
                    try:
                        t = dt.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        age_h = round((now - t).total_seconds() / 3600, 1)
                    except ValueError:
                        pass
                integ = post.get("integration") or {}
                f.write(json.dumps({
                    "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "platform": plat,
                    "post_id": post.get("id"),
                    "account": integ.get("name") if isinstance(integ, dict) else None,
                    "url": m["url"],
                    "age_hours": age_h,
                    "views": m["views"],
                    "likes": m["likes"],
                    "comments": m["comments"],
                    "shares": m["shares"],
                }, ensure_ascii=False) + "\n")
                got += 1
                written += 1
        print(f"{plat}: requested={len(urls)} matched={got}")

    if errored:
        names = {}
        for p in errored:
            integ = p.get("integration") or {}
            n = integ.get("name") if isinstance(integ, dict) else "?"
            names[n] = names.get(n, 0) + 1
        print("ERROR-state posts nobody was watching: "
              + ", ".join(f"{k}={v}" for k, v in sorted(names.items())))

    print(f"WROTE {written} rows -> {STATE}")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
