#!/usr/bin/env python3
"""Build the bounded agent prompt for one full Capafy portfolio audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import capafy_portfolio as portfolio


def build_prompt(snapshot: dict) -> str:
    digest = portfolio.snapshot_digest(snapshot)
    products = [
        {
            "agent_id": item["agent_id"],
            "name": item["name"],
            "description": item["description"],
            "observed_status": item["observed_status"],
            "public_url": item["public_url"],
            "platform_sales": item["platform_sales"],
        }
        for item in snapshot["products"]
    ]
    return f"""Perform one bounded commercial audit of the seller-owned Capafy portfolio below.
Use web research and direct public pages where available. Return exactly 31 product rows, one for
every supplied agent_id, bound to portfolio_source_digest {digest}. Do not create, edit, publish,
delete, market, purchase, message, or log in to anything.

Do not invent a target customer, recurring mechanism, purchase model, value metric, alternative,
renewal reason, demand, price, sales, cost, or decision. Use null/undecided and name every unresolved
fact in unknowns when evidence is insufficient. Every non-null authored field and every decision
must be backed by at least one HTTPS evidence object whose supports array names that exact field.
The claim must state only what the cited page supports; include the observation time and calibrated
confidence. A listing description proves positioning, not willingness to pay or observed demand.

Allowed decisions: promote, repair, reposition, pause, retire_candidate.
Allowed purchase models: subscription, usage, one_time, hybrid, undecided.
Allowed recurring mechanisms: repeated_workflow, scheduled_refresh, ongoing_monitoring,
collaboration, metered_execution, or null.

Use the supplied output schema exactly. Set schema_version=1, kind=capafy_portfolio_audit,
portfolio_source_digest={digest}, and audited_at to the actual UTC observation time.

PORTFOLIO JSON:
{json.dumps(products, ensure_ascii=False, separators=(",", ":"))}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
    errors = portfolio.validate_snapshot(snapshot)
    if errors:
        raise SystemExit("; ".join(errors))
    print(build_prompt(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
