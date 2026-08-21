#!/usr/bin/env python3
"""tag-counts — measure REAL note.com hashtag popularity for candidate tags. Returns facts only;
which N (<=5) to actually pass to note-publish/publish-paid.py --tags is the calling agent's
judgment call (SKILL.md #73: "before acting on a recorded market decision, re-run the one call that
would falsify it" — a giant tag like #AI at 794k drowns a small article, but where exactly to draw
the line is per-article, not hardcoded here).

API: GET https://note.com/api/v2/hashtags/{tag} -> data.count. A 404 means the tag has never been
used on note and counts as 0 (not an error, not fatal). note's API sometimes rejects a bare python
User-Agent, so every request here sends a browser one.

usage:  tag-counts.py <tag1> <tag2> ...   (tag names WITHOUT the leading #, any number of them)
stdout: exactly one line, a JSON object {"tag": count, ...} in the order given.
stderr: one "tag=count" diagnostic line per tag, as it is measured.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def count_for(tag: str) -> int:
    url = "https://note.com/api/v2/hashtags/" + urllib.parse.quote(tag)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=15))
        return d["data"]["count"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 0
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("tags", nargs="+", help="tag names without the leading #")
    args = p.parse_args()

    out = {}
    for raw in args.tags:
        t = raw.lstrip("#").strip()
        if not t:
            continue
        out[t] = count_for(t)
        print(f"{t}={out[t]}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
