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


def test_allocator_contract_is_bounded_and_replay_stable() -> None:
    module = load_module()
    retry = {"agent_id": "rejected-1", "title": "Fix Me"}
    fresh = {"feature": "capafy-o1-fresh", "title": "Fresh Skill"}
    cases = [
        ({"readable": False, "counts": {"occupied": None}}, [retry], [fresh], "SERVER_UNREADABLE", None),
        ({"readable": True, "counts": {"occupied": 5}}, [retry], [fresh], "CAP_FULL", None),
        ({"readable": True, "counts": {"occupied": 4}}, [retry], [fresh], "PUBLISHABLE", "retry_existing"),
        ({"readable": True, "counts": {"occupied": 5}}, [], [fresh], "CAP_FULL", None),
        ({"readable": True, "counts": {"occupied": 4}}, [], [fresh], "PUBLISHABLE", "create_fresh"),
        ({"readable": True, "counts": {"occupied": 4}}, [], [], "DRAINED", None),
    ]

    for normalized, retries, publishable, verdict, action in cases:
        first = module.allocate_action(normalized, retries, publishable)
        replay = module.allocate_action(normalized, retries, publishable)
        assert first == replay
        assert first["verdict"] == verdict
        assert first.get("action") == action
        assert int(first.get("action") is not None) <= 1


def test_allocator_selects_only_one_deterministic_candidate() -> None:
    module = load_module()
    normalized = {"readable": True, "counts": {"occupied": 0}}
    candidates = [
        {"feature": "capafy-o2", "title": "Second"},
        {"feature": "capafy-o1", "title": "First"},
    ]

    decision = module.allocate_action(normalized, [], candidates)

    assert decision["action"] == "create_fresh"
    assert decision["action_key"] == "create:capafy-o1"
    assert decision["item"]["feature"] == "capafy-o1"


def test_allocator_resumes_matching_draft_at_full_cap_but_blocks_without_one() -> None:
    module = load_module()
    normalized = {"readable": True, "counts": {"occupied": 5}}
    draft = {
        "agent_id": "draft-42",
        "title": "Portfolio Tracker — Daily Position Review",
        "feature": "catalog:portfolio-tracker",
        "icon": "/catalog/portfolio-tracker/icon.svg",
        "listing": "/catalog/portfolio-tracker/LISTING.md",
        "skill": "/catalog/portfolio-tracker/SKILL.md",
        "source": "repo_catalog",
    }
    retry = {"agent_id": "rejected-1", "title": "Retry Me"}
    fresh = {"feature": "catalog:fresh", "title": "Fresh Skill"}

    resumed = module.allocate_action(normalized, [retry], [fresh], [draft])

    assert resumed["verdict"] == "PUBLISHABLE"
    assert resumed["action"] == "resume_draft"
    assert resumed["action_key"] == "resume:draft-42"
    assert resumed["item"] == draft

    blocked = module.allocate_action(normalized, [retry], [fresh], [])

    assert blocked == {"verdict": "CAP_FULL", "occupied": 5}


def test_repo_catalog_is_ready_and_overrides_same_title_legacy_item(tmp_path: Path) -> None:
    module = load_module()
    features = tmp_path / "features"
    icons = tmp_path / "icons"
    catalog = tmp_path / "catalog"
    legacy = features / "capafy-o1-football"
    canonical = catalog / "football-match-analyst"
    legacy.mkdir(parents=True)
    icons.mkdir()
    canonical.mkdir(parents=True)
    title = "Football Match Analyst — Weekly Fixture Read"
    (legacy / "LISTING.md").write_text(f"## Title\n{title}\n")
    (legacy / "SKILL.md").write_text("legacy")
    (icons / "o1.png").write_bytes(b"png")
    (canonical / "LISTING.md").write_text(f"## Title\n{title}\n")
    (canonical / "SKILL.md").write_text("canonical")
    (canonical / "icon.svg").write_text("<svg/>")
    module.FEATURES = str(features)
    module.ICONS = str(icons)
    module.CATALOG = str(catalog)

    items = module.ready_inventory()

    assert len(items) == 1
    assert items[0]["feature"] == "catalog:football-match-analyst"
    assert items[0]["source"] == "repo_catalog"
