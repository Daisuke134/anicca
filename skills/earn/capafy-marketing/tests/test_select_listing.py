import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/select_listing.py"


def load_module():
    spec = importlib.util.spec_from_file_location("select_listing", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_choose_only_uses_online_agents_with_repo_evidence_and_does_not_commit(tmp_path: Path) -> None:
    module = load_module()
    evidence = tmp_path / "evidence"
    (evidence / "2").mkdir(parents=True)
    (evidence / "2/case1.md").write_text("input and verified output")
    agents = [
        {"agentId": "1", "agentStatus": "online", "name": "No evidence"},
        {"agentId": "2", "agentStatus": "online", "name": "Ready"},
        {"agentId": "3", "agentStatus": "draft", "name": "Not online"},
    ]

    result = module.choose(agents, {}, evidence)

    assert result["agent_id"] == "2"
    assert result["evidence_source"] == str(evidence / "2/case1.md")
    assert result["selection_committed"] is False
    assert result["evidence_ready_pool"] == 1


def test_rotation_changes_only_after_explicit_commit(tmp_path: Path) -> None:
    module = load_module()
    rotation = tmp_path / "rotation.jsonl"

    module._record("2", str(rotation))

    assert '"agent_id": "2"' in rotation.read_text()
