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
        captured["env"] = kwargs["env"]
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
        cdp_base="http://127.0.0.1:9233",
        runner=tmp_path / "runner.py", schema=tmp_path / "schema.json",
        evidence_root=tmp_path / "evidence",
    )

    assert result["status"] == "ok"
    assert "browser-lane-agent" in captured["command"]
    assert "SEALED_INTENT=" in captured["prompt"]
    assert "#step-rate" not in captured["prompt"]
    assert "hardcoded provider selectors" in captured["prompt"]
    normalized = " ".join(captured["prompt"].split())
    assert "authenticated persistent DEFAULT browser context" in normalized
    assert "Never create an isolated/incognito context" in normalized
    assert "EXACT_CDP_ENDPOINT=http://127.0.0.1:9233" in normalized
    assert "any other CDP endpoint or port" in normalized
    assert "Run `browser-harness skill` once" in normalized
    assert "Do not search the filesystem for its SKILL.md" in normalized
    assert "native prototype value setter" in normalized
    assert "must not submit" in normalized
    assert "account balances are live observations" in normalized
    assert "required charge exceeds the live balance" in normalized
    assert captured["env"]["BU_CDP_URL"] == "http://127.0.0.1:9233"
    assert captured["env"]["BU_NAME"] == "market-form-anymarket"
