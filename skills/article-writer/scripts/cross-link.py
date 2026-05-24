#!/usr/bin/env python3
"""
cross-link.py — Tweet "Just published <article-en-url>" via Postiz.

Reads:  ~/.openclaw/workspace/article-writer/published.json
Picks:  the most recent dev.to entry for today's date
Posts:  via Postiz to the tweet account configured in env

Env:
  POSTIZ_API_KEY              required for live POST
  ARTICLE_TWEET_ACCOUNT_EN    integration_id for the tweet account (default: build-in-public's @aniccaxxx)
  ARTICLE_DRY_RUN             "true" → log only
  ARTICLE_DATE                override target date
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Reuse the build-in-public retry helper
sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "build-in-public" / "scripts"))
try:
    from importlib import import_module
    rp = import_module("retry-postiz".replace("-", "_"))
    post_with_retry = rp.post_with_retry  # type: ignore
except Exception:
    post_with_retry = None  # type: ignore

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "article-writer"
PUBLISHED = WORKSPACE / "published.json"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "article-writer"
POSTIZ_BASE = os.environ.get("POSTIZ_BASE_URL", "https://app.postiz.com/api")
TWEET_ACCOUNT = os.environ.get("ARTICLE_TWEET_ACCOUNT_EN", "cmm6d7m5703rwpr0yr5vtme3w")
DRY_RUN = os.environ.get("ARTICLE_DRY_RUN", "false").lower() == "true"
API_KEY = os.environ.get("POSTIZ_API_KEY", "")


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"cross-link_{date.today():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def main() -> int:
    target = os.environ.get("ARTICLE_DATE", date.today().isoformat())
    if not PUBLISHED.exists():
        log("no published.json yet — nothing to cross-link")
        return 0
    history = json.loads(PUBLISHED.read_text())
    today_devto = [e for e in history if e.get("date") == target and e.get("platform") == "dev.to"]
    if not today_devto:
        log(f"no dev.to article published for {target} — skipping")
        return 0
    entry = today_devto[-1]
    url = entry["url"]
    title = entry.get("title", "today's article")
    body = f"Just published: {title}\n\n{url}\n\n#buildinpublic #agi"

    log(f"target_date={target} url={url} integration={TWEET_ACCOUNT} dry_run={DRY_RUN}")

    payload = {
        "posts": [{
            "integration": {"id": TWEET_ACCOUNT},
            "value": [{"content": body}],
        }],
        "type": "now",
    }

    if DRY_RUN:
        log("[DRY_RUN] would POST to Postiz /posts")
        log(f"[DRY_RUN] body: {body}")
        print(json.dumps({"dry_run": True, "url": url, "body": body}, indent=2, ensure_ascii=False))
        return 0

    if post_with_retry is None:
        log("ERROR: retry-postiz module not importable")
        return 3
    if not API_KEY:
        log("ERROR: POSTIZ_API_KEY not set")
        return 4

    try:
        result = post_with_retry(
            f"{POSTIZ_BASE}/posts", payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        log(f"OK posted: {result}")
        return 0
    except Exception as e:
        log(f"ERROR: {e}")
        return 5


if __name__ == "__main__":
    sys.exit(main())
