from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import market_form_operator as operator  # noqa: E402


def test_common_operator_passes_sealed_intent_to_terra_without_provider_selectors(tmp_path, monkeypatch):
    captured = {}

    class Completed:
        returncode = 0

    def run(command, **kwargs):
        captured["command"] = command
        captured["prompt"] = kwargs["input"]
        evidence = Path(command[command.index("--evidence-dir") + 1])
        result = evidence / "result.json"
        result.write_text(json.dumps({"status": "ok", "summary": "submitted", "evidence": ["page"]}))
        (evidence / "summary.json").write_text(json.dumps({
            "status": "success", "result_path": str(result.resolve()),
        }))
        return Completed()

    monkeypatch.setattr(operator.subprocess, "run", run)
    result = operator.operate(
        provider="anymarket", resource_id="job-1", form_url="https://example.com/apply",
        sealed_intent={"price": 40, "proposal": "truthful"},
        runner=tmp_path / "runner.py", schema=tmp_path / "schema.json",
        evidence_root=tmp_path / "evidence",
    )

    assert result["status"] == "ok"
    assert "browser-lane-agent" in captured["command"]
    assert "SEALED_INTENT=" in captured["prompt"]
    assert "#step-rate" not in captured["prompt"]
    assert "hardcoded provider selectors" in captured["prompt"]
