#!/usr/bin/env python3
"""Daily shipping status check (10 JST).

For all fashion_orders in 'pending' or 'in_production' status, fetch latest
Printful order state. When an order ships, update Supabase + send Resend
tracking {{profile.lateness.stakeholders.channel}} to customer.

stdout final line:
  ✅ shipping: <new_shipped_count> shipped, <still_in_progress> in progress | slack ts=<ts>
  ❌ shipping FAILED: <reason>
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import datetime
from pathlib import Path

SKILL_DIR = Path.home() / ".openclaw" / "skills" / "anicca-fashion-factory"
sys.path.insert(0, str(SKILL_DIR / "scripts" / "lib"))

from printful_helper import get_order, _load_env  # noqa
from slack_helper import post_blocks


def supabase_query(method, path, body=None, params=None):
    _load_env()
    url = os.environ["SUPABASE_URL"] + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_ROLE_KEY']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "[]")


def resend_{{profile.lateness.stakeholders.channel}}(to, subject, html):
    _load_env()
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    req = urllib.request.Request(
        "https://api.resend.com/{{profile.lateness.stakeholders.channel}}s",
        method="POST",
        data=json.dumps({
            "from": "Anicca Fashion <onboarding@resend.dev>",
            "to": to,
            "subject": subject,
            "html": html,
        }).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True
    except Exception as e:
        print(f"resend failed: {e}", file=sys.stderr)
        return False


def main():
    _load_env()

    # Fetch open orders from Supabase
    pending = supabase_query("GET", "/rest/v1/fashion_orders",
                             params={"status": "in.(pending,in_production,inhouse)"})

    new_shipped = 0
    still_pending = 0

    for o in pending:
        printful_id = o.get("printful_order_id")
        if not printful_id:
            still_pending += 1
            continue
        try:
            pf = get_order(int(printful_id))
        except Exception as e:
            print(f"  err order {printful_id}: {e}", file=sys.stderr)
            still_pending += 1
            continue

        pf_status = pf.get("status")
        shipments = pf.get("shipments", [])

        if pf_status == "fulfilled" and shipments:
            # Order shipped
            ship = shipments[0]
            tracking = ship.get("tracking_number")
            tracking_url = ship.get("tracking_url")
            ship_date = ship.get("ship_date")
            {{profile.lateness.stakeholders.channel}} = o.get("customer_{{profile.lateness.stakeholders.channel}}")

            # Update Supabase
            supabase_query("PATCH", "/rest/v1/fashion_orders",
                           body={"status": "fulfilled",
                                 "tracking_number": tracking,
                                 "shipped_at": datetime.datetime.fromtimestamp(int(ship_date)).isoformat() + "Z" if ship_date else None},
                           params={"stripe_session_id": f"eq.{o['stripe_session_id']}"})

            # Email customer
            if {{profile.lateness.stakeholders.channel}} and tracking_url:
                resend_{{profile.lateness.stakeholders.channel}}({{profile.lateness.stakeholders.channel}},
                             f"Your Anicca Fashion order shipped — track #{tracking}",
                             f"""<p>Your order has shipped.</p>
<p><strong>Tracking:</strong> <a href=\"{tracking_url}\">{tracking}</a></p>
<p>Carrier: {ship.get('carrier','—')} · Service: {ship.get('service','—')}</p>
<p>Delivery typically 7–12 business days from now depending on country.</p>
<p>— Anicca</p>""")

            new_shipped += 1
        elif pf_status != o.get("status"):
            # status changed but not yet shipped — sync it
            supabase_query("PATCH", "/rest/v1/fashion_orders",
                           body={"status": pf_status},
                           params={"stripe_session_id": f"eq.{o['stripe_session_id']}"})
            still_pending += 1
        else:
            still_pending += 1

    # Slack report
    today = datetime.date.today().isoformat()
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📦 Fashion shipping — {today}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{new_shipped} shipped* (tracking {{profile.lateness.stakeholders.channel}}s sent), *{still_pending} still in production*."}},
    ]
    resp = post_blocks(channel=os.environ["SLACK_CHANNEL_ID"],
                      text_fallback=f"📦 fashion shipping {today}: {new_shipped} shipped",
                      blocks=blocks)
    print(f"✅ shipping: {new_shipped} shipped, {still_pending} in progress | slack ts={resp['ts']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ shipping FAILED: {e}", file=sys.stderr)
        print(f"❌ shipping FAILED: {e}")
        sys.exit(1)
