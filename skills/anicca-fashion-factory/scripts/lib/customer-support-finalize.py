#!/usr/bin/env python3
"""Finalize customer-support-event: append to coupons.json + post Slack.

Args:
  1. coupons.json path
  2. stripe coupon id
  3. stripe promotion code id
  4. promo_code (human-readable, e.g. ANICCA26057469)
  5. customer_{{profile.lateness.stakeholders.channel}}
  6. reason (free text)
  7. slack channel id
  8. slack bot token

Stdout: slack ts (or '?' on failure).
"""
import sys
import json
import datetime
import urllib.request
import pathlib


def main() -> None:
    if len(sys.argv) < 9:
        print("?", file=sys.stderr)
        sys.exit(2)

    (coupons_file, coupon_id, promo_id, promo_code,
     {{profile.lateness.stakeholders.channel}}, reason, channel, slack_token) = sys.argv[1:9]

    p = pathlib.Path(coupons_file)
    db = json.loads(p.read_text())
    db.setdefault("coupons", []).append({
        "issued_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stripe_coupon_id": coupon_id,
        "stripe_promo_id":  promo_id,
        "promo_code":       promo_code,
        "customer_{{profile.lateness.stakeholders.channel}}":   {{profile.lateness.stakeholders.channel}},
        "reason":           reason,
        "percent_off":      30,
        "valid_days":       30,
    })
    db["coupons"] = db["coupons"][-200:]
    p.write_text(json.dumps(db, ensure_ascii=False, indent=2))

    payload = {
        "channel": channel,
        "text": f"🩹 fashion-customer-support: {promo_code} → {{{profile.lateness.stakeholders.channel}}}",
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text",
                      "text": "🩹 fashion-customer-support-event"}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": (f"*to:* `{{{profile.lateness.stakeholders.channel}}}`\n"
                               f"*coupon:* `{promo_code}` "
                               f"(30 percent off, 30 days, 1-time)\n"
                               f"*stripe coupon id:* `{coupon_id}`")}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f"*reason:*\n>>> {reason}"}},
        ],
    }
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read().decode())
        print(resp.get("ts", "?"))
    except Exception:
        print("?")


if __name__ == "__main__":
    main()
