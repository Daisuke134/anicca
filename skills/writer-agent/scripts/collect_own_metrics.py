#!/usr/bin/env python3
"""Collect what our OWN published pieces actually earned, so the judge can be audited.

Why this exists: beat rate asks a judge which headline a stranger would click.
Nothing so far checks whether that judge is right. If its preferences do not
predict the reactions our own posts actually get, then every night of training
is optimising a judge's taste rather than a reader's behaviour -- the same
closed loop the rubric judge created, wearing a better costume (spec 47
sections 19.3 and 21.2 T9).

This collects only dev.to for now, because it answers over an authenticated
API with no browser. X and note carry the larger audiences but need the shared
browser, which is reserved for publishing, so they are deliberately absent
rather than half-implemented. A source that is missing is visible; a source
that is guessed is not.

Rows are append-only under state/own-metrics.jsonl:
  {"ts": ..., "platform": "devto", "id": ..., "url": ..., "title": ...,
   "published_at": ..., "metric": {"reactions": N, "comments": N, "views": N|null},
   "age_hours": float}

`age_hours` matters: reactions accumulate, so comparing a piece published two
hours ago against one from last week measures elapsed time, not writing. Any
later analysis must bucket by age before it compares anything.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://dev.to/api/articles/me/published?per_page=100"
TIMEOUT = 25
UA = "anicca-own-metrics/1.0 (+writer-loop judge calibration)"


def fetch_devto(api_key: str) -> list[dict]:
    request = urllib.request.Request(
        API, headers={"api-key": api_key, "User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = json.load(response)
    return payload if isinstance(payload, list) else []


def normalise(row: dict, *, now: datetime) -> dict | None:
    url = str(row.get("url") or "").strip()
    title = str(row.get("title") or "").strip()
    if not url or not title:
        return None
    published = str(row.get("published_at") or "")
    age_hours = None
    if published:
        try:
            stamp = datetime.fromisoformat(published.replace("Z", "+00:00"))
            age_hours = round((now - stamp).total_seconds() / 3600.0, 2)
        except ValueError:
            age_hours = None
    return {
        "ts": now.isoformat(),
        "platform": "devto",
        "id": f"devto:{row.get('id')}",
        "url": url,
        "title": title,
        "published_at": published,
        # views are absent from this endpoint; recorded as null rather than 0,
        # because a missing measurement and a measured zero are different facts.
        "metric": {
            "reactions": int(row.get("public_reactions_count") or 0),
            "comments": int(row.get("comments_count") or 0),
            "views": row.get("page_views_count"),
        },
        "age_hours": age_hours,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "stats"))
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "state" / "own-metrics.jsonl"),
    )
    args = parser.parse_args(argv)
    out = Path(args.out)

    if args.command == "stats":
        if not out.exists():
            print(json.dumps({"rows": 0, "reason": "no metrics collected yet"}))
            return 0
        rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        latest: dict[str, dict] = {}
        for row in rows:
            latest[row["id"]] = row
        reactions = [r["metric"]["reactions"] for r in latest.values()]
        print(json.dumps({
            "rows": len(rows),
            "pieces": len(latest),
            "reactions_total": sum(reactions),
            "reactions_max": max(reactions) if reactions else 0,
            "reactions_zero": sum(1 for value in reactions if value == 0),
        }, ensure_ascii=False))
        return 0

    api_key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not api_key:
        print(json.dumps({"ok": False, "reason": "DEVTO_API_KEY is not set"}), file=sys.stderr)
        return 1
    try:
        raw = fetch_devto(api_key)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as exc:
        # A collection failure is a missing datapoint, never a zero.
        print(json.dumps({"ok": False, "reason": f"devto fetch failed: {exc}"}), file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    rows = [row for row in (normalise(item, now=now) for item in raw) if row]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "written": len(rows), "path": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
