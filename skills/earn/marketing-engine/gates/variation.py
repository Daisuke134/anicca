#!/usr/bin/env python3
"""variation.py — refuse to publish the same thing twice.

Why: `fixed-strings-*.json` pinned one hook and one background per variant, so every
post from a variant was visually and verbally identical no matter which library card
supplied the body text. Deduping by `source_id` (what run-account.sh already does)
does not catch this: the card rotates, the visible hook does not.

This module owns the "is it actually different" judgment for every marketing loop.

Sub-commands
  pick-hook  --pool-json <file> --account <acct> [--history <path>] [--days 14]
      Print a hook from the pool that this account has not used inside the window.
      Exit 3 when the whole pool is inside the window (the caller must not post).

  check-hook --hook <text> --account <acct> [--history <path>] [--days 14]
      Exit 1 if that hook (normalised) is already in the window.

  pick-bg    --pool <dir|json-list> --account <acct> [--state <path>] [--days 7]
      Least-recently-used background for the account, so a pool of N images cycles
      instead of one file being burned into every slide. Records the choice.

Normalisation is deliberate: case, whitespace, punctuation, emoji and hashtags are
stripped before comparing, because "5 signs you are healing" and "5 SIGNS YOU'RE
HEALING!! ✨ #healing" are the same hook to a viewer and to the algorithm.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import pathlib
import re
import sys
import unicodedata

DEFAULT_HISTORY = os.path.expanduser(
    os.environ.get("MKT_ACCOUNT_HISTORY",
                   "~/.openclaw/state/content-library/account-history.jsonl"))
DEFAULT_BG_STATE = os.path.expanduser(
    os.environ.get("MKT_BG_STATE",
                   "~/.openclaw/state/content-library/.bg-usage.jsonl"))

_STRIP = re.compile(r"[\s\W_]+", re.UNICODE)
_HASHTAG = re.compile(r"#\S+")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

# Contractions are expanded before stripping punctuation, otherwise "you're" and
# "you are" normalise to different strings and the same hook slips through twice.
_CONTRACTIONS = [
    ("you're", "you are"), ("you've", "you have"), ("you'll", "you will"),
    ("i'm", "i am"), ("i've", "i have"), ("it's", "it is"), ("that's", "that is"),
    ("don't", "do not"), ("doesn't", "does not"), ("didn't", "did not"),
    ("can't", "cannot"), ("won't", "will not"), ("isn't", "is not"),
    ("aren't", "are not"), ("they're", "they are"), ("we're", "we are"),
    ("here's", "here is"), ("what's", "what is"), ("let's", "let us"),
]
# Near-identical is still identical to a viewer, so compare with a ratio too.
SIMILARITY_THRESHOLD = float(os.environ.get("MKT_HOOK_SIMILARITY", "0.85"))


def normalize(text: str) -> str:
    """Collapse a hook to its comparable core."""
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = _HASHTAG.sub(" ", t)
    for short, long in _CONTRACTIONS:
        t = t.replace(short, long)
    return _STRIP.sub("", t)


def is_duplicate(hook: str, used: set[str]) -> str | None:
    """Return the colliding hook when `hook` repeats something in `used`."""
    key = normalize(hook)
    if not key:
        return None
    if key in used:
        return key
    for other in used:
        if difflib.SequenceMatcher(None, key, other).ratio() >= SIMILARITY_THRESHOLD:
            return other
    return None


def _rows(path: str):
    p = pathlib.Path(path)
    if not p.exists():
        return
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line, strict=False)
        except json.JSONDecodeError:
            continue


def _parse_ts(value: str):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def recent_hooks(account: str, history: str, days: int) -> set[str]:
    cutoff = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=days)
    out = set()
    for row in _rows(history):
        if row.get("account") != account:
            continue
        ts = _parse_ts(row.get("ts") or row.get("posted_at") or "")
        if ts is not None and ts < cutoff:
            continue
        hook = normalize(row.get("hook", ""))
        if hook:
            out.add(hook)
    return out


def last_used_backgrounds(account: str, state: str) -> dict[str, str]:
    """background path -> most recent ISO timestamp for this account."""
    seen: dict[str, str] = {}
    for row in _rows(state):
        if row.get("account") != account:
            continue
        bg, ts = row.get("background"), row.get("ts")
        if bg and ts and ts >= seen.get(bg, ""):
            seen[bg] = ts
    return seen


def expand_pool(spec: str) -> list[str]:
    """A pool is a directory of images or a JSON list of paths."""
    text = spec.strip()
    if text.startswith("["):
        entries = json.loads(text)
    else:
        p = pathlib.Path(os.path.expanduser(text))
        if p.is_dir():
            entries = [str(f) for f in sorted(p.iterdir())
                       if f.suffix.lower() in IMAGE_SUFFIXES]
        elif p.is_file() and p.suffix.lower() == ".json":
            entries = json.loads(p.read_text())
        else:
            entries = [text]
    return [os.path.expanduser(e) for e in entries]


def cmd_pick_hook(a) -> int:
    pool = json.loads(pathlib.Path(a.pool_json).read_text()) if a.pool_json != "-" \
        else json.load(sys.stdin)
    if isinstance(pool, dict):
        pool = pool.get("slide1_hook_pool") or []
    pool = [h for h in pool if str(h).strip()]
    if not pool:
        print("FATAL: hook pool is empty", file=sys.stderr)
        return 2

    used = recent_hooks(a.account, a.history, a.days)
    fresh = [h for h in pool if not is_duplicate(h, used)]
    if not fresh:
        print(f"FATAL: all {len(pool)} pooled hooks were used by {a.account} "
              f"within {a.days}d — widen the pool instead of repeating", file=sys.stderr)
        return 3
    print(fresh[0])
    return 0


def cmd_check_hook(a) -> int:
    used = recent_hooks(a.account, a.history, a.days)
    collision = is_duplicate(a.hook, used)
    if collision:
        print(f"DUPLICATE hook for {a.account} within {a.days}d: {a.hook!r} "
              f"collides with {collision!r}", file=sys.stderr)
        return 1
    print("OK")
    return 0


def cmd_pick_bg(a) -> int:
    pool = expand_pool(a.pool)
    missing = [p for p in pool if not os.path.isfile(p)]
    if missing:
        print(f"FATAL: background(s) missing: {', '.join(missing)}", file=sys.stderr)
        return 2
    if not pool:
        print("FATAL: background pool is empty", file=sys.stderr)
        return 2

    last = last_used_backgrounds(a.account, a.state)
    chosen = min(pool, key=lambda p: (last.get(p, ""), p))
    if a.record:
        with open(a.state, "a") as f:
            f.write(json.dumps({
                "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "account": a.account,
                "background": chosen,
            }) + "\n")
    print(chosen)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    ph = sub.add_parser("pick-hook")
    ph.add_argument("--pool-json", required=True)
    ph.add_argument("--account", required=True)
    ph.add_argument("--history", default=DEFAULT_HISTORY)
    ph.add_argument("--days", type=int, default=14)
    ph.set_defaults(func=cmd_pick_hook)

    ch = sub.add_parser("check-hook")
    ch.add_argument("--hook", required=True)
    ch.add_argument("--account", required=True)
    ch.add_argument("--history", default=DEFAULT_HISTORY)
    ch.add_argument("--days", type=int, default=14)
    ch.set_defaults(func=cmd_check_hook)

    pb = sub.add_parser("pick-bg")
    pb.add_argument("--pool", required=True)
    pb.add_argument("--account", required=True)
    pb.add_argument("--state", default=DEFAULT_BG_STATE)
    pb.add_argument("--days", type=int, default=7)
    pb.add_argument("--record", action="store_true")
    pb.set_defaults(func=cmd_pick_bg)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
