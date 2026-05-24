#!/usr/bin/env python3
"""
compute-revenue.py — gross revenue minus refunds for the prior calendar
month, returned in USD.

Strategy:
  1. Try `stripe.charges.list({created:{gte,lt}})` paged + `stripe.refunds.list`.
  2. If `stripe` library or API key missing, fall back to reading
     `~/anicca-products/apps/landing/public/dashboard.json` (or the live URL
     `https://aniccaai.com/dashboard.json`) for `mrr.total_usd` as an
     approximation, and tag the run state with `revenue_source="dashboard-fallback"`.
  3. Write {period, revenue_usd, source} into run-YYYY-MM.json.

Usage:
  DONATION_DRY_RUN=true python3 compute-revenue.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    HOME,
    is_dry_run,
    load_env_files,
    load_wizard_config,
    prior_month_period,
    write_run_state,
)


def fetch_stripe_revenue(period_label, start_dt, end_dt) -> tuple[float, dict]:
    """Returns (revenue_usd, debug). Raises on missing stripe lib or API key."""
    try:
        import stripe  # type: ignore
    except Exception as e:
        raise RuntimeError(f"stripe lib not installed: {e}")
    api_key = os.environ.get("STRIPE_API_KEY", "")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY not set in env")
    stripe.api_key = api_key

    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    # Charges
    gross_cents = 0
    n_charges = 0
    starting_after = None
    while True:
        kwargs = dict(limit=100, created={"gte": start_ts, "lt": end_ts})
        if starting_after:
            kwargs["starting_after"] = starting_after
        page = stripe.Charge.list(**kwargs)
        for ch in page.data:
            if ch.status == "succeeded" and not ch.refunded:
                # NB: amount is in the smallest currency unit; assume USD account
                gross_cents += int(ch.amount)
                n_charges += 1
        if not page.has_more:
            break
        starting_after = page.data[-1].id

    # Refunds (subtract)
    refund_cents = 0
    n_refunds = 0
    starting_after = None
    while True:
        kwargs = dict(limit=100, created={"gte": start_ts, "lt": end_ts})
        if starting_after:
            kwargs["starting_after"] = starting_after
        page = stripe.Refund.list(**kwargs)
        for rf in page.data:
            refund_cents += int(rf.amount)
            n_refunds += 1
        if not page.has_more:
            break
        starting_after = page.data[-1].id

    net_cents = max(0, gross_cents - refund_cents)
    return net_cents / 100.0, {
        "n_charges": n_charges,
        "n_refunds": n_refunds,
        "gross_cents": gross_cents,
        "refund_cents": refund_cents,
        "currency_assumption": "usd",
    }


def fallback_dashboard_revenue() -> tuple[float, dict]:
    # Local checkout first
    candidates = [
        HOME / "anicca-products" / "apps" / "landing" / "public" / "dashboard.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                blob = json.loads(p.read_text())
                v = float(((blob.get("mrr") or {}).get("total_usd")) or 0)
                return v, {"source_file": str(p)}
            except Exception:
                continue
    # Live URL
    try:
        with urllib.request.urlopen("https://aniccaai.com/dashboard.json", timeout=8) as resp:
            blob = json.loads(resp.read().decode("utf-8"))
            v = float(((blob.get("mrr") or {}).get("total_usd")) or 0)
            return v, {"source_url": "https://aniccaai.com/dashboard.json"}
    except Exception as e:
        return 0.0, {"error": f"fallback failed: {e}"}


def main() -> int:
    load_env_files()
    cfg = load_wizard_config()
    period_label, start_dt, end_dt = prior_month_period()
    dry_run = is_dry_run()

    revenue_usd = 0.0
    source = "none"
    debug: dict = {}
    try:
        revenue_usd, debug = fetch_stripe_revenue(period_label, start_dt, end_dt)
        source = "stripe-api"
    except Exception as e:
        sys.stderr.write(f"[compute-revenue] stripe path failed: {e}; falling back to dashboard\n")
        revenue_usd, debug = fallback_dashboard_revenue()
        source = "dashboard-fallback"
        debug["fallback_reason"] = str(e)

    payload = {
        "period": period_label,
        "period_start_iso": start_dt.isoformat(),
        "period_end_iso": end_dt.isoformat(),
        "dry_run": dry_run,
        "revenue_usd": round(revenue_usd, 2),
        "revenue_source": source,
        "revenue_debug": debug,
        "percent": cfg["percent"],
    }
    out = write_run_state(period_label, payload)
    sys.stderr.write(
        f"[compute-revenue] period={period_label} revenue=${revenue_usd:.2f} "
        f"source={source} dry_run={dry_run} -> {out}\n"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
