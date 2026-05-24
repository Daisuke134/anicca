#!/usr/bin/env python3
"""
pull-analytics.py — Postiz analytics fetcher for build-in-public.

Reads ~/.openclaw/workspace/build-in-public/sent_*.json (post URL + post_id),
calls Postiz GET /analytics/post/{post_id} for each, writes consolidated
~/.openclaw/workspace/build-in-public/postiz-cache.json with engagement metrics.

Cron: bip-postiz-pull @ 23:00 JST.
DRY_RUN: set BIP_DRY_RUN=true to skip live Postiz calls and emit fixture data.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request, error

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "build-in-public"
CACHE_PATH = WORKSPACE / "postiz-cache.json"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "build-in-public"

POSTIZ_BASE = os.environ.get("POSTIZ_BASE_URL", "https://app.postiz.com/api")
API_KEY = os.environ.get("POSTIZ_API_KEY", "")
DRY_RUN = os.environ.get("BIP_DRY_RUN", "true").lower() == "true"
LOOKBACK_DAYS = int(os.environ.get("BIP_LOOKBACK_DAYS", "14"))


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"pull-analytics_{datetime.now():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def load_sent_ledgers(days: int) -> list[dict]:
    """Read sent_YYYY-MM-DD.json files for the past N days."""
    posts: list[dict] = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        f = WORKSPACE / f"sent_{d}.json"
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text())
            entries = data if isinstance(data, list) else data.get("posts", [])
            for e in entries:
                if "post_id" in e or "id" in e:
                    posts.append({
                        "date": d,
                        "post_id": e.get("post_id") or e.get("id"),
                        "url": e.get("url") or e.get("post_url"),
                        "headline_formula": e.get("headline_formula"),
                        "body": e.get("body", "")[:120],
                    })
        except Exception as ex:
            log(f"WARN: failed to parse {f}: {ex}")
    return posts


def fetch_analytics(post_id: str) -> dict:
    if DRY_RUN:
        # Fixture: deterministic mock metrics so cache is populated for testing
        h = hash(post_id)
        return {
            "post_id": post_id,
            "impressions": 100 + (abs(h) % 900),
            "engagements": 5 + (abs(h) % 45),
            "likes": 2 + (abs(h) % 20),
            "replies": abs(h) % 5,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "_dry_run": True,
        }
    url = f"{POSTIZ_BASE}/analytics/post/{post_id}"
    req = request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            return {
                "post_id": post_id,
                **json.loads(resp.read().decode("utf-8")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except error.HTTPError as e:
        log(f"WARN: {post_id} → HTTP {e.code}")
        return {"post_id": post_id, "error": f"http_{e.code}"}
    except Exception as e:
        log(f"WARN: {post_id} → {e}")
        return {"post_id": post_id, "error": str(e)}


def main() -> int:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    log(f"=== bip-postiz-pull start (DRY_RUN={DRY_RUN}, lookback={LOOKBACK_DAYS}d) ===")

    sent = load_sent_ledgers(LOOKBACK_DAYS)
    log(f"loaded {len(sent)} sent post entries")

    if not DRY_RUN and not API_KEY:
        log("ERROR: POSTIZ_API_KEY not set (and not in DRY_RUN mode)")
        return 1

    cache: dict = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text())
        except Exception:
            cache = {}
    cache.setdefault("posts", {})
    cache["last_pulled_at"] = datetime.now(timezone.utc).isoformat()

    fetched = 0
    for entry in sent:
        pid = entry["post_id"]
        if not pid:
            continue
        metrics = fetch_analytics(pid)
        cache["posts"][pid] = {**entry, **metrics}
        fetched += 1
        if not DRY_RUN:
            time.sleep(0.5)  # be nice to Postiz

    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
    log(f"wrote {len(cache['posts'])} posts to {CACHE_PATH} ({fetched} fetched this run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
