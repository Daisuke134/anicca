#!/usr/bin/env python3
"""attribution.py — give every marketing account its own App Store campaign link.

Without this the loop is blind: a post can be traced to views and nothing else. The
public failure case is documented — one operator drove 10M TikTok views to 5 signups
because the funnel was never instrumented (zenn.dev/kyoneno, 2025-10-14).

Apple's own App Analytics campaign links carry two query parameters:
  pt = provider token (the App Store Connect provider/vendor number)
  ct = campaign token (free text — we use the marketing account handle)
They need no API object, so a link exists the moment an account exists, and App
Analytics groups installs by `ct` under Acquisition → Campaigns.

  link    --app-id 6755129214 --account larry-en-v1 [--provider 93486075] [--record]
  list    [--product aniccaios]
  verify  --account larry-en-v1     (re-resolve the stored link against the store)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

STATE = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_ATTRIBUTION_STATE",
    "~/.openclaw/state/content-library/attribution-links.jsonl")))
STORE_BASE = "https://apps.apple.com/app/id{app_id}"


def _rows() -> list[dict]:
    if not STATE.exists():
        return []
    out = []
    for line in STATE.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def latest_for(account: str) -> dict | None:
    hits = [r for r in _rows() if r.get("account") == account]
    return hits[-1] if hits else None


def build_link(app_id: str, account: str, provider: str) -> str:
    query = urllib.parse.urlencode({"pt": provider, "ct": account, "mt": "8"})
    return f"{STORE_BASE.format(app_id=app_id)}?{query}"


def resolves(url: str) -> tuple[bool, int]:
    """The store answers 200/30x for a real app id; anything else is a broken link."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200 <= r.status < 400, r.status
    except urllib.error.HTTPError as e:
        return False, e.code
    except urllib.error.URLError:
        return False, 0


def cmd_link(a) -> int:
    provider = a.provider or os.environ.get("ASC_VENDOR_NUMBER", "")
    if not provider:
        print("FATAL: no provider token (--provider or ASC_VENDOR_NUMBER); "
              "a link without pt is not attributable", file=sys.stderr)
        return 2

    url = build_link(a.app_id, a.account, provider)
    ok, status = resolves(url)
    if not ok:
        print(f"FATAL: store did not accept the link (HTTP {status}): {url}", file=sys.stderr)
        return 1

    if a.record:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE, "a") as f:
            f.write(json.dumps({
                "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "product": a.product or "",
                "app_id": a.app_id,
                "account": a.account,
                "provider_token": provider,
                "campaign_token": a.account,
                "url": url,
                "verified_http": status,
            }) + "\n")
    print(url)
    return 0


def cmd_list(a) -> int:
    rows = _rows()
    if a.product:
        rows = [r for r in rows if r.get("product") == a.product]
    seen = {}
    for r in rows:
        seen[r.get("account")] = r
    for acct, r in sorted(seen.items()):
        print(f"{acct}\t{r.get('product','')}\t{r.get('url')}")
    if not seen:
        print("(no campaign links recorded yet)")
    return 0


def cmd_verify(a) -> int:
    row = latest_for(a.account)
    if not row:
        print(f"FATAL: no recorded link for {a.account}", file=sys.stderr)
        return 1
    ok, status = resolves(row["url"])
    print(f"{a.account} http={status} {'OK' if ok else 'BROKEN'} {row['url']}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("link")
    l.add_argument("--app-id", required=True)
    l.add_argument("--account", required=True)
    l.add_argument("--product", default="")
    l.add_argument("--provider", default="")
    l.add_argument("--record", action="store_true")
    l.set_defaults(func=cmd_link)

    ls = sub.add_parser("list")
    ls.add_argument("--product", default="")
    ls.set_defaults(func=cmd_list)

    v = sub.add_parser("verify")
    v.add_argument("--account", required=True)
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
