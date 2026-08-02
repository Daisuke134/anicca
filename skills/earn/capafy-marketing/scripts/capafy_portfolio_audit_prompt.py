#!/usr/bin/env python3
"""Build the bounded agent prompt for one full Capafy portfolio audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

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


def _sanitized_remote_fact(remote: dict) -> dict:
    latest = remote.get("latest_version") if isinstance(remote, dict) else None
    if not isinstance(latest, dict):
        return {}
    return {
        "agent_id": str(latest.get("agentId") or ""),
        "version_id": str(latest.get("agentVersionId") or ""),
        "product_type": latest.get("agentType"),
        "status": latest.get("status"),
        "audit_status": latest.get("auditStatus"),
        "is_confirmed_skills": latest.get("isConfirmedSkills"),
        "title": latest.get("title"),
        "short_description": latest.get("shortDescription"),
        "detailed_description": latest.get("detailedDescription"),
        "billings": [
            {
                "billing_mode": billing.get("billingMode"),
                "one_time_fee": billing.get("oneTimeFee"),
                "cycle_type": billing.get("cycleType"),
                "cycle_price": billing.get("cyclePrice"),
                "currency": billing.get("currency"),
            }
            for billing in latest.get("billings", [])
            if isinstance(billing, dict)
        ],
    }


def build_residual_prompt(
    snapshot: dict,
    remotes: Optional[dict[str, dict]] = None,
) -> str:
    digest = portfolio.snapshot_digest(snapshot)
    remotes = remotes or {}
    products = [
        {
            "agent_id": item["agent_id"],
            "name": item["name"],
            "description": item["description"],
            "product_type": item["product_type"],
            "observed_status": item["observed_status"],
            "listing_url": f"https://capafy.ai/agent/{item['agent_id']}",
            "platform_sales": item["platform_sales"],
            "remote_fact": _sanitized_remote_fact(remotes.get(item["agent_id"], {})),
        }
        for item in snapshot["products"]
        if item["decision"] == "unaudited"
    ]
    count = len(products)
    return f"""Perform one bounded residual commercial audit of only the unaudited Capafy products below.
Return exactly {count} product rows, one for every supplied agent_id and no others, bound to
portfolio_source_digest {digest}. Do not change any product or external system.

Do not invent a target customer, recurring mechanism, purchase model, value metric, alternative,
renewal reason, demand, price, sales, cost, or decision. Use null/undecided and list unresolved facts
in unknowns when evidence is insufficient. Every asserted authored field and decision needs an HTTPS
evidence object whose supports names that field. A seller listing or remote product record proves
positioning and configured distribution type, not demand, willingness to pay, approval, or sales.

Allowed decisions: promote, repair, reposition, pause, retire_candidate.
Allowed purchase models: subscription, usage, one_time, hybrid, undecided.
Allowed recurring mechanisms: repeated_workflow, scheduled_refresh, ongoing_monitoring,
collaboration, metered_execution, or null.

Use the supplied output schema exactly. Set schema_version=1, kind=capafy_portfolio_audit,
portfolio_source_digest={digest}, and audited_at to the actual UTC observation time.

RESIDUAL PORTFOLIO JSON:
{json.dumps(products, ensure_ascii=False, separators=(",", ":"))}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--residual", action="store_true")
    parser.add_argument("--remote-json", type=Path, action="append", default=[])
    args = parser.parse_args()
    snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
    errors = portfolio.validate_snapshot(snapshot)
    if errors:
        raise SystemExit("; ".join(errors))
    remotes = {}
    for path in args.remote_json:
        value = json.loads(path.read_text(encoding="utf-8"))
        latest = value.get("latest_version") if isinstance(value, dict) else None
        if isinstance(latest, dict) and latest.get("agentId") is not None:
            remotes[str(latest["agentId"])] = value
    print(build_residual_prompt(snapshot, remotes) if args.residual else build_prompt(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
