#!/usr/bin/env python3
"""
post-devto.py — POST a markdown draft to dev.to.

Reads:  ~/.openclaw/workspace/article-writer/drafts/YYYY-MM-DD/en.md
POST:   https://dev.to/api/articles  (header: api-key)
Writes: ~/.openclaw/workspace/article-writer/published.json (append)

Frontmatter must include `title`, `tags`. The script flips `published: true`
unless ARTICLE_DRY_RUN=true (in which case it leaves it false and skips POST).

Env:
  DEVTO_API_KEY        required for live POST
  ARTICLE_DRY_RUN      "true" → skip POST, log only (default: false)
  ARTICLE_DATE         override target draft date (YYYY-MM-DD)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib import request, error

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "article-writer"
PUBLISHED = WORKSPACE / "published.json"
LOG_DIR = Path.home() / ".openclaw" / "logs" / "article-writer"
DEVTO_URL = "https://dev.to/api/articles"
API_KEY = os.environ.get("DEVTO_API_KEY", "")
DRY_RUN = os.environ.get("ARTICLE_DRY_RUN", "false").lower() == "true"


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with (LOG_DIR / f"post-devto_{date.today():%Y-%m-%d}.log").open("a") as fh:
        fh.write(line + "\n")


def parse_frontmatter(md: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", md, re.DOTALL)
    if not m:
        return {}, md
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, m.group(2)


def main() -> int:
    target = os.environ.get("ARTICLE_DATE", date.today().isoformat())
    draft = WORKSPACE / "drafts" / target / "en.md"
    if not draft.exists():
        log(f"ERROR: draft not found: {draft}")
        return 2

    fm, body = parse_frontmatter(draft.read_text(encoding="utf-8"))
    title = fm.get("title", f"Building Anicca — {target}")
    tags_raw = fm.get("tags", "agi,opensource,ai,automation")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()][:4]

    article = {
        "article": {
            "title": title,
            "published": not DRY_RUN,
            "body_markdown": body.strip(),
            "tags": tags,
        }
    }

    log(f"target_date={target} title={title!r} tags={tags} body_len={len(body)} dry_run={DRY_RUN}")

    if DRY_RUN:
        log("[DRY_RUN] skipping POST to dev.to")
        log(f"[DRY_RUN] would POST {len(json.dumps(article))} bytes to {DEVTO_URL}")
        print(json.dumps({"dry_run": True, "title": title, "tags": tags, "body_chars": len(body)}, indent=2))
        return 0

    if not API_KEY:
        log("ERROR: DEVTO_API_KEY not set")
        return 3

    body_bytes = json.dumps(article).encode("utf-8")
    req = request.Request(
        DEVTO_URL, data=body_bytes, method="POST",
        headers={"Content-Type": "application/json", "api-key": API_KEY},
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        log(f"HTTPError {e.code}: {e.read().decode('utf-8','replace')[:300]}")
        return 4
    except Exception as e:
        log(f"ERROR: {e}")
        return 5

    url = data.get("url") or data.get("canonical_url") or "?"
    log(f"OK posted: {url}")

    history = []
    if PUBLISHED.exists():
        try:
            history = json.loads(PUBLISHED.read_text())
        except Exception:
            history = []
    history.append({
        "date": target, "platform": "dev.to", "title": title, "url": url,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    PUBLISHED.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(json.dumps({"url": url, "title": title}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
