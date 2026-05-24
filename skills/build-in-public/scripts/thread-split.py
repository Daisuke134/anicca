#!/usr/bin/env python3
"""
thread-split.py — Split a long tweet body into a "1/n", "2/n", ... thread.

Used by build-in-public when the daily post exceeds 280 chars.

Usage:
  echo "$BODY" | python3 thread-split.py
  python3 thread-split.py --file body.txt
  python3 thread-split.py --max 270 --file body.txt   # custom max chars

Strategy:
  - Reserve 6 chars per tweet for " (i/n)" suffix.
  - Greedy split on paragraph (\\n\\n) → sentence (。/. ?) → space → hard cut.
  - Never break mid-word, never break inside a URL.
  - Output JSON list of strings to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

URL_RE = re.compile(r"https?://\S+")
SENT_END = re.compile(r"(?<=[。．.!?])\s+")


def chunks(text: str, hard_max: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= hard_max:
        return [text]

    # Step 1: paragraph split
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        if len(p) <= hard_max:
            units.append(p)
        else:
            # Step 2: sentence split, but protect URLs
            sentences = SENT_END.split(p)
            buf = ""
            for s in sentences:
                if len(buf) + len(s) + 1 <= hard_max:
                    buf = (buf + " " + s).strip() if buf else s
                else:
                    if buf:
                        units.append(buf)
                    if len(s) <= hard_max:
                        buf = s
                    else:
                        # Step 3: word-level fallback
                        words = s.split(" ")
                        wbuf = ""
                        for w in words:
                            if len(wbuf) + len(w) + 1 <= hard_max:
                                wbuf = (wbuf + " " + w).strip() if wbuf else w
                            else:
                                if wbuf:
                                    units.append(wbuf)
                                wbuf = w if len(w) <= hard_max else w[:hard_max]
                        if wbuf:
                            buf = wbuf
                        else:
                            buf = ""
            if buf:
                units.append(buf)

    # Pack units into tweets ≤ hard_max
    tweets: list[str] = []
    cur = ""
    for u in units:
        candidate = (cur + "\n\n" + u).strip() if cur else u
        if len(candidate) <= hard_max:
            cur = candidate
        else:
            if cur:
                tweets.append(cur)
            cur = u
    if cur:
        tweets.append(cur)
    return tweets


def annotate(tweets: list[str]) -> list[str]:
    n = len(tweets)
    if n <= 1:
        return tweets
    return [f"{t} ({i+1}/{n})" for i, t in enumerate(tweets)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=274, help="max chars per tweet (280 - 6 for suffix)")
    ap.add_argument("--file", type=str, default="-", help="input file or '-' for stdin")
    args = ap.parse_args()

    if args.file == "-":
        body = sys.stdin.read()
    else:
        body = open(args.file, encoding="utf-8").read()

    parts = annotate(chunks(body, args.max))
    print(json.dumps(parts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
