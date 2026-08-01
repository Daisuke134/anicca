#!/usr/bin/env python3
"""Build the bounded judgment prompt for Capafy's cleanup queue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import capafy_portfolio as portfolio


def build_prompt(snapshot: dict) -> str:
    digest = portfolio.snapshot_digest(snapshot)
    mandatory = [
        product["agent_id"]
        for product in snapshot["products"]
        if product["observed_status"] in {"under_review", "draft", "rejected"}
    ]
    products = [
        {
            "agent_id": p["agent_id"], "name": p["name"],
            "description": p["description"], "observed_status": p["observed_status"],
            "decision": p["decision"], "decision_reason": p["decision_reason"],
            "public_url": p["public_url"], "evidence": p["evidence"],
        }
        for p in snapshot["products"]
    ]
    return f"""Create one non-destructive cleanup queue for this Capafy portfolio.
Return an item for every mandatory non-online ID {json.dumps(mandatory)} and at least one
evidence-backed overlap group. For overlaps, name every related_agent_id. Choose exactly one
bounded action per item: repair, reposition, or retire_candidate. Do not delete, publish, edit,
submit, or log in. status must be queued and remote_url must be null.

Each action needs an HTTPS evidence citation, an honest reason, and an observable stop condition.
One repair/reposition attempt is the maximum; a failed or unverifiable attempt becomes a stop,
not an endless retry. Listing text proves current positioning, not sales or demand. Do not invent
commercial proof. Bind output to portfolio_source_digest {digest} and use actual UTC created_at.

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
