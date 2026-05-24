#!/usr/bin/env python3
"""
public-tweet.py — post the monthly donation total to X via Postiz.

Reads the run-YYYY-MM.json for the prior month, composes a single English
tweet, and POSTs to Postiz REST. If `donation.tweet_via_buildinpublic=true`
(default), it just queues a request file under
`~/.openclaw/workspace/build-in-public/queued-donation-tweets/` for the
build-in-public skill to pick up — avoids duplicating Postiz infra and
rate-limit budgets. If false, it posts directly.

DRY_RUN: never POSTs; writes the would-be tweet to the run state instead.
"""

from __future__ import annotations

import json
import os
import sys
import datetime as dt
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    HOME,
    is_dry_run,
    load_env_files,
    load_wizard_config,
    prior_month_period,
    read_run_state,
    write_run_state,
)


def compose_tweet(ctx: dict) -> str:
    if ctx.get("anonymize_amount"):
        body = (
            f"This month, Anicca donated to charities working to reduce suffering. "
            f"Tip the empire: {ctx['receipt_host']}"
        )
    else:
        body = (
            f"This month's Anicca Fund: ${ctx['total_amount_usd']:.2f} → "
            f"{len(ctx['transfers'])} recipient(s) working to reduce suffering. "
            f"Receipt: {ctx['receipt_host']}/{ctx['period']}"
        )
    # Trim defensively to ~270 chars
    if len(body) > 270:
        body = body[:267] + "..."
    return body


def post_via_buildinpublic(period_label: str, tweet: str) -> tuple[bool, str]:
    queue_dir = HOME / ".openclaw" / "workspace" / "build-in-public" / "queued-donation-tweets"
    queue_dir.mkdir(parents=True, exist_ok=True)
    fp = queue_dir / f"{period_label}.json"
    fp.write_text(json.dumps({
        "period": period_label,
        "queued_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tweet": tweet,
        "source_skill": "donation",
    }, ensure_ascii=False, indent=2))
    return True, f"queued for build-in-public: {fp}"


def post_via_postiz(tweet: str, integration_id: str) -> tuple[bool, str]:
    api_key = os.environ.get("POSTIZ_API_KEY", "")
    if not api_key:
        return False, "POSTIZ_API_KEY not set"
    if not integration_id:
        return False, "POSTIZ_X_INTEGRATION_ID not set"
    body = json.dumps({
        "type": "now",
        "shortLink": False,
        "posts": [{
            "integration": {"id": integration_id},
            "value": [{"content": tweet}],
            "settings": {"__type": "twitter"},
        }],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.postiz.com/public/v1/posts",
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            return True, data[:200]
    except Exception as e:
        return False, f"postiz failed: {e}"


def main() -> int:
    load_env_files()
    cfg = load_wizard_config()
    period_label, _, _ = prior_month_period()
    state = read_run_state(period_label)
    if not state:
        sys.stderr.write("[public-tweet] no run state — run earlier scripts first\n")
        return 2

    ctx = {
        "period": period_label,
        "total_amount_usd": float(state.get("total_amount_usd") or 0),
        "transfers": state.get("transfers") or [],
        "receipt_host": cfg["receipt_host"],
        "anonymize_amount": cfg["anonymize_amount"],
    }
    tweet = compose_tweet(ctx)

    if is_dry_run():
        write_run_state(period_label, {
            "tweet_status": "dry_run",
            "tweet_text": tweet,
        })
        sys.stderr.write(f"[public-tweet] DRY_RUN — would post: {tweet}\n")
        print(json.dumps({"dry_run": True, "tweet": tweet}, indent=2))
        return 0

    if cfg.get("tweet_via_buildinpublic"):
        ok, status = post_via_buildinpublic(period_label, tweet)
    else:
        ok, status = post_via_postiz(tweet, os.environ.get("POSTIZ_X_INTEGRATION_ID", ""))

    write_run_state(period_label, {
        "tweet_status": "queued" if ok else f"failed: {status}",
        "tweet_text": tweet,
        "tweet_route": "buildinpublic" if cfg.get("tweet_via_buildinpublic") else "direct",
    })
    sys.stderr.write(f"[public-tweet] ok={ok} {status}\n")
    print(json.dumps({"ok": ok, "status": status, "tweet": tweet}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
