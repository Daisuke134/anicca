import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import project_ledger


def test_project_tree_and_ledger_are_request_scoped(tmp_path):
    root = project_ledger.init_project(tmp_path, "req-42", "coconala", {"buyer": "A"})
    assert root.name == "req-42"
    for name in ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence"):
        assert (root / name).is_dir()
    state = project_ledger.append(root, {"current_version": "v1"}, "artifact_created")
    assert state["request_id"] == "req-42"
    events = [json.loads(x) for x in (root / "events.jsonl").read_text().splitlines()]
    assert events[-1]["request_id"] == "req-42"
    assert events[-1]["adapter"] == "coconala"


def test_ledger_rejects_mismatched_request_id(tmp_path):
    root = project_ledger.init_project(tmp_path, "req-a", "lancers")
    try:
        project_ledger.append(root, {"request_id": "req-b"}, "bad")
    except ValueError as exc:
        assert "request_id" in str(exc)
    else:
        raise AssertionError("mismatched request id must fail closed")
