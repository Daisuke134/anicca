import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "writer_unavailable_incident_bridge.py"
)
def test_unavailable_destination_becomes_durable_agent_incident(tmp_path: Path) -> None:
    assert SCRIPT.is_file(), "production unavailable-to-incident bridge is missing"
    spec = importlib.util.spec_from_file_location(
        "writer_unavailable_incident_bridge", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    state_root = tmp_path / "state"
    run_dir = state_root / "runs" / "run-1"
    gates = run_dir / "gates"
    gates.mkdir(parents=True)
    (gates / "generation-state.json").write_text(
        json.dumps({"run_id": "run-1", "status": "complete"}), encoding="utf-8"
    )
    (gates / "quality-self-heal.json").write_text(
        json.dumps({"run_id": "run-1", "action": "ready_to_freeze"}),
        encoding="utf-8",
    )
    (gates / "publication-state.json").write_text(
        json.dumps({
            "run_id": "run-1",
            "run_dir": str(run_dir),
            "pairs": {
                "x-article/ja": {
                    "status": "unavailable",
                    "error": "x-draft-editor-not-found-after-anchor",
                }
            },
        }),
        encoding="utf-8",
    )

    result = module.bridge(
        state_root=state_root,
        run_id="run-1",
        observed_at="2026-08-06T21:00:00+09:00",
    )

    queue = json.loads(
        (state_root / "self-heal" / "incident-queue.json").read_text(encoding="utf-8")
    )
    incidents = list(queue["items"].values())
    assert result["enqueued"] == 1
    assert len(incidents) == 1
    assert incidents[0]["phase"] == "destination:x-article/ja"
    assert incidents[0]["reason"] == "x-draft-editor-not-found-after-anchor"
    assert incidents[0]["classification"] == "DOM/selector"
    assert incidents[0]["owner"] == "writer-self-heal"
    assert incidents[0]["next_action"] == "CLAIM"

    incomplete = state_root / "runs" / "legacy-incomplete" / "gates"
    incomplete.mkdir(parents=True)
    (incomplete / "publication-state.json").write_text(
        json.dumps({"run_id": "legacy-incomplete", "pairs": {}}), encoding="utf-8"
    )

    all_result = module.bridge_all(
        state_root=state_root, observed_at="2026-08-06T21:01:00+09:00"
    )

    assert all_result["runs"] == 1
    assert all_result["skipped"] == [{
        "run_id": "legacy-incomplete",
        "reason": "generation and quality receipts are required",
    }]
