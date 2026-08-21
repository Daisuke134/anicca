#!/usr/bin/env python3
"""Add a path back to us on already-published dev.to pieces that have none.

Measured 2026-07-27: the traffic and the doors are on different articles.
The top twenty pieces by views carry 2,538 of 3,314 total views and not one
of them mentions substack, note, aniccaai.com or the repository. The five
newest pieces mostly do carry a path — and have zero views. A reader arrives
on a how-to from search, gets helped, and is shown nowhere to go, which is why
conversion is structurally zero regardless of how good the writing gets.

This appends one closing block to old pieces that lack it. It does NOT touch
the daily publishing flow, and it never rewrites body text a human wrote: it
appends, so the worst case is a redundant footer rather than a mangled piece.

DRY RUN IS THE DEFAULT. Modifying already-public articles is outward-facing
and effectively irreversible in the eyes of anyone who already read them, so
`--apply` has to be asked for explicitly and the diff printed first.

  retrofit_cta.py plan            # what would change, and nothing else
  retrofit_cta.py plan --limit 5
  retrofit_cta.py apply --limit 5 # actually PUT, one at a time
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

LIST_URL = "https://dev.to/api/articles/me/published?per_page=100"
UA = "anicca-cta-retrofit/1.0"
TIMEOUT = 25

# Any of these already counts as a door; a piece carrying one is left alone.
PATH_MARKERS = ("aniccaai.com", "substack", "note.com", "github.com/daisuke134")

# Written to be useful rather than promotional: the reader arrived with a
# problem, so the offer is more of the same kind of help, not a pitch.
CTA_BLOCK = """

---

I write up one of these every day — real failures, the measurements behind
them, and what actually fixed it. The archive and the notes live at
https://aniccaai.com/ if this one saved you time.
"""


def api(url: str, key: str, *, method: str = "GET", payload: dict | None = None) -> dict | list:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "api-key": key,
            "User-Agent": UA,
            "Accept": "application/vnd.forem.api-v1+json",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def needs_cta(body: str) -> bool:
    lowered = body.lower()
    return not any(marker in lowered for marker in PATH_MARKERS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("--limit", type=int, default=20, help="most-viewed N to consider")
    args = parser.parse_args(argv)

    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        print("DEVTO_API_KEY is not set", file=sys.stderr)
        return 1

    rows = api(LIST_URL, key)
    if not isinstance(rows, list):
        print("unexpected list payload", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: -(r.get("page_views_count") or 0))

    planned, skipped, views = [], 0, 0
    for row in rows[: args.limit]:
        try:
            article = api(f"https://dev.to/api/articles/{row['id']}", key)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"skip {row['id']}: {exc}", file=sys.stderr)
            continue
        body = article.get("body_markdown") or ""
        if not needs_cta(body):
            skipped += 1
        else:
            planned.append((row, body))
            views += row.get("page_views_count") or 0
        time.sleep(0.3)

    print(json.dumps({
        "considered": min(args.limit, len(rows)),
        "already_have_a_path": skipped,
        "would_change": len(planned),
        "views_behind_them": views,
        "mode": args.command,
    }, ensure_ascii=False))
    for row, _ in planned:
        print(f"  {row.get('page_views_count'):>5} views  {row['title'][:60]}")

    if args.command == "plan":
        print("\n--- block that would be appended ---")
        print(CTA_BLOCK.strip())
        return 0

    changed = 0
    for row, body in planned:
        try:
            api(
                f"https://dev.to/api/articles/{row['id']}",
                key,
                method="PUT",
                payload={"article": {"body_markdown": body + CTA_BLOCK}},
            )
            changed += 1
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f"failed {row['id']}: {exc}", file=sys.stderr)
        time.sleep(1.0)
    print(json.dumps({"applied": changed, "of": len(planned)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
