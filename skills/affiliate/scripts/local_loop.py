#!/usr/bin/env python3
"""Mac-local Affiliate wake and append-only receipts."""

import argparse
import fcntl
import json
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def append(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def elevenlabs_link(path):
    if not path.is_file() or path.stat().st_mode & 0o077:
        return None
    text = path.read_text(encoding="utf-8")
    section = re.search(r"(?ms)^## ElevenLabs\n.*?(?=^## |\Z)", text)
    if not section:
        return None
    match = re.search(r"(?m)^- Default affiliate link: `([^`]+)`$", section.group())
    if not match:
        return None
    link = match.group(1)
    parsed = urlparse(link)
    return link if parsed.scheme == "https" and parsed.hostname == "try.elevenlabs.io" else None


def browser_ready(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3) as response:
            return response.status == 200
    except OSError:
        return False


def wake(args):
    state = args.state.expanduser()
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (state / ".wake.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('{"state":"ALREADY_RUNNING"}')
        return 0
    link = elevenlabs_link(args.private_markdown.expanduser())
    browser = browser_ready(args.cdp_port)
    status = "READY_FOR_PUBLICATION" if link and browser else (
        "BROWSER_UNAVAILABLE" if link else "TRACKING_LINK_UNAVAILABLE"
    )
    event = {
        "event": "affiliate_wake",
        "provider": "elevenlabs",
        "status": status,
        "ts": int(time.time()),
    }
    append(state / "events.jsonl", event)
    atomic_json(state / "last-run.json", event)
    print(json.dumps(event, sort_keys=True, separators=(",", ":")))
    return 0


def placement(args):
    link = elevenlabs_link(args.private_markdown.expanduser())
    if not link:
        raise ValueError("verified ElevenLabs tracking link is unavailable")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,79}", args.placement):
        raise ValueError("invalid placement")
    state = args.state.expanduser()
    receipt = {
        "event": "placement_ready",
        "locale": args.locale,
        "placement": args.placement,
        "provider": "elevenlabs",
        "status": "TRACKING_LINK_VERIFIED",
        "ts": int(time.time()),
    }
    append(state / "placements.jsonl", receipt)
    print(link if args.print_url else json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="affiliate loop")
    parser.add_argument("command", choices=("wake", "placement"))
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument("--private-markdown", type=Path, default=Path("~/.config/anicca/affiliate-credentials.md"))
    parser.add_argument("--cdp-port", type=int, default=9324)
    parser.add_argument("--placement", default="article-1")
    parser.add_argument("--locale", choices=("en", "ja"), default="en")
    parser.add_argument("--print-url", action="store_true")
    args = parser.parse_args()
    return wake(args) if args.command == "wake" else placement(args)


if __name__ == "__main__":
    raise SystemExit(main())
