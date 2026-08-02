import copy
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_packaging_decision as packaging
import capafy_packaging_decision_prompt as packaging_prompt
import capafy_portfolio


def product(agent_id: str = "5051239796") -> dict:
    return {
        "agent_id": agent_id,
        "name": "Cold Email Writer",
        "description": "Writes cold-email sequences from supplied offer facts.",
        "product_type": "run_online",
        "observed_status": "online",
        "updated_at": "2026-08-02T01:30:00Z",
        "public_url": f"https://capafy.ai/agent/{agent_id}",
        "platform_sales": None,
        "recurring_mechanism": "repeated_workflow",
        "purchase_model": "undecided",
        "value_metric": None,
        "target_customer": "Founders and outbound teams",
        "next_best_alternative": None,
        "renewal_reason": None,
        "evidence": [{
            "url": f"https://capafy.ai/agent/{agent_id}",
            "observed_at": "2026-08-02T01:30:00Z",
            "claim": "The listing supports repeated outbound campaigns.",
            "confidence": "high",
            "supports": ["decision"],
        }],
        "unit_economics": {
            "gross_usd": None,
            "cost_usd": None,
            "contribution_usd": None,
        },
        "decision": "promote",
        "decision_reason": "Evidence-backed repeated workflow.",
        "experiment": None,
        "unknowns": ["Purchase model", "Value metric", "Renewal reason", "Observed demand"],
    }


def snapshot() -> dict:
    return {
        "schema_version": 1,
        "kind": "capafy_portfolio",
        "observed_at": "2026-08-02T01:30:00Z",
        "inventory_source_digest": "sha256:" + "a" * 64,
        "company_projection_id": "sha256:" + "b" * 64,
        "inventory": {"online": 2, "under_review": 0, "draft": 0, "rejected": 0},
        "products": [product(), product("4886968609")],
    }


def decision() -> dict:
    source = snapshot()
    return {
        "schema_version": 1,
        "kind": "capafy_packaging_decision",
        "portfolio_source_digest": capafy_portfolio.snapshot_digest(source),
        "decided_at": "2026-08-02T02:00:00Z",
        "agent_id": "5051239796",
        "purchase_model": "subscription",
        "price_usd": "5.99",
        "billing_interval": "month",
        "included_units": 60,
        "metered_unit": "completed cold-email request",
        "bounded_deliverable": None,
        "value_metric": "up to 60 completed cold-email requests per month",
        "renewal_reason": "Ongoing outbound campaigns require fresh sequences and follow-ups.",
        "platform_fee_rate": "0.2000",
        "input_tokens_per_unit": 10000,
        "output_tokens_per_unit": 4000,
        "input_price_per_million_usd": "0.30",
        "output_price_per_million_usd": "2.50",
        "compute_assumption": "Conservative ceiling per completed request; observed usage remains unknown.",
        "gross_usd": "5.99",
        "platform_fee_usd": "1.20",
        "cost_usd": "0.78",
        "contribution_usd": "4.01",
        "resolved_unknowns": ["Purchase model", "Value metric", "Renewal reason"],
        "evidence": [
            {
                "url": "https://capafy.ai/agent/5051239796",
                "observed_at": "2026-08-02T02:00:00Z",
                "claim": "The configured monthly plan is $5.99 for 60 requests.",
                "confidence": "high",
                "supports": ["price_usd", "included_units", "purchase_model", "value_metric", "renewal_reason"],
            },
            {
                "url": "https://capafy.ai/publisher-agreement",
                "observed_at": "2026-08-02T02:00:00Z",
                "claim": "Capafy charges a 20% platform service fee.",
                "confidence": "high",
                "supports": ["platform_fee_rate"],
            },
            {
                "url": "https://ai.google.dev/gemini-api/docs/pricing",
                "observed_at": "2026-08-02T02:00:00Z",
                "claim": "Gemini 3.5 Flash-Lite costs $0.30/M input and $2.50/M output tokens.",
                "confidence": "high",
                "supports": ["model_pricing"],
            },
        ],
    }


def test_apply_records_packaging_without_activating_an_experiment() -> None:
    source = snapshot()
    result = packaging.apply_decision(source, decision())

    chosen = result["products"][0]
    assert chosen["purchase_model"] == "subscription"
    assert chosen["value_metric"] == "up to 60 completed cold-email requests per month"
    assert chosen["renewal_reason"].startswith("Ongoing outbound")
    assert chosen["unit_economics"] == {
        "gross_usd": "5.99", "cost_usd": "0.78", "contribution_usd": "4.01"
    }
    assert chosen["experiment"] is None
    assert chosen["unknowns"] == ["Observed demand"]
    assert result["products"][1] == source["products"][1]


def test_exact_package_economics_use_unrounded_token_cost() -> None:
    value = decision()
    value["cost_usd"] = "0.60"
    value["contribution_usd"] = "4.19"

    errors = packaging.validate_decision(snapshot(), value)

    assert any("cost_usd does not match" in error for error in errors)


def test_official_platform_fee_must_be_exactly_twenty_percent() -> None:
    value = decision()
    value["platform_fee_rate"] = "0.2037"
    value["platform_fee_usd"] = "1.22"
    value["contribution_usd"] = "3.99"

    assert any("official 0.2000" in error for error in packaging.validate_decision(snapshot(), value))


@pytest.mark.parametrize("field", ["price_usd", "included_units", "purchase_model", "value_metric", "renewal_reason", "platform_fee_rate", "model_pricing"])
def test_every_commercial_assertion_requires_field_specific_evidence(field: str) -> None:
    value = decision()
    for item in value["evidence"]:
        if field in item["supports"]:
            item["supports"].remove(field)

    assert any(field in error and "evidence" in error for error in packaging.validate_decision(snapshot(), value))


def test_decision_rejects_stale_ineligible_or_already_decided_products() -> None:
    stale = decision()
    stale["portfolio_source_digest"] = "sha256:" + "c" * 64
    assert any("digest" in error for error in packaging.validate_decision(snapshot(), stale))

    ineligible = snapshot()
    ineligible["products"][0]["decision"] = "pause"
    candidate = decision()
    candidate["portfolio_source_digest"] = capafy_portfolio.snapshot_digest(ineligible)
    assert any("eligible" in error for error in packaging.validate_decision(ineligible, candidate))

    decided = snapshot()
    decided["products"][0]["purchase_model"] = "subscription"
    candidate = decision()
    candidate["portfolio_source_digest"] = capafy_portfolio.snapshot_digest(decided)
    assert any("undecided" in error for error in packaging.validate_decision(decided, candidate))


def test_resolved_unknowns_must_be_an_exact_subset_of_the_selected_product() -> None:
    value = decision()
    value["resolved_unknowns"] = ["Not present"]

    assert any("resolved_unknowns" in error for error in packaging.validate_decision(snapshot(), value))


def test_apply_rejects_a_second_packaging_write() -> None:
    first = packaging.apply_decision(snapshot(), decision())
    retry = copy.deepcopy(decision())
    retry["portfolio_source_digest"] = capafy_portfolio.snapshot_digest(first)

    with pytest.raises(ValueError, match="undecided"):
        packaging.apply_decision(first, retry)


def test_prompt_scopes_one_product_and_sanitizes_remote_commercial_facts() -> None:
    remote = {
        "latest_version": {
            "agentId": "5051239796",
            "agentType": "run_online",
            "title": "Cold Email Writer",
            "billings": [
                {"billingMode": "subscription", "cycleType": "month", "cyclePrice": 5.99, "cycleMaxMessageCount": 60}
            ],
            "config": {"API_KEY": "must-not-leak"},
        }
    }

    text = packaging_prompt.build_prompt(snapshot(), "5051239796", remote)

    assert '"agent_id":"5051239796"' in text
    assert '"agent_id":"4886968609"' not in text
    assert '"cycle_price":5.99' in text
    assert '"included_units":60' in text
    assert "must-not-leak" not in text
    assert "observed demand remains unknown" in text
    assert "platform_fee_rate must be exactly 0.2000" in text
