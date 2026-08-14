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


def residual_snapshot() -> dict:
    original = base_snapshot()
    governed = audit.apply_audit(original, complete_audit(original))
    agents = inventory_agents() + [
        {
            "agentId": "5648342153",
            "name": "Amazon Listing Images — 7-Slot Kit",
            "desc": "Create a bounded buyer-run image brief.",
            "agentType": "download",
            "agentStatus": "under_review",
            "hasOnlineVersion": False,
            "latestAgentVersionId": "2085631800000000000",
            "updatedAt": 1785631800000,
            "sales": None,
        }
    ]
    return portfolio.refresh_snapshot(
        governed, agents, company_projection(), "2026-08-02T12:45:00Z"
    )


def residual_audit(snapshot: dict) -> dict:
    return {
        "schema_version": 1,
        "kind": "capafy_portfolio_audit",
        "portfolio_source_digest": portfolio.snapshot_digest(snapshot),
        "audited_at": "2026-08-02T13:00:00Z",
        "products": [
            audit_product(product)
            for product in snapshot["products"]
            if product["decision"] == "unaudited"
        ],
    }


def test_residual_audit_updates_only_exact_unaudited_set() -> None:
    snapshot = residual_snapshot()
    before = copy.deepcopy(snapshot)

    result = audit.apply_residual_audit(snapshot, residual_audit(snapshot))

    assert audit.validate_residual_audit(before, residual_audit(before)) == []
    old_by_id = {product["agent_id"]: product for product in before["products"]}
    new_by_id = {product["agent_id"]: product for product in result["products"]}
    assert new_by_id["5648342153"]["decision"] == "pause"
    for agent_id, old in old_by_id.items():
        if agent_id != "5648342153":
            assert new_by_id[agent_id] == old


def test_residual_audit_rejects_missing_or_already_governed_ids() -> None:
    snapshot = residual_snapshot()
    missing = residual_audit(snapshot)
    missing["products"] = []
    governed = residual_audit(snapshot)
    governed["products"] = [audit_product(snapshot["products"][0])]

    assert any("exact unaudited" in error for error in audit.validate_residual_audit(snapshot, missing))
    assert any("exact unaudited" in error for error in audit.validate_residual_audit(snapshot, governed))


def test_residual_audit_does_not_revalidate_preserved_legacy_evidence() -> None:
    snapshot = residual_snapshot()
    governed = next(product for product in snapshot["products"] if product["decision"] != "unaudited")
    governed["evidence"] = [
        {
            "url": f"https://capafy.ai/agent/{governed['agent_id']}",
            "observed_at": "2026-08-02T12:50:00Z",
            "claim": "Terminal cleanup evidence intentionally has no audit supports field.",
            "confidence": "high",
        }
    ]

    assert audit.validate_residual_audit(snapshot, residual_audit(snapshot)) == []


def test_prompt_binds_all_products_and_forbids_uncited_business_defaults() -> None:
    snapshot = base_snapshot()

    prompt = audit_prompt.build_prompt(snapshot)

    assert portfolio.snapshot_digest(snapshot) in prompt
    assert all(product["agent_id"] in prompt for product in snapshot["products"])
    assert "Do not invent" in prompt
    assert "exactly 31" in prompt
    assert "supports" in prompt
    assert "unknowns" in prompt


def test_residual_prompt_binds_only_exact_unaudited_products() -> None:
    snapshot = residual_snapshot()

    prompt = audit_prompt.build_residual_prompt(snapshot)

    assert portfolio.snapshot_digest(snapshot) in prompt
    assert "exactly 1" in prompt
    assert "5648342153" in prompt
    assert snapshot["products"][0]["agent_id"] not in prompt


def test_residual_prompt_includes_only_sanitized_remote_commercial_facts() -> None:
    snapshot = residual_snapshot()
    remote = {
        "latest_version": {
            "agentId": "5648342153",
            "agentVersionId": "version-1",
            "agentType": "download",
            "status": 1,
            "auditStatus": 2,
            "isConfirmedSkills": 1,
            "title": "Amazon Listing Images — 7-Slot Kit",
            "shortDescription": "A bounded local seven-slot image-gallery kit.",
            "detailedDescription": "Buyer supplies local image-generation access.",
            "billings": [{"billingMode": "download", "oneTimeFee": 49.0, "currency": "usd"}],
            "requiredCredentials": "must-not-enter-prompt",
        }
    }

    prompt = audit_prompt.build_residual_prompt(snapshot, {"5648342153": remote})

    assert '"one_time_fee":49.0' in prompt
    assert '"is_confirmed_skills":1' in prompt
    assert "must-not-enter-prompt" not in prompt
