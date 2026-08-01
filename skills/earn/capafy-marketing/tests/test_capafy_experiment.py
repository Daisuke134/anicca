import copy
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_experiment as experiment
import capafy_portfolio
import capafy_event_store
import capafy_experiment_prompt
import capafy_experiment_remote


def product(agent_id: str = "3947077924") -> dict:
    return {
        "agent_id": agent_id,
        "name": "Meeting Notes → Action Items & Decisions",
        "description": "Turns meeting notes into decisions and actions.",
        "product_type": "run_online",
        "observed_status": "online",
        "updated_at": "2026-08-02T12:00:00Z",
        "public_url": f"https://capafy.ai/agent/{agent_id}",
        "platform_sales": None,
        "recurring_mechanism": "repeated_workflow",
        "purchase_model": "undecided",
        "value_metric": None,
        "target_customer": "PMs, founders, and EAs running meetings",
        "next_best_alternative": None,
        "renewal_reason": None,
        "evidence": [{"url": f"https://capafy.ai/agent/{agent_id}", "observed_at": "2026-08-02T12:00:00Z", "claim": "The listing supports a repeated meeting workflow.", "confidence": "high", "supports": ["decision"]}],
        "unit_economics": {"gross_usd": None, "cost_usd": None, "contribution_usd": None},
        "decision": "promote",
        "decision_reason": "Evidence-backed recurring workflow.",
        "experiment": None,
        "unknowns": ["observed demand"],
    }


def snapshot() -> dict:
    products = [product(), product("4886968609")]
    return {
        "schema_version": 1, "kind": "capafy_portfolio",
        "observed_at": "2026-08-02T12:00:00Z",
        "inventory_source_digest": "sha256:" + "a" * 64,
        "company_projection_id": "sha256:" + "b" * 64,
        "inventory": {"online": 2, "under_review": 0, "draft": 0, "rejected": 0},
        "products": products,
    }


def proposal(model: str = "subscription") -> dict:
    return {
        "schema_version": 1,
        "kind": "capafy_packaging_experiment",
        "portfolio_source_digest": capafy_portfolio.snapshot_digest(snapshot()),
        "experiment_id": "capafy-exp-meeting-notes-001",
        "agent_id": "3947077924",
        "owner": "marketer",
        "purchase_model": model,
        "price_usd": "10.00",
        "billing_interval": "month" if model in {"subscription", "hybrid"} else None,
        "metered_unit": "completed meeting brief" if model in {"usage", "hybrid"} else None,
        "bounded_deliverable": "One decision-and-action brief" if model in {"one_time", "hybrid"} else None,
        "value_metric": "verified action items delivered",
        "renewal_reason": "New meetings create repeated work" if model in {"subscription", "hybrid"} else None,
        "projected_units": 10,
        "platform_fee_rate": "0.2000",
        "model_cost_per_unit_usd": "0.50",
        "projected_gross_usd": "100.00",
        "projected_platform_fee_usd": "20.00",
        "projected_cost_usd": "5.00",
        "projected_contribution_usd": "75.00",
        "observed_gross_usd": None,
        "observed_cost_usd": None,
        "observed_contribution_usd": None,
        "success_metric": "attributed paid orders and positive contribution",
        "stop_condition": "Stop after 100 verified campaign visits with zero paid orders.",
        "activated_at": "2026-08-02T13:30:00Z",
        "evidence": [
            {"url": "https://capafy.ai/publisher-agreement", "observed_at": "2026-08-02T13:30:00Z", "claim": "Capafy charges a 20% platform service fee.", "confidence": "high"},
            {"url": "https://capafy.ai/agent/3947077924", "observed_at": "2026-08-02T13:30:00Z", "claim": "The listing is a repeated meeting workflow.", "confidence": "high"},
        ],
    }


@pytest.mark.parametrize("model", ["subscription", "usage", "one_time", "hybrid"])
def test_all_purchase_models_have_required_packaging_and_exact_economics(model: str) -> None:
    assert experiment.validate_proposal(snapshot(), proposal(model)) == []


def test_economics_must_equal_price_units_fee_and_recorded_cost() -> None:
    value = proposal()
    value["projected_contribution_usd"] = "95.00"
    assert any("projected_contribution_usd" in e for e in experiment.validate_proposal(snapshot(), value))


def test_model_specific_requirements_fail_closed() -> None:
    value = proposal("subscription")
    value["renewal_reason"] = None
    assert any("renewal_reason" in e for e in experiment.validate_proposal(snapshot(), value))
    value = proposal("usage")
    value["metered_unit"] = None
    assert any("metered_unit" in e for e in experiment.validate_proposal(snapshot(), value))
    value = proposal("one_time")
    value["bounded_deliverable"] = None
    assert any("bounded_deliverable" in e for e in experiment.validate_proposal(snapshot(), value))
    value = proposal("usage")
    value["model_cost_per_unit_usd"] = "0.00"
    value["projected_cost_usd"] = "0.00"
    value["projected_contribution_usd"] = "80.00"
    assert any("compute cost" in e for e in experiment.validate_proposal(snapshot(), value))


def test_activate_exactly_one_eligible_experiment_and_block_replacement() -> None:
    source = snapshot()
    result = experiment.activate(source, proposal())
    active = [p for p in result["products"] if p["experiment"] and p["experiment"]["status"] == "active"]
    assert len(active) == 1
    assert active[0]["agent_id"] == "3947077924"
    replacement = copy.deepcopy(proposal())
    replacement["agent_id"] = "4886968609"
    replacement["experiment_id"] = "capafy-exp-other-001"
    replacement["portfolio_source_digest"] = capafy_portfolio.snapshot_digest(result)
    with pytest.raises(ValueError, match="must be measured"):
        experiment.activate(result, replacement)


def test_revenue_ledger_accepts_experiment_lifecycle_events() -> None:
    assert {"experiment.activated", "experiment.measured", "experiment.stopped"} <= capafy_event_store.EVENT_TYPES
    event = experiment.activation_event(proposal(), "2026-08-02T13:31:00Z")
    assert capafy_event_store.validate_event(event) == []
    assert event["money"]["gross_delta"] == "0.00"
    assert "projected" in " ".join(event["public_evidence"]["labels"])


def test_invalid_active_proposal_can_self_repair_without_touching_other_products() -> None:
    activated = experiment.activate(snapshot(), proposal())
    invalid = proposal()
    invalid["projected_contribution_usd"] = "95.00"

    repaired = experiment.repair_invalid_activation(activated, invalid)

    chosen = repaired["products"][0]
    assert chosen["experiment"] is None
    assert chosen["purchase_model"] == "undecided"
    assert repaired["products"][1] == activated["products"][1]


def test_remote_verifier_requires_exact_download_price_and_confirmed_skill() -> None:
    value = proposal("one_time")
    remote = {
        "ok": True,
        "latest_version": {
            "agentId": value["agent_id"], "agentType": "download", "status": 1,
            "isConfirmedSkills": 1,
            "billings": [{"billingMode": "download", "oneTimeFee": 10.0}],
        },
    }
    assert capafy_experiment_remote.validate_remote(value, remote) == []
    wrong = copy.deepcopy(remote); wrong["latest_version"]["oneTimeFee"] = 9
    wrong["latest_version"]["billings"][0]["oneTimeFee"] = 9
    assert any("one-time fee" in e for e in capafy_experiment_remote.validate_remote(value, wrong))
    cloud = copy.deepcopy(remote); cloud["latest_version"]["agentType"] = "run_online"
    assert any("agentType" in e for e in capafy_experiment_remote.validate_remote(value, cloud))


def test_configuration_event_carries_complete_reporting_contract() -> None:
    event = experiment.configuration_event(proposal("one_time"), "2026-08-02T13:40:00Z")
    assert capafy_event_store.validate_event(event) == []
    assert event["event_type"] == "experiment.configured"
    assert any(label.startswith("success metric: ") for label in event["public_evidence"]["labels"])


def test_active_experiment_can_self_stop_after_remote_platform_rejection() -> None:
    activated = experiment.activate(snapshot(), proposal("one_time"))

    stopped = experiment.stop_active(
        activated,
        proposal("one_time"),
        "Capafy forbids changing an already-online Agent from run-online to Download.",
        "2026-08-02T14:00:00Z",
    )

    chosen = stopped["products"][0]
    assert chosen["experiment"]["status"] == "stopped"
    assert chosen["experiment"]["stop_reason"].startswith("Capafy forbids")
    assert chosen["purchase_model"] == "undecided"
    event = experiment.stopped_event(
        proposal("one_time"), chosen["experiment"]["stop_reason"], "2026-08-02T14:00:00Z"
    )
    assert capafy_event_store.validate_event(event) == []
    assert event["event_type"] == "experiment.stopped"
    assert event["status"] == {"before": "active", "after": "stopped"}
    assert event["money"]["gross_delta"] == "0.00"
    assert experiment.stop_active(
        stopped,
        proposal("one_time"),
        chosen["experiment"]["stop_reason"],
        "2026-08-02T14:01:00Z",
    ) == stopped


def test_prompt_exposes_eligible_products_and_official_fee_evidence_without_price_default() -> None:
    text = capafy_experiment_prompt.build_prompt(snapshot())
    assert "3947077924" in text
    assert "https://capafy.ai/publisher-agreement" in text
    assert "Do not invent" in text
    assert "Choose the price" in text
