import copy
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import select_listing
from test_capafy_portfolio_audit import base_snapshot, complete_audit
import capafy_portfolio_audit


def audited_portfolio() -> dict:
    snapshot = base_snapshot()
    value = complete_audit(snapshot)
    for index, item in enumerate(value["products"]):
        item["decision"] = "promote" if index in {0, 1} else "pause"
        item["decision_reason"] = "Evidence-backed portfolio decision."
    return capafy_portfolio_audit.apply_audit(snapshot, value)


def seller_agents(snapshot: dict) -> list[dict]:
    return [
        {
            "agentId": item["agent_id"],
            "agentStatus": "online",
            "name": item["name"],
            "desc": item["description"],
            "sales": item["platform_sales"],
            "rating": None,
        }
        for item in snapshot["products"]
    ]


def test_selector_uses_audited_promote_pool_and_evidence_never_niche_rank() -> None:
    snapshot = audited_portfolio()

    result = select_listing.select_from(seller_agents(snapshot), snapshot, {})

    assert result["ok"] is True
    assert result["agent_id"] == snapshot["products"][0]["agent_id"]
    assert result["eligible_pool"] == 2
    assert result["portfolio_decision"] == "promote"
    assert result["evidence_count"] == 1


def test_selector_refuses_unaudited_paused_retired_and_non_owned_rows() -> None:
    snapshot = audited_portfolio()
    snapshot["products"][0]["decision"] = "unaudited"
    snapshot["products"][1]["decision"] = "pause"
    agents = seller_agents(snapshot) + [
        {"agentId": "9999999999", "agentStatus": "online", "name": "Foreign", "desc": "x"}
    ]

    result = select_listing.select_from(agents, snapshot, {})

    assert result == {"ok": False, "error": "no evidence-eligible owned listings"}


def test_active_or_proposed_experiment_blocks_replacement_until_measured() -> None:
    snapshot = audited_portfolio()
    snapshot["products"][0]["experiment"] = {
        "experiment_id": "exp-existing",
        "owner": "marketer",
        "status": "active",
        "success_metric": "attributed_orders",
        "stop_condition": "100 verified campaign visits with zero orders",
    }

    result = select_listing.select_from(seller_agents(snapshot), snapshot, {})

    assert result["ok"] is False
    assert "must be measured" in result["error"]

    snapshot["products"][0]["experiment"]["status"] = "measured"
    measured = select_listing.select_from(seller_agents(snapshot), snapshot, {})
    assert measured["ok"] is True


def test_rotation_only_breaks_ties_inside_evidence_eligible_pool() -> None:
    snapshot = audited_portfolio()
    first = snapshot["products"][0]["agent_id"]
    second = snapshot["products"][1]["agent_id"]

    result = select_listing.select_from(
        seller_agents(snapshot), snapshot, {first: 200, second: 100}
    )

    assert result["agent_id"] == second
