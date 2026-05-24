#!/usr/bin/env python3
"""
transfer.py — split the prior month's donation across recipients and call
`stripe.transfers.create` once per recipient.

Reads run-YYYY-MM.json (must already contain revenue_usd from
compute-revenue.py). Computes:
  total_usd  = max(1, revenue_usd * percent / 100)
  per_recipient_usd[i] = round(total_usd * weight[i] / sum(weights), 2)

Skips entries with charges_enabled_verified=false (emits 🚨 to Slack), and
entries with rail != "stripe-connect" (those go to the agent-{{profile.lateness.stakeholders.channel}} archive,
not handled here).

Idempotency:
  transfer_group   = donation-YYYY-MM
  idempotency_key  = donation-YYYY-MM-<recipient_id>
Re-runs of the same month are no-ops at the Stripe API level.

DRY_RUN behavior:
  No `transfers.create` call. Plan is computed and recorded; transfer_id
  is set to "DRY_RUN".
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    is_dry_run,
    is_period_skipped,
    load_env_files,
    load_recipients,
    load_wizard_config,
    prior_month_period,
    read_run_state,
    write_run_state,
)


def slack_alert(text: str):
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    channel = os.environ.get("SLACK_CHANNEL", "{{profile.channels.reportChannel}}")
    if not token or is_dry_run():
        sys.stderr.write(f"[transfer] (slack suppressed) {text}\n")
        return
    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        sys.stderr.write(f"[transfer] slack failed: {e}\n")


def split_amount_cents(total_cents: int, recipients: list) -> list:
    weights = [int(r.get("weight") or 0) for r in recipients]
    total_w = sum(weights)
    if total_w <= 0:
        return [0] * len(recipients)
    shares = [int(round(total_cents * w / total_w)) for w in weights]
    drift = total_cents - sum(shares)
    if drift != 0:
        # Apply drift to the highest-weight entry
        idx = weights.index(max(weights))
        shares[idx] += drift
    return shares


def create_transfer(amount_cents: int, currency: str, destination: str,
                    transfer_group: str, idempotency_key: str, metadata: dict) -> tuple[str, str]:
    """Returns (transfer_id, status). Raises on failure."""
    import stripe  # type: ignore

    api_key = os.environ.get("STRIPE_API_KEY", "")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY not set")
    stripe.api_key = api_key
    t = stripe.Transfer.create(
        amount=amount_cents,
        currency=currency,
        destination=destination,
        transfer_group=transfer_group,
        metadata=metadata,
        idempotency_key=idempotency_key,
    )
    # Transfer create is synchronous; return id and assume "succeeded" if no error
    return t.id, "succeeded"


def main() -> int:
    load_env_files()
    cfg = load_wizard_config()
    period_label, _, _ = prior_month_period()
    dry_run = is_dry_run()

    if is_period_skipped(period_label):
        sys.stderr.write(f"[transfer] period {period_label} marked skipped — no-op\n")
        return 0

    state = read_run_state(period_label)
    revenue_usd = float(state.get("revenue_usd") or 0)
    if revenue_usd <= 0 and not state.get("revenue_source"):
        sys.stderr.write(
            "[transfer] no revenue in run state — run compute-revenue.py first\n"
        )
        return 2

    percent = float(cfg["percent"])
    raw = revenue_usd * percent / 100.0
    total_usd = round(max(1.0, raw), 2)
    total_cents = int(round(total_usd * 100))

    recipients = load_recipients(cfg["recipients_path"])
    eligible = [r for r in recipients if r.get("rail", "stripe-connect") == "stripe-connect"
                and r.get("charges_enabled_verified") is True]
    skipped = [r for r in recipients if r not in eligible]

    if not eligible:
        slack_alert(
            f"🚨 donation {period_label}: no eligible Stripe Connect recipients. "
            f"Total {total_usd:.2f} USD NOT transferred. "
            f"Skipped: {len(skipped)} (charges_enabled_verified=false or non-connect rail)."
        )
        write_run_state(period_label, {
            "total_amount_usd": total_usd,
            "transfers": [],
            "skipped_recipients": [r.get("recipient_id") for r in skipped],
            "transfer_status": "no-eligible-recipients",
        })
        return 0

    shares_cents = split_amount_cents(total_cents, eligible)
    transfer_group = f"donation-{period_label}"
    transfers_log = []

    for r, cents in zip(eligible, shares_cents):
        if cents <= 0:
            continue
        idem_key = f"donation-{period_label}-{r['recipient_id']}"
        meta = {
            "recipient_id": r["recipient_id"],
            "name": r["name"],
            "donor_entity": cfg["tax_entity"],
            "period": period_label,
        }
        if dry_run:
            transfers_log.append({
                "recipient_id": r["recipient_id"],
                "name": r["name"],
                "amount_usd": round(cents / 100.0, 2),
                "destination": r["stripe_connect_account_id"],
                "transfer_group": transfer_group,
                "idempotency_key": idem_key,
                "transfer_id": "DRY_RUN",
                "status": "planned",
            })
            continue
        try:
            tid, status = create_transfer(
                amount_cents=cents,
                currency="usd",
                destination=r["stripe_connect_account_id"],
                transfer_group=transfer_group,
                idempotency_key=idem_key,
                metadata=meta,
            )
            transfers_log.append({
                "recipient_id": r["recipient_id"],
                "name": r["name"],
                "amount_usd": round(cents / 100.0, 2),
                "destination": r["stripe_connect_account_id"],
                "transfer_group": transfer_group,
                "idempotency_key": idem_key,
                "transfer_id": tid,
                "status": status,
            })
        except Exception as e:
            transfers_log.append({
                "recipient_id": r["recipient_id"],
                "amount_usd": round(cents / 100.0, 2),
                "transfer_id": None,
                "status": f"error: {e}",
            })
            slack_alert(f"🚨 donation {period_label}: transfer failed for {r['recipient_id']}: {e}")

    payload = {
        "total_amount_usd": total_usd,
        "transfer_group": transfer_group,
        "transfers": transfers_log,
        "skipped_recipients": [r.get("recipient_id") for r in skipped],
        "transfer_status": "dry_run" if dry_run else "executed",
    }
    out = write_run_state(period_label, payload)
    sys.stderr.write(
        f"[transfer] period={period_label} total=${total_usd:.2f} "
        f"transfers={len(transfers_log)} dry_run={dry_run} -> {out}\n"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
