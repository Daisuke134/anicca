#!/usr/bin/env python3
"""Tomb daily sales report (23 JST). Pull last 24h Stripe charges with skill=gpt-tomb-factory."""
import os, sys, time, datetime, json
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "gpt-tomb-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from stripe_helper import list_charges
from slack_helper import post_blocks, load_env


def main():
    load_env()
    since = int(time.time()) - 86400
    charges = list_charges(created_gte=since, limit=100)
    tomb_charges = [c for c in charges
                    if c.get("status") == "succeeded"
                    and (c.get("metadata") or {}).get("skill") == "gpt-tomb-factory"]

    count = len(tomb_charges)
    total_jpy = sum((c.get("amount", 0) for c in tomb_charges))

    today = datetime.date.today().isoformat()
    rows = []
    for c in tomb_charges[:20]:
        prod = (c.get("metadata") or {}).get("product", "?")
        amt = c.get("amount", 0)
        rows.append(f"  • {prod} · ¥{amt:,} · {(c.get('billing_details', {}) or {}).get('{{profile.lateness.stakeholders.channel}}', '?')}")
    rows_text = "\n".join(rows) if rows else "  (no orders in last 24h)"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🪦 Tomb sales — {today}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{count} orders · ¥{total_jpy:,} total* (last 24h)\n```\n{rows_text}\n```"}},
    ]
    resp = post_blocks(channel=os.environ["SLACK_CHANNEL_ID"],
                      text_fallback=f"🪦 tomb sales {today}: {count} orders, ¥{total_jpy:,}",
                      blocks=blocks)
    print(f"✅ tomb sales: {count} orders, ¥{total_jpy:,} | slack ts={resp['ts']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ tomb sales FAILED: {e}", file=sys.stderr)
        print(f"❌ tomb sales FAILED: {e}")
        sys.exit(1)
