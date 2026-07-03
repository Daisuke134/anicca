#!/usr/bin/env python3
"""REQ-009: URL-deduplicated, null-guarded post count for the clip-earn ledger.

Used by monitor.sh instead of a raw non-null-post_url line count, which double-counts
a true-positive post and its false-positive duplicate (the real 2026-07-03 incident:
lines 2/3 of the ledger share the IDENTICAL post_url after post_reel.py's before/after
reel-diff race condition misreported an existing post as new).
"""
import json


def count_confirmed_posts(lines):
    """PURE. lines = iterable of raw ledger JSONL strings (already read, not a file path
    -- callers must pass a FROZEN copy in tests, never the live ledger path directly)."""
    urls = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        status = d.get("status")
        post_url = d.get("post_url")
        if status == "posted":
            if post_url:
                urls.add(post_url)
        elif status is None:
            # old-format line (pre-REQ-005/006): non-null post_url, not a false-positive correction
            if post_url and not d.get("false_positive_corrected"):
                urls.add(post_url)
        # status == "unverified" (or any other new-format status) never contributes a post_url
    return len(urls)
