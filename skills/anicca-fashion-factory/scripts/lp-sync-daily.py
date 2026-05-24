#!/usr/bin/env python3
"""Daily LP consistency check (0 JST).

Verify that data/{products,stripe-products}.json references match what is
currently committed to apps/landing/app/fashion/page.tsx.

Drift = a Stripe Payment Link ID in stripe-products.json does not appear in
        /fashion/page.tsx.

This cron is informational by design: it does NOT auto-edit the LP because
/fashion/page.tsx is hand-tuned with marketing copy that should not be
overwritten by a script. When drift is detected, a Slack alert + diff is
emitted so a human can update the LP intentionally.

stdout final line:
  ✅ lp-sync: no drift | products=<n> | slack ts=<ts>
  ⚠️ lp-sync: drift detected — N items missing | slack ts=<ts>
  ❌ lp-sync FAILED: <reason>
"""
import json
import os
import sys
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-fashion-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from slack_helper import post_blocks, load_env  # noqa


REPO_ROOT = Path("/Users/anicca/anicca-products")
PAGE_TSX = REPO_ROOT / "apps" / "landing" / "app" / "fashion" / "page.tsx"


def main() -> int:
    products_path = SKILL_DIR / "data" / "products.json"

    if not products_path.exists():
        raise RuntimeError(f"products.json not found: {products_path}")
    if not PAGE_TSX.exists():
        raise RuntimeError(f"/fashion/page.tsx not found: {PAGE_TSX}")

    raw = json.loads(products_path.read_text())
    page_text = PAGE_TSX.read_text()

    # products.json shape: {"products": [{...}, ...]} or top-level list
    if isinstance(raw, dict):
        items = raw.get("products", raw)
    else:
        items = raw
    if isinstance(items, dict):
        items = list(items.values())

    drift = []
    checked = 0
    for info in items or []:
        if not isinstance(info, dict):
            continue
        checked += 1
        slug = info.get("slug", "?")
        link = info.get("payment_link") or info.get("buy_url")
        if not link:
            continue
        link_id = link.rstrip("/").rsplit("/", 1)[-1]
        if link_id and link_id not in page_text:
            drift.append(f"{slug}: payment_link `{link_id}` missing in /fashion/page.tsx")

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "text": "🧵 fashion-lp-sync-daily"}},
        {"type": "section",
         "text": {"type": "mrkdwn",
                  "text": f"*products checked:* {checked}\n*drift:* {len(drift)}"}},
    ]
    if drift:
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn",
                                "text": "*missing references:*\n>>> " + "\n".join(drift)}})

    load_env()
    sresp = post_blocks(os.environ["SLACK_CHANNEL_ID"],
                        f"fashion-lp-sync drift={len(drift)}", blocks)
    ts = sresp.get("ts", "?")

    if drift:
        print(f"⚠️ lp-sync: drift detected — {len(drift)} items missing | slack ts={ts}")
        return 0
    print(f"✅ lp-sync: no drift | products={checked} | slack ts={ts}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        msg = str(e)[:300]
        print(f"❌ lp-sync FAILED: {msg}", file=sys.stderr)
        print(f"❌ lp-sync FAILED: {msg}")
        sys.exit(1)
