#!/usr/bin/env python3
"""Build a bounded prompt for one Capafy packaging decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import capafy_packaging_decision as packaging
import capafy_portfolio as portfolio


def _remote_fact(remote: dict) -> dict:
    return packaging.remote_fact(remote)


def build_prompt(snapshot: dict, agent_id: str, remote: dict) -> str:
    selected = next(
        (item for item in snapshot["products"] if item["agent_id"] == agent_id),
        None,
    )
    if selected is None:
        raise ValueError("agent_id is absent from the portfolio")
    product = {
        key: selected.get(key)
        for key in (
            "agent_id", "name", "description", "product_type", "observed_status",
            "public_url", "platform_sales", "recurring_mechanism", "target_customer",
            "decision", "decision_reason", "unknowns", "evidence",
        )
    }
    product["remote_fact"] = _remote_fact(remote)
    digest = portfolio.snapshot_digest(snapshot)
    remote_digest = packaging.remote_source_digest(remote)
    return f"""Make one evidence-bound packaging decision for exactly the supplied Capafy product.
Do not change, publish, market, buy, or activate an experiment. Return only the requested JSON.
Bind it to portfolio_source_digest {digest} and use the actual UTC time for decided_at.
Bind it to remote_source_digest {remote_digest}. Copy the sole remote provider_name and provider_model
exactly. If the remote product is not online, has OpenRouter, has generic credentials, or is not the
supported Google Gemini 3.5 Flash-Lite provider, do not invent economics: the deterministic gate will
reject it so provider migration can happen first.

The model, value metric, renewal reason, and conservative compute assumption are your commercial
judgment. Deterministic code will verify eligibility, evidence coverage, exact decimal arithmetic,
and update only bookkeeping. Use the configured billing facts rather than inventing a price or quota.
Treat listing and campaign evidence as positioning/exposure evidence only; observed demand remains unknown
unless a cited record explicitly proves orders. Keep unresolved demand/sales unknowns. resolved_unknowns
must copy only exact strings from the product's current unknowns that this decision truly resolves.

For hosted execution, use Google Gemini 3.5 Flash-Lite pricing of $0.30 per million input tokens and
$2.50 per million output tokens, citing https://ai.google.dev/gemini-api/docs/pricing. Choose explicit,
conservative input_tokens_per_unit and output_tokens_per_unit assumptions; label them assumptions, not
observed usage. Cite https://capafy.ai/publisher-agreement for the 20% platform fee;
platform_fee_rate must be exactly 0.2000 and any other value is invalid. Compute one package:
gross=price; fee=round(gross*fee rate, 2); cost=round(included units*((input tokens*input rate + output
tokens*output rate)/1,000,000), 2); contribution=round(gross-fee-cost, 2).

Evidence supports may use only purchase_model, price_usd, included_units, value_metric, renewal_reason,
platform_fee_rate, model_pricing, and bounded_deliverable. Subscription and hybrid require a defensible
renewal reason. One-time and hybrid require a bounded deliverable. Never call projected contribution
realized revenue.

PRODUCT JSON:
{json.dumps(product, ensure_ascii=False, separators=(",", ":"))}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--remote-json", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
    remote = json.loads(args.remote_json.read_text(encoding="utf-8"))
    errors = portfolio.validate_snapshot(snapshot)
    if errors:
        raise SystemExit("; ".join(errors))
    print(build_prompt(snapshot, args.agent_id, remote))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
