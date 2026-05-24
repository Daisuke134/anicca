#!/usr/bin/env python3
"""Daily fashion sales report (23 JST).

Pull last 24h Stripe charges where metadata[skill]=anicca-fashion-factory
→ Slack #metrics summary.

stdout last line:
  ✅ fashion sales: <count> orders, $<total> | slack ts=<ts>
  ✅ fashion sales: 0 orders today | slack ts=<ts>
  ❌ fashion sales FAILED: <reason>
"""
import os
import sys
import time
import datetime
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-fashion-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from stripe_helper import list_charges
from slack_helper import post_blocks, load_env


def main():
    load_env()

    # Last 24h
    since = int(time.time()) - 86400
    charges = list_charges(created_gte=since, limit=100)

    fashion = [
        c for c in charges
        if c.get("status") == "succeeded"
        and (c.get("metadata") or {}).get("skill") == "anicca-fashion-factory"
    ]
    # Also include charges where the underlying payment_link product had skill metadata
    # (Stripe doesn't auto-propagate metadata from product to charge — link to it via line_items query if needed)

    count = len(fashion)
    total_usd = sum((c.get("amount", 0) for c in fashion)) / 100.0

    today = datetime.date.today().isoformat()
    rows = []
    for c in fashion[:20]:
        prod = (c.get("metadata") or {}).get("product", "?")
        amt = c.get("amount", 0) / 100.0
        rows.append(f"  • {prod} · ${amt:.2f} · {c.get('billing_details', {}).get('{{profile.lateness.stakeholders.channel}}', '?')}")
    rows_text = "\n".join(rows) if rows else "  (no orders in last 24h)"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"👕 Fashion sales — {today}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{count} orders · ${total_usd:.2f} total* (last 24h)\n```\n{rows_text}\n```"}},
    ]
    resp = post_blocks(
        channel=os.environ["SLACK_CHANNEL_ID"],
        text_fallback=f"👕 fashion sales {today}: {count} orders, ${total_usd:.2f}",
        blocks=blocks,
    )
    print(f"✅ fashion sales: {count} orders, ${total_usd:.2f} | slack ts={resp['ts']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ fashion sales FAILED: {e}", file=sys.stderr)
        print(f"❌ fashion sales FAILED: {e}")
        sys.exit(1)
