from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inventory_status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("inventory_status", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def agent(agent_id: str, status: str, **extra) -> dict:
    return {
        "agentId": agent_id,
        "name": f"Skill {agent_id}",
        "agentStatus": status,
        "agentType": "run_online",
        "latestAgentVersionId": f"v-{agent_id}",
        "latestVersionName": "1.0.0",
        "sales": 2,
        "recentSales": 1,
    } | extra


def test_normalize_agents_returns_exact_slot_and_retry_counts() -> None:
    module = load_module()
    rows = [
        agent("1", "online"),
        agent("2", "approved"),
        agent("3", "draft"),
        agent("4", "under_review"),
        agent("5", "review_rejected"),
        agent("6", "banned"),
    ]

    result = module.normalize_agents(rows)

    assert result["readable"] is True
    assert result["counts"] == {
        "total": 6,
        "listed": 2,
        "occupied": 2,
        "free": 3,
        "retry": 1,
        "blocked": 1,
        "unknown": 0,
    }
    assert result["agents"][2] == {
        "agent_id": "3",
        "name": "Skill 3",
        "latest_version_id": "v-3",
        "latest_version_name": "1.0.0",
        "remote_status": "draft",
        "lifecycle": "occupied",
        "agent_type": "run_online",
        "sales": 2,
        "recent_sales": 1,
    }


def test_unknown_status_fails_closed_without_free_slot_claim() -> None:
    module = load_module()

    result = module.normalize_agents([agent("1", "platform_new_state")])

    assert result["readable"] is False
    assert result["counts"]["occupied"] is None
    assert result["counts"]["free"] is None
    assert result["counts"]["unknown"] == 1


def test_missing_identity_fails_closed() -> None:
    module = load_module()
    row = agent("1", "online")
    row.pop("agentId")

    result = module.normalize_agents([row])

    assert result["readable"] is False
    assert result["counts"]["free"] is None
