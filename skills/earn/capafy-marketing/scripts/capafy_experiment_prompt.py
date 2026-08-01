#!/usr/bin/env python3
"""Build the bounded packaging-experiment proposal prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import capafy_portfolio as portfolio


def build_prompt(snapshot: dict) -> str:
    digest = portfolio.snapshot_digest(snapshot)
    eligible = [
        {key: product.get(key) for key in (
            "agent_id", "name", "description", "product_type", "public_url",
            "platform_sales", "recurring_mechanism", "target_customer", "evidence",
            "decision_reason", "unknowns",
        )}
        for product in snapshot["products"]
        if product["observed_status"] == "online"
        and product["decision"] == "promote"
        and product["evidence"]
    ]
    return f"""Choose exactly one highest-evidence eligible Capafy product and propose one bounded
packaging experiment. Do not edit, submit, publish, market, or purchase anything. Choose the price,
purchase model, value metric, and stop condition from evidence; the deterministic validator will
recalculate every money field. Do not invent observed demand, sales, costs, or willingness to pay.
This is a paid-demand experiment: price_usd must be greater than 0. Treat price as a bounded test
hypothesis, not as evidence of willingness to pay.

Capafy officially supports Subscription, Hourly, and One-Time pricing. Map hourly to purchase_model
usage. Hybrid means multiple supported modes on one Agent. Official publisher terms state a 20%
platform service fee on all transactions and additional actual compute fees for subscription/hourly.
Cite https://capafy.ai/publisher-agreement for the 0.2000 fee. If actual publisher compute/model cost
per unit is unknown, do not claim it is known. A zero model cost is defensible only for a one-time
Download experiment where execution and model choice shift to the buyer; cite
https://capafy.ai/help-center. Subscription requires a renewal reason; usage requires a metered unit;
one_time requires a bounded deliverable; hybrid requires all three.

Use projected_units as a bounded exposure scenario, not a sales forecast. observed money must remain
null. success_metric and stop_condition must be observable without calendar waiting. Bind the result
to portfolio_source_digest {digest}; owner must be builder or marketer; activated_at is actual UTC.

ELIGIBLE PORTFOLIO JSON:
{json.dumps(eligible, ensure_ascii=False, separators=(",", ":"))}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.portfolio.read_text())
    errors = portfolio.validate_snapshot(snapshot)
    if errors:
        raise SystemExit("; ".join(errors))
    print(build_prompt(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
