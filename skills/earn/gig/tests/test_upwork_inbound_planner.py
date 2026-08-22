from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts/providers/upwork_inbound_planner.py"
spec = importlib.util.spec_from_file_location("upwork_inbound_planner_test", MODULE)
assert spec and spec.loader
planner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = planner
spec.loader.exec_module(planner)


def _packet(tmp_path):
    value = {
        "version": 1, "provider": "upwork", "kind": "invitation_detected",
        "resource_id": "~invite-1", "resource_url": "https://www.upwork.com/jobs/~invite-1",
        "detail_evidence_sha256": "a" * 64, "observed_at": "now",
        "rendered_text": "Accept and send a proposal. Exact private job. Decline.",
    }
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path = tmp_path / f"{hashlib.sha256(body.encode()).hexdigest()}.json"
    path.write_text(body)
    path.chmod(0o600)
    return path, value


def _decision(packet):
    return {
        "decision": "submit", "reason_codes": [],
        "proposal": {
            "provider": "upwork", "job_id": packet["resource_id"],
            "job_url": packet["resource_url"],
            "job_source_sha256": packet["detail_evidence_sha256"],
            "title": "Exact private job", "status": "frozen_waiting_for_invitation",
            "terms": {"type": "fixed_price", "bid_usd": 75, "delivery_days": 3,
                      "required_connects": 0, "available_connects_before": 0},
            "cover_letter": "I can deliver the exact documented scope using only the facts provided in this invitation.",
            "screening_answers": [], "unsupported_claims": [], "attachments": [],
        },
    }


def test_exact_private_packet_and_decision_seal_zero_connect_proposal(tmp_path):
    path, packet = _packet(tmp_path)

    loaded = planner.load_packet(path)
    proposal = planner.validate_decision(_decision(packet), loaded)

    assert proposal["job_id"] == packet["resource_id"]
    assert proposal["terms"]["required_connects"] == 0
    assert len(proposal["payload_sha256"]) == 64


@pytest.mark.parametrize("mutation", [
    ("job_id", "~other"), ("job_url", "https://www.upwork.com/jobs/~other"),
    ("job_source_sha256", "b" * 64),
])
def test_identity_or_evidence_drift_is_rejected(tmp_path, mutation):
    path, packet = _packet(tmp_path)
    decision = _decision(packet)
    decision["proposal"][mutation[0]] = mutation[1]

    with pytest.raises(ValueError, match="inbound_decision_mismatch"):
        planner.validate_decision(decision, planner.load_packet(path))


def test_skip_requires_reason_and_never_creates_proposal(tmp_path):
    path, _ = _packet(tmp_path)
    packet = planner.load_packet(path)

    assert planner.validate_decision({
        "decision": "skip", "reason_codes": ["not_fully_deliverable"], "proposal": None,
    }, packet) is None
    with pytest.raises(ValueError, match="inbound_decision_invalid"):
        planner.validate_decision({"decision": "skip", "reason_codes": [], "proposal": None}, packet)


def test_existing_runner_cli_contract_returns_owned_private_result(tmp_path):
    packet_path, packet = _packet(tmp_path)
    decision = _decision(packet)
    runner = tmp_path / "runner.py"
    calls = tmp_path / "calls"
    runner.write_text(
        "import json,sys\n"
        "from pathlib import Path\n"
        "args=sys.argv; root=Path(args[args.index('--evidence-dir')+1]); root.mkdir(parents=True,exist_ok=True)\n"
        f"decision={decision!r}\n"
        f"counter=Path({str(calls)!r}); counter.write_text(str(int(counter.read_text())+1) if counter.exists() else '1')\n"
        "result=root/'result.json'; result.write_text(json.dumps(decision))\n"
        "(root/'summary.json').write_text(json.dumps({'status':'success','result_path':str(result.resolve())}))\n"
        "sys.stdin.read()\n"
    )
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"skills": ["Python"]}))
    evidence = tmp_path / "evidence"

    proposal = planner.invoke(
        packet_path, runner=runner, schema=planner.DEFAULT_SCHEMA,
        profile=profile, evidence_dir=evidence,
    )

    assert proposal["payload_sha256"]
    assert evidence.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in evidence.iterdir())
    assert planner.invoke(
        packet_path, runner=runner, schema=planner.DEFAULT_SCHEMA,
        profile=profile, evidence_dir=evidence,
    )["payload_sha256"] == proposal["payload_sha256"]
    assert calls.read_text() == "1"

    sealed = planner.write_sealed_proposal(proposal, tmp_path / "sealed")
    assert sealed.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "sealed").stat().st_mode & 0o777 == 0o700
    assert planner.write_sealed_proposal(proposal, tmp_path / "sealed") == sealed
