from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "topic_router.py"


def _replacement(run_id: str, topic_id: str) -> dict[str, object]:
    items = [{"id": "editorial-1", "lang": "ja", "kind": "editorial_fix", "text": "cite evidence"}]
    unsigned = {"version": 1, "items": items}
    feedback = {
        **unsigned,
        "feedback_sha256": hashlib.sha256(
            json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    return {
        "replacement_run_id": run_id,
        "replaced_run_id": "prior-run",
        "forbidden_topic_id": topic_id,
        "forbidden_editorial_form": "comparison",
        "quality_failure_feedback": feedback,
    }


def test_reroute_receipt_preserves_topic_id_despite_replacement_topic_ban(tmp_path: Path) -> None:
    """A repaired in-run reroute changes only form, not the replacement topic."""
    run_id = "20260805-162010"
    topic_id = "paid-demand:stable-topic"
    runs_root = tmp_path / "runs"
    gates = runs_root / run_id / "gates"
    gates.mkdir(parents=True)
    (gates / "topic-route.json").write_text(
        json.dumps({"topic_id": topic_id, "editorial_form": "how-to"}), encoding="utf-8"
    )
    (gates / "quality-self-heal.json").write_text(
        json.dumps({"version": 2, "attempt": 1, "action": "reroute", "forbidden_editorial_form": "how-to", "required_changes": ["editorial_form", "outline"]}),
        encoding="utf-8",
    )
    (gates / "quality-replacement.json").write_text(json.dumps(_replacement(run_id, topic_id)), encoding="utf-8")
    source = {
        "topic_id": topic_id,
        "topic_source": "explicit-queue",
        "reader": {"audience": "solo creator", "job": "build a content funnel", "outcome": "publish a cited guide"},
        "evidence_plan": [{"method": "browse", "ref": "https://example.com/evidence", "addresses_feedback": ["editorial-1"]}],
        "editorial_form": "explainer",
        "product_link": {"audience": "creator"},
    }
    input_path = tmp_path / "route-input.json"
    out_path = gates / "rerouted.json"
    input_path.write_text(json.dumps(source), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROUTER), "validate", "--input", str(input_path), "--out", str(out_path), "--runs-root", str(runs_root), "--current-run-id", run_id],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(out_path.read_text(encoding="utf-8"))["editorial_form"] == "explainer"
