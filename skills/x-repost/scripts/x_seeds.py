#!/usr/bin/env python3
"""The well of primary-source facts the loop is allowed to quote, and its cooldown.

29 posts drew on three anecdotes because config/voice.md held five seeds and never grew. A file
the loop only reads is a well with a bottom. This makes the well state: seeds are added as they are
measured, marked when used, and withheld for a cooldown afterwards so the same story cannot come
back out next hour.

  --available            print seeds that are usable right now (JSON list)
  --mark <id>            record that a seed was published
  --add                  append one seed read as JSON on stdin
  --bootstrap <voice.md> import the original table once, if the well is empty
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

COOLDOWN_DAYS = 14


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def write_all(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def available(rows: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        used = r.get("last_used_at")
        if used:
            try:
                if now - datetime.fromisoformat(used).astimezone(timezone.utc) < timedelta(days=COOLDOWN_DAYS):
                    continue
            except ValueError:
                pass
        out.append({"id": r["id"], "fact": r["fact"], "measured_on": r.get("measured_on", ""),
                    "times_used": r.get("times_used", 0)})
    # Never used first, then least recently used: variety is the whole point of the cooldown.
    out.sort(key=lambda r: (r["times_used"],))
    return out


def bootstrap(path: Path, voice_md: Path) -> int:
    if read(path):
        return 0
    rows, n = [], 0
    for line in voice_md.read_text(encoding="utf-8").splitlines():
        # The date column is prose, not a date: one seed is measured over a range ("2026-07-19〜07-30").
        # Matching a strict date silently dropped it, which is the same class of bug as the missing
        # like counts -- a parser that quietly discards a row it does not recognise.
        m = re.match(r"^\|\s*(v\d+)\s*\|\s*(.+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            n += 1
            rows.append({"id": m.group(1), "fact": m.group(2), "measured_on": m.group(3),
                         "source": "config/voice.md", "times_used": 0, "last_used_at": None})
    if rows:
        write_all(path, rows)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--available", action="store_true")
    ap.add_argument("--mark")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--bootstrap")
    args = ap.parse_args()

    path = Path(args.seeds).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    if args.bootstrap:
        print(json.dumps({"imported": bootstrap(path, Path(args.bootstrap).expanduser())}))
        return

    rows = read(path)

    if args.available:
        json.dump(available(rows), sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    if args.mark:
        now = datetime.now(timezone.utc).isoformat()
        hit = False
        for r in rows:
            if r["id"] == args.mark:
                r["times_used"] = r.get("times_used", 0) + 1
                r["last_used_at"] = now
                hit = True
        write_all(path, rows)
        print(json.dumps({"marked": args.mark, "found": hit}))
        return

    if args.add:
        incoming = json.load(sys.stdin)
        fact = (incoming.get("fact") or "").strip()
        if not fact:
            print(json.dumps({"added": False, "reason": "empty fact"}))
            return
        # A near-duplicate seed reopens the well only in appearance, so reject on the fact text.
        norm = re.sub(r"\s+", "", fact)
        if any(re.sub(r"\s+", "", r.get("fact", "")) == norm for r in rows):
            print(json.dumps({"added": False, "reason": "duplicate"}))
            return
        nid = f"v{max([int(r['id'][1:]) for r in rows if r.get('id', 'v0')[1:].isdigit()] + [0]) + 1:03d}"
        rows.append({"id": nid, "fact": fact,
                     "measured_on": incoming.get("measured_on", datetime.now().strftime("%Y-%m-%d")),
                     "source": incoming.get("source", "unknown"),
                     "times_used": 0, "last_used_at": None})
        write_all(path, rows)
        print(json.dumps({"added": True, "id": nid}, ensure_ascii=False))
        return

    ap.error("one of --available / --mark / --add / --bootstrap is required")


if __name__ == "__main__":
    main()
