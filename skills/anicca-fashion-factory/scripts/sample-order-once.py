#!/usr/bin/env python3
"""Order Tee/Hoodie/Cap M sample to a recipient address (one-shot).

Usage:
  python3 sample-order-once.py
  RECIPIENT_NAME=... RECIPIENT_ADDRESS1=... RECIPIENT_CITY=... \
    RECIPIENT_STATE=... RECIPIENT_COUNTRY=... RECIPIENT_ZIP=... \
    RECIPIENT_EMAIL=... RECIPIENT_PHONE=... python3 sample-order-once.py

Default recipient = Dais Tokyo home.

stdout final:
  ✅ sample order: pf_order_id=<id> total=<currency><amount> | slack ts=<ts>
  ❌ sample FAILED: <reason>
"""
import os
import sys
import json
import datetime
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-fashion-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from printful_helper import create_order, _load_env  # noqa
from slack_helper import post_blocks


DEFAULT_RECIPIENT = {
    "name": "<your-name>",
    "address1": "Minamimotomachi 15-27",
    "city": "Shinjuku-ku",
    "state_code": "JP-13",
    "country_code": "JP",
    "zip": "160-0012",
    "phone": "{{profile.contact.phone}}",
    "{{profile.lateness.stakeholders.channel}}": "{{profile.contact.personalEmail}}",
}


def main():
    _load_env()
    config = json.loads((SKILL_DIR / "data" / "printful-products.json").read_text())
    sync_variant_ids = []
    for p in config:
        sp_id = p.get("sync_product_id")
        if not sp_id:
            continue
        # Need sync_variant_id — look it up from store/products endpoint
        # For now read from products.json which already has it
    # Fallback: hardcode known IDs from this drop
    sync_variant_ids = [
        ("Tee Black M", 5298091479),
        ("Hoodie Black M", 5298091481),
        ("Cap Black", 5298092119),
    ]

    recipient = DEFAULT_RECIPIENT.copy()
    for k in ["name", "address1", "city", "state_code", "country_code", "zip", "{{profile.lateness.stakeholders.channel}}", "phone"]:
        env_key = "RECIPIENT_" + k.upper()
        if os.environ.get(env_key):
            recipient[k] = os.environ[env_key]

    items = [{"sync_variant_id": svi, "quantity": 1} for _, svi in sync_variant_ids]

    print(f"placing order for {recipient['name']} ({recipient['country_code']})")
    order = create_order(
        recipient=recipient,
        items=items,
        external_id=f"anicca-sample-{datetime.date.today().isoformat()}",
        confirm=True,
    )

    pf_id = order.get("id")
    costs = order.get("costs") or {}
    total = costs.get("total")
    currency = costs.get("currency")

    # Persist
    out = SKILL_DIR / "data" / "sample-orders" / f"{pf_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(order, indent=2))

    # Slack
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📦 Fashion sample order placed"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Printful order:* {pf_id}\n*Total:* {currency} {total}\n*Recipient:* {recipient['name']} / {recipient['country_code']}\n*Items:* " + ", ".join(n for n, _ in sync_variant_ids)}},
    ]
    resp = post_blocks(channel=os.environ["SLACK_CHANNEL_ID"],
                      text_fallback=f"📦 sample order {pf_id}",
                      blocks=blocks)
    print(f"✅ sample order: pf_order_id={pf_id} total={currency} {total} | slack ts={resp['ts']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ sample FAILED: {e}", file=sys.stderr)
        print(f"❌ sample FAILED: {e}")
        sys.exit(1)
