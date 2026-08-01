import copy
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_portfolio
import capafy_portfolio_cleanup as cleanup
import capafy_portfolio_cleanup_prompt as cleanup_prompt
from test_capafy_portfolio_audit import base_snapshot, complete_audit
import capafy_portfolio_audit


def portfolio() -> dict:
    snapshot = base_snapshot()
    return capafy_portfolio_audit.apply_audit(snapshot, complete_audit(snapshot))


def evidence(agent_id: str) -> list[dict]:
    return [{
        "url": f"https://capafy.ai/agent/{agent_id}",
        "observed_at": "2026-08-02T13:00:00Z",
        "claim": "The cited listing and portfolio state support this cleanup action.",
        "confidence": "high",
    }]


def item(agent_id: str, trigger: str, related: list[str] | None = None) -> dict:
    return {
        "agent_id": agent_id,
        "triggers": [trigger],
        "related_agent_ids": related or [],
        "action": "repair" if trigger != "overlap" else "reposition",
        "action_reason": "One bounded change is justified by the cited current state.",
        "stop_condition": "Stop after one submission if remote status is not verified.",
        "evidence": evidence(agent_id),
        "status": "queued",
        "remote_url": None,
    }


def complete_cleanup(snapshot: dict) -> dict:
    mandatory = [p for p in snapshot["products"] if p["observed_status"] != "online"]
    items = [item(p["agent_id"], p["observed_status"]) for p in mandatory]
    items.append(item(snapshot["products"][4]["agent_id"], "overlap", [snapshot["products"][5]["agent_id"]]))
    return {
        "schema_version": 1,
        "kind": "capafy_portfolio_cleanup",
        "portfolio_source_digest": capafy_portfolio.snapshot_digest(snapshot),
        "created_at": "2026-08-02T13:00:00Z",
        "items": items,
    }


def test_cleanup_requires_every_non_online_item_and_one_overlap_group() -> None:
    snapshot = portfolio()
    value = complete_cleanup(snapshot)

    assert cleanup.validate_cleanup(snapshot, value) == []
    result = cleanup.apply_cleanup(snapshot, value)
    by_id = {p["agent_id"]: p for p in result["products"]}
    assert all(by_id[item["agent_id"]]["decision"] in {"repair", "reposition"} for item in value["items"])


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda value: value["items"].pop(0), "mandatory"),
        (lambda value: value["items"].pop(), "overlap"),
        (lambda value: value["items"][0].update({"action": "delete"}), "action"),
        (lambda value: value["items"][0].update({"stop_condition": ""}), "stop_condition"),
        (lambda value: value["items"][0]["evidence"].clear(), "evidence"),
    ],
)
def test_cleanup_rejects_partial_destructive_or_unbounded_output(mutation, expected) -> None:
    snapshot = portfolio()
    value = complete_cleanup(snapshot)
    mutation(value)

    assert any(expected in error for error in cleanup.validate_cleanup(snapshot, value))


def test_retire_candidate_is_excluded_immediately_without_remote_delete() -> None:
    snapshot = portfolio()
    value = complete_cleanup(snapshot)
    value["items"][0]["action"] = "retire_candidate"
    value["items"][0]["status"] = "retired"

    result = cleanup.apply_cleanup(snapshot, value)

    by_id = {product["agent_id"]: product for product in result["products"]}
    assert by_id[value["items"][0]["agent_id"]]["decision"] == "retire_candidate"
    assert value["items"][0]["remote_url"] is None


def test_cleanup_prompt_names_mandatory_ids_and_forbids_remote_delete() -> None:
    snapshot = portfolio()
    prompt = cleanup_prompt.build_prompt(snapshot)

    mandatory = [p["agent_id"] for p in snapshot["products"] if p["observed_status"] != "online"]
    assert all(agent_id in prompt for agent_id in mandatory)
    assert "Do not delete" in prompt
    assert "overlap" in prompt
    assert capafy_portfolio.snapshot_digest(snapshot) in prompt
