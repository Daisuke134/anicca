from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "candidate_backlog.py"
DAILY = Path(__file__).parents[1] / "scripts" / "daily_loop.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("candidate_backlog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def candidate_tree(tmp_path: Path) -> tuple[Path, Path]:
    features = tmp_path / "features"
    icons = tmp_path / "icons"
    candidate = features / "capafy-o13-interviews"
    (candidate / "test").mkdir(parents=True)
    icons.mkdir()
    (candidate / "SKILL.md").write_text("# Interview Synthesizer\n")
    (candidate / "LISTING.md").write_text("## Title\nInterview Synthesizer\n")
    (candidate / "test" / "case1.md").write_text("input -> expected output\n")
    (icons / "o13.png").write_bytes(b"png")
    return features, icons


def inventory(status: str | None = None) -> dict:
    agents = [] if status is None else [{"name": "Interview Synthesizer", "remote_status": status}]
    return {"readable": True, "agents": agents, "counts": {"occupied": 5, "free": 0}}


def test_refresh_registers_complete_offline_candidate_without_platform_agent(tmp_path: Path) -> None:
    module = load_module()
    features, icons = candidate_tree(tmp_path)

    backlog = module.refresh_backlog({}, inventory(), features, icons, "2026-08-22T12:00:00Z")

    item = backlog["items"][0]
    assert item["candidate_id"] == "capafy-o13-interviews"
    assert item["platform_state"] == "not_submitted"
    assert item["state"] == "ready"
    assert item["gates"] == {"skill": "pass", "listing": "pass", "icon": "pass", "tests": "pass"}
    assert item["content_sha256"].startswith("sha256:")
    assert "agent_id" not in item


def test_platform_match_advances_backlog_without_creating_another_candidate(tmp_path: Path) -> None:
    module = load_module()
    features, icons = candidate_tree(tmp_path)
    first = module.refresh_backlog({}, inventory(), features, icons, "2026-08-22T12:00:00Z")
    second = module.refresh_backlog(first, inventory("under_review"), features, icons, "2026-08-22T13:00:00Z")

    assert len(second["items"]) == 1
    assert second["items"][0]["platform_state"] == "under_review"
    assert second["items"][0]["state"] == "submitted"


def test_incomplete_candidate_is_not_ready(tmp_path: Path) -> None:
    module = load_module()
    features, icons = candidate_tree(tmp_path)
    (features / "capafy-o13-interviews" / "test" / "case1.md").unlink()

    backlog = module.refresh_backlog({}, inventory(), features, icons, "2026-08-22T12:00:00Z")

    assert backlog["items"][0]["state"] == "building"
    assert backlog["items"][0]["gates"]["tests"] == "missing"


def test_atomic_write_is_private(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "state" / "backlog.json"
    module.atomic_write(output, {"schema_version": 1, "items": []})

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert json.loads(output.read_text())["items"] == []


def test_daily_loop_refreshes_backlog_before_cap_full_exit() -> None:
    source = DAILY.read_text()
    refresh = source.index("candidate_backlog.py")
    cap_full = source.index("DRAINED|CAP_FULL")

    assert refresh < cap_full
    assert "--inventory-stdin" in source
