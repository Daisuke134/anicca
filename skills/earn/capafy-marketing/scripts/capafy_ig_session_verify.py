#!/usr/bin/env python3
"""Verify a newly appended browser-owned Instagram session without logging in."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--credential", type=Path, required=True)
    parser.add_argument("--handle", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    rows = json.loads(args.accounts.read_text(encoding="utf-8"))
    matches = [row for row in rows if isinstance(row, dict) and row.get("handle") == args.handle]
    if len(matches) != 1:
        raise SystemExit("expected exactly one appended account row")
    row = matches[0]
    if row.get("status") != "warming" or row.get("session_owner") != "browser":
        raise SystemExit("account row is not a browser-owned warming session")
    if int(row.get("port") or 0) != args.port:
        raise SystemExit("account row port does not match the live browser")

    credential = json.loads(args.credential.read_text(encoding="utf-8"))
    if credential.get("username") != args.handle or not credential.get("pw"):
        raise SystemExit("credential file does not match the new handle")

    with urlopen(f"http://127.0.0.1:{args.port}/json/list", timeout=8) as response:
        tabs = json.load(response)
    instagram_tabs = []
    for tab in tabs if isinstance(tabs, list) else []:
        parsed = urlparse(str(tab.get("url") or ""))
        if parsed.hostname not in {"instagram.com", "www.instagram.com"}:
            continue
        if parsed.path.startswith(("/accounts/login", "/challenge")):
            continue
        instagram_tabs.append(tab)
    if not instagram_tabs:
        raise SystemExit("no authenticated-looking Instagram tab exists in the isolated browser")
    print(json.dumps({"verified": True, "handle": args.handle, "session_owner": "browser"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
