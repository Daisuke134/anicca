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
        "title": "Exact private job",
    }
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path = tmp_path / f"{hashlib.sha256(body.encode()).hexdigest()}.json"
    path.write_text(body)
    path.chmod(0o600)
    return path, value


def _decision(packet):
    return {
        "job_id": packet["resource_id"], "decision": "submit",
        "reason_codes": ["この案件はインストール済みSkillで完遂できます。"],
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


def _public_packet(tmp_path, suffix):
    value = {
        "version": 1, "provider": "upwork", "kind": "public_job",
        "resource_id": f"~job-{suffix}",
        "resource_url": f"https://www.upwork.com/jobs/~job-{suffix}",
        "detail_evidence_sha256": suffix * 64, "observed_at": "now",
        "rendered_text": f"Public job {suffix}", "required_connects": 8,
        "available_connects_before": 20, "title": f"Public job {suffix}",
    }
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path = tmp_path / f"{hashlib.sha256(body.encode()).hexdigest()}.json"
    path.write_text(body); path.chmod(0o600)
    return path, value


def test_exact_private_packet_and_decision_seal_zero_connect_proposal(tmp_path):
    path, packet = _packet(tmp_path)

    loaded = planner.load_packet(path)
    proposal = planner.validate_decision(_decision(packet), loaded)

    assert proposal["job_id"] == packet["resource_id"]
    assert proposal["terms"]["required_connects"] == 0
    assert len(proposal["payload_sha256"]) == 64


def test_prompts_require_owner_readable_natural_language_reasons(tmp_path, monkeypatch):
    _, packet = _packet(tmp_path)
    single = planner.planner_prompt(packet, {})
    batch = planner.batch_planner_prompt([packet], {})
    for prompt in (single, batch):
        assert "natural Japanese" in prompt
        assert "snake_case" in prompt
        assert "Installed Skills are execution recipes" in prompt
        assert "never an application whitelist" in prompt
        assert "INSTALLED_SKILLS=" not in prompt
        assert "installed Skills can complete" not in prompt
        assert "Submit is the default for every feasible job" in " ".join(prompt.split())
        assert "unverified payment" in prompt


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
        "job_id": packet["resource_id"], "decision": "skip",
        "reason_codes": ["完全な納品を保証できません。"], "proposal": None,
    }, packet) is None
    with pytest.raises(ValueError, match="inbound_decision_invalid"):
        planner.validate_decision({"job_id": packet["resource_id"], "decision": "skip",
                                   "reason_codes": [], "proposal": None}, packet)


def test_luna_submit_and_skip_project_to_stable_natural_language_work_events(tmp_path):
    path, packet = _packet(tmp_path)
    loaded = planner.load_packet(path)
    submit = _decision(packet)
    skipped = {
        "job_id": packet["resource_id"], "decision": "skip",
        "reason_codes": ["The requested physical filming cannot be completed by installed Skills."],
        "proposal": None,
    }

    submit_event = planner.application_decision_event(
        submit, loaded, title="Exact private job", occurred_at="2026-08-24T08:00:00+00:00",
    )
    skip_event = planner.application_decision_event(
        skipped, loaded, title="On-site filming", occurred_at="2026-08-24T08:00:00+00:00",
    )

    assert submit_event["state"] == "selected"
    assert submit_event["attributes"]["terms"]["bid_usd"] == 75
    assert planner.application_decision_event(
        submit, loaded, title="Exact private job", occurred_at="2026-08-24T08:00:00+00:00",
    )["event_key"] == submit_event["event_key"]
    assert skip_event["state"] == "skipped"
    assert skip_event["attributes"]["reason_codes"] == skipped["reason_codes"]
    assert skip_event["next_action"] == "次の案件確認を続けます"


def test_batch_returns_every_profitable_proposal_and_every_candidate_event(tmp_path, monkeypatch):
    first_path, first = _public_packet(tmp_path, "a")
    second_path, second = _public_packet(tmp_path, "b")
    decisions = [_decision(first), _decision(second)]
    for decision in decisions:
        decision["proposal"]["status"] = "frozen_waiting_for_connects"
        decision["proposal"]["terms"].update(required_connects=8, available_connects_before=20)
    monkeypatch.setattr(planner, "_invoke_prompt", lambda *args, **kwargs: {"decisions": decisions})
    profile = tmp_path / "profile.json"; profile.write_text("{}")

    events = []
    proposals = planner.invoke_batch(
        [first_path, second_path], profile=profile, evidence_dir=tmp_path / "evidence",
        decision_sink=events.extend,
    )

    assert [proposal["job_id"] for proposal in proposals] == [
        first["resource_id"], second["resource_id"],
    ]
    assert all(proposal["terms"]["required_connects"] == 8 for proposal in proposals)
    assert [(event["state"], event["entity_id"]) for event in events] == [
        ("selected", first["resource_id"]),
        ("selected", second["resource_id"]),
    ]


def test_batch_skip_emits_one_natural_decision_per_candidate(tmp_path, monkeypatch):
    first_path, first = _public_packet(tmp_path, "a")
    second_path, second = _public_packet(tmp_path, "b")
    decisions = [{
        "job_id": packet["resource_id"], "decision": "skip",
        "reason_codes": [f"{packet['title']}は期待利益が正ではありません。"], "proposal": None,
    } for packet in (first, second)]
    monkeypatch.setattr(planner, "_invoke_prompt", lambda *args, **kwargs: {"decisions": decisions})
    profile = tmp_path / "profile.json"; profile.write_text("{}")
    events = []

    assert planner.invoke_batch(
        [first_path, second_path], profile=profile, evidence_dir=tmp_path / "evidence",
        decision_sink=events.extend,
    ) == []
    assert [(event["state"], event["entity_id"]) for event in events] == [
        ("skipped", first["resource_id"]), ("skipped", second["resource_id"]),
    ]
    assert [event["attributes"]["reason_codes"] for event in events] == [
        decision["reason_codes"] for decision in decisions
    ]


def test_existing_runner_cli_contract_returns_owned_private_result(tmp_path):
    packet_path, packet = _packet(tmp_path)
    decision = _decision(packet)
    runner = tmp_path / "runner.py"
    calls = tmp_path / "calls"
    runner.write_text(
        "import json,sys\n"
        "from pathlib import Path\n"
        "args=sys.argv; root=Path(args[args.index('--evidence-dir')+1]); root.mkdir(parents=True,exist_ok=True)\n"
        f"decision={{'decisions':[{decision!r}]}}\n"
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
