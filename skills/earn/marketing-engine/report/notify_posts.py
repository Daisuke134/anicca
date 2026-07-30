#!/usr/bin/env python3
"""notify_posts.py — one tappable line per published post, and never a silent failure.

What arrived on Telegram before this was `label exit=N` plus a raw log tail: no link,
no account, no number. This sends the thing a human would actually act on — the public
URL — the moment a post goes out, and names every post that failed instead of letting
a quarter of the output vanish (23 of 106 posts were in ERROR state, unnoticed).

State is a jsonl of already-announced post ids, so a rerun never double-notifies.

  notify_posts.py [--hours 6] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

STATE = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_NOTIFY_STATE", "~/.openclaw/state/content-library/notified-posts.jsonl")))
ENV_FILE = pathlib.Path(os.path.expanduser("~/.openclaw/.env"))
POSTIZ = "https://api.postiz.com/public/v1"
TELEGRAM_TARGET = os.environ.get("MKT_TELEGRAM_TARGET", "8547730585")


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(errors="replace").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip())
    return env


def already_notified() -> set[str]:
    if not STATE.exists():
        return set()
    out = set()
    for line in STATE.read_text(errors="replace").splitlines():
        try:
            out.add(json.loads(line)["post_id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def fetch_posts(env, hours: int) -> list[dict]:
    key = env.get("POSTIZ_API_KEY")
    if not key:
        raise SystemExit("FATAL: POSTIZ_API_KEY missing")
    now = dt.datetime.now(dt.timezone.utc)
    q = urllib.parse.urlencode({
        "startDate": (now - dt.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "endDate": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": 200,
    })
    req = urllib.request.Request(f"{POSTIZ}/posts?{q}", headers={"Authorization": key})
    with urllib.request.urlopen(req, timeout=90) as r:
        body = json.load(r)
    return body if isinstance(body, list) else body.get("posts", [])


def send(message: str) -> bool:
    """openclaw owns the Telegram transport; a failed send must not look like success."""
    r = subprocess.run(
        ["openclaw", "message", "send", "--channel", "telegram",
         "--target", TELEGRAM_TARGET, "--message", message, "--json"],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"send failed rc={r.returncode}: {(r.stderr or r.stdout)[:200]}", file=sys.stderr)
        return False
    return True


def account_of(post: dict) -> str:
    integ = post.get("integration") or {}
    return (integ.get("name") if isinstance(integ, dict) else None) or "?"


def platform_of(post: dict) -> str:
    integ = post.get("integration") or {}
    ident = integ.get("providerIdentifier", "") if isinstance(integ, dict) else ""
    for name in ("tiktok", "instagram", "youtube"):
        if name in ident:
            return name
    return ident or "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    env = load_env()
    posts = fetch_posts(env, a.hours)
    seen = already_notified()

    new_pub = [p for p in posts
               if p.get("state") == "PUBLISHED" and p.get("releaseURL")
               and p.get("id") not in seen]
    new_err = [p for p in posts if p.get("state") == "ERROR" and p.get("id") not in seen]
    print(f"window={a.hours}h posts={len(posts)} new_published={len(new_pub)} "
          f"new_errors={len(new_err)}")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    sent = 0
    for p in new_pub:
        head = " ".join((p.get("content") or "").split())[:70]
        msg = (f"📤 {account_of(p)} · {platform_of(p)}\n"
               f"{head}\n{p['releaseURL']}")
        if a.dry_run:
            print("--- would send ---\n" + msg)
            continue
        if send(msg):
            with open(STATE, "a") as f:
                f.write(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"), "post_id": p["id"], "kind": "published"}) + "\n")
            sent += 1

    if new_err:
        by_account: dict[str, int] = {}
        for p in new_err:
            by_account[account_of(p)] = by_account.get(account_of(p), 0) + 1
        msg = ("⚠️ posts failed to publish\n"
               + "\n".join(f"{k}: {v}" for k, v in sorted(by_account.items())))
        if a.dry_run:
            print("--- would send ---\n" + msg)
        elif send(msg):
            with open(STATE, "a") as f:
                for p in new_err:
                    f.write(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"), "post_id": p["id"], "kind": "error"}) + "\n")
            sent += 1

    print(f"sent={sent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
