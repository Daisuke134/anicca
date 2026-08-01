import copy
import json
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_portfolio as portfolio
import capafy_portfolio_audit as audit
import capafy_portfolio_audit_prompt as audit_prompt

from test_capafy_portfolio import company_projection, inventory_agents


def base_snapshot() -> dict:
    return portfolio.build_snapshot(
        inventory_agents(), company_projection(), "2026-08-02T12:00:00Z"
    )


def audit_product(product: dict) -> dict:
    return {
        "agent_id": product["agent_id"],
        "recurring_mechanism": None,
        "purchase_model": "undecided",
        "value_metric": None,
        "target_customer": None,
        "next_best_alternative": None,
        "renewal_reason": None,
        "decision": "pause",
        "decision_reason": "No public demand evidence is currently available.",
        "unknowns": ["platform_sales", "willingness_to_pay", "observed_cost"],
        "evidence": [
            {
                "url": f"https://capafy.ai/agent/{product['agent_id']}",
                "observed_at": "2026-08-02T12:30:00Z",
                "claim": "The product URL is the seller-owned Capafy listing under audit.",
                "confidence": "high",
                "supports": ["decision"],
            }
        ],
    }


def complete_audit(snapshot: dict) -> dict:
    return {
        "schema_version": 1,
        "kind": "capafy_portfolio_audit",
        "portfolio_source_digest": portfolio.snapshot_digest(snapshot),
        "audited_at": "2026-08-02T12:30:00Z",
        "products": [audit_product(product) for product in snapshot["products"]],
    }


def test_deterministic_snapshot_has_no_business_defaults() -> None:
    snapshot = base_snapshot()

    assert all(product["target_customer"] is None for product in snapshot["products"])
    assert all(product["recurring_mechanism"] is None for product in snapshot["products"])
    assert all(product["purchase_model"] == "undecided" for product in snapshot["products"])
    assert all(product["value_metric"] is None for product in snapshot["products"])
    assert all(product["decision"] == "unaudited" for product in snapshot["products"])


def test_complete_cited_audit_updates_every_product_and_preserves_observed_fields() -> None:
    snapshot = base_snapshot()
    before = copy.deepcopy(snapshot)
    result = audit.apply_audit(snapshot, complete_audit(snapshot))

    assert audit.validate_audit(before, complete_audit(before)) == []
    assert len(result["products"]) == 31
    assert all(product["decision"] == "pause" for product in result["products"])
    assert all(product["evidence"] for product in result["products"])
    for old, new in zip(before["products"], result["products"]):
        for field in audit.OBSERVED_PRODUCT_FIELDS:
            assert new[field] == old[field]


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda value: value["products"].pop(), "exactly one result"),
        (lambda value: value["products"].append(value["products"][0]), "duplicate"),
        (lambda value: value["products"][0].update({"target_customer": "everyone"}), "evidence"),
        (lambda value: value["products"][0].update({"unknowns": []}), "unknowns"),
        (lambda value: value["products"][0]["evidence"].clear(), "evidence"),
        (lambda value: value["products"][0]["evidence"][0].update({"url": "http://bad"}), "HTTPS"),
    ],
)
def test_partial_placeholder_or_uncited_audit_is_rejected(mutation, expected) -> None:
    snapshot = base_snapshot()
    value = complete_audit(snapshot)
    mutation(value)

    assert any(expected in error for error in audit.validate_audit(snapshot, value))


def test_source_digest_must_match_exact_portfolio() -> None:
    snapshot = base_snapshot()
    value = complete_audit(snapshot)
    value["portfolio_source_digest"] = "sha256:" + "b" * 64

    with pytest.raises(ValueError, match="source digest"):
        audit.apply_audit(snapshot, value)


def test_prompt_binds_all_products_and_forbids_uncited_business_defaults() -> None:
    snapshot = base_snapshot()

    prompt = audit_prompt.build_prompt(snapshot)

    assert portfolio.snapshot_digest(snapshot) in prompt
    assert all(product["agent_id"] in prompt for product in snapshot["products"])
    assert "Do not invent" in prompt
    assert "exactly 31" in prompt
    assert "supports" in prompt
    assert "unknowns" in prompt
