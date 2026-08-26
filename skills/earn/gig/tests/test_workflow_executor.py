from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workflow_executor as executor  # noqa: E402
from project_workspace import create_workspace  # noqa: E402


NOW = datetime(2026, 8, 23, 0, 0, tzinfo=timezone.utc)


def _contract(**changes):
    value = {
        "version": 1, "provider": "upwork", "contract_id": "contract-1",
        "offer_id": "offer-1", "scope": "Build one tested local REST API integration artifact.",
        "deadline": "2026-09-01", "terms_sha256": "a" * 64,
        "contract_readback_sha256": "b" * 64,
    }
    value.update(changes)
    return value


def _skill(skills: Path) -> tuple[Path, dict]:
    root = skills / "earn" / "example-delivery"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: earn/example-delivery\nversion: 1.0.0\n---\n\n# Build\nCreate the exact local artifact.\n",
        encoding="utf-8",
    )
    bundle, _source, _paths = executor._skill_bundle(root)
    return root, {"skill_id": "earn/example-delivery", "version": "1.0.0", "bundle_sha256": bundle}


def _runner(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env python3
import argparse,json,os,pathlib
p=argparse.ArgumentParser()
for name in ('prompt-file','schema','evidence-dir','task-label','loop','workdir','task-class','timeout-seconds'):
 p.add_argument('--'+name)
a=p.parse_args(); evidence=pathlib.Path(a.evidence_dir); work=pathlib.Path(a.workdir)
evidence.mkdir(parents=True,exist_ok=True); (work/'artifacts').mkdir(parents=True,exist_ok=True)
counter=pathlib.Path(os.environ['FAKE_RUNNER_COUNTER']); counter.write_text(str(int(counter.read_text() or '0')+1) if counter.exists() else '1')
scenario=os.environ.get('FAKE_RUNNER_SCENARIO','ok')
if scenario=='missing': artifacts=['artifacts/missing.txt']
else:
 out=work/'artifacts'/'output.txt'; out.write_text("api_key='sk-live-abcdefghijklmnopqrstuvwxyz'" if scenario=='secret' else 'verified artifact')
 artifacts=['artifacts/output.txt']
result=evidence/'result.json'; result.write_text(json.dumps({'status':'ok','reason':'done','artifacts':artifacts}))
attempts=evidence/'attempts.jsonl'; attempts.write_text(json.dumps({'usage':{'provider_cost_usd':0.125,'tool_cost_usd':0.01}})+'\\n')
(evidence/'summary.json').write_text(json.dumps({'status':'success','result_path':str(result),'attempts_path':str(attempts)}))
""",
        encoding="utf-8",
    )
    os.chmod(path, 0o700)
    return path


def _workspace(tmp_path: Path, contract=None):
    skills = tmp_path / "skills"
    _root, workflow = _skill(skills)
    made = create_workspace(tmp_path / "projects", contract or _contract(), workflow)
    return Path(made["workspace"]), made["revision_sha256"], skills


def test_executes_once_promotes_hashes_cost_and_replays(tmp_path, monkeypatch):
    root, revision, skills = _workspace(tmp_path)
    runner, counter = _runner(tmp_path / "fake_runner.py"), tmp_path / "count"
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(counter))

    first = executor.execute_workflow(workspace=root, revision_sha256=revision, skills_root=skills,
        agent_runner=runner, timeout_seconds=60, now=NOW)
    replay = executor.execute_workflow(workspace=root, revision_sha256=revision, skills_root=skills,
        agent_runner=runner, timeout_seconds=60, now=NOW)

    assert first == replay and counter.read_text() == "1"
    artifact = root / first["artifacts"][0]["path"]
    assert artifact.read_text() == "verified artifact"
    assert first["artifacts"][0]["sha256"] == executor._sha_file(artifact)
    assert first["model_cost_usd"] == 0.125 and first["tool_cost_usd"] == 0.01
    events = (root / "events.jsonl").read_text().splitlines()
    assert sum('"kind":"workflow_execution_completed"' in row for row in events) == 1
    assert first["marketplace_effects"] == 0
    for path in (root, *root.rglob("*")):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


def test_general_agent_executes_without_an_installed_named_skill(tmp_path, monkeypatch):
    workflow = executor.general_agent_workflow()
    made = create_workspace(tmp_path / "projects", _contract(), workflow)
    runner, counter = _runner(tmp_path / "fake_runner.py"), tmp_path / "count"
    empty_skills = tmp_path / "skills"
    empty_skills.mkdir()
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(counter))

    receipt = executor.execute_workflow(
        workspace=made["workspace"], revision_sha256=made["revision_sha256"],
        skills_root=empty_skills, agent_runner=runner, timeout_seconds=60, now=NOW,
    )

    assert receipt["skill_id"] == "general-agent" and counter.read_text() == "1"


@pytest.mark.parametrize("fault", ["uninstalled", "changed_contract", "expired"])
def test_contract_skill_and_deadline_fail_before_runner(tmp_path, monkeypatch, fault):
    root, revision, skills = _workspace(tmp_path)
    runner, counter = _runner(tmp_path / "fake_runner.py"), tmp_path / "count"
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(counter))
    now = NOW
    if fault == "uninstalled":
        skills = tmp_path / "empty-skills"; skills.mkdir()
    elif fault == "changed_contract":
        requirement = root / "requirements" / "revisions" / f"{revision}.json"
        value = json.loads(requirement.read_text()); value["scope"] = "Changed after acceptance"
        requirement.write_text(json.dumps(value)); os.chmod(requirement, 0o600)
    else:
        now = datetime(2026, 9, 2, tzinfo=timezone.utc)

    with pytest.raises(executor.WorkflowExecutionError):
        executor.execute_workflow(workspace=root, revision_sha256=revision, skills_root=skills,
            agent_runner=runner, timeout_seconds=60, now=now)
    assert not counter.exists()


@pytest.mark.parametrize("scenario,reason", [("missing", "artifact_missing"), ("secret", "artifact_secret_leak")])
def test_missing_or_secret_artifact_never_completes(tmp_path, monkeypatch, scenario, reason):
    root, revision, skills = _workspace(tmp_path)
    runner, counter = _runner(tmp_path / "fake_runner.py"), tmp_path / "count"
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(counter))
    monkeypatch.setenv("FAKE_RUNNER_SCENARIO", scenario)

    with pytest.raises(executor.WorkflowExecutionError, match=reason):
        executor.execute_workflow(workspace=root, revision_sha256=revision, skills_root=skills,
            agent_runner=runner, timeout_seconds=60, now=NOW)
    with pytest.raises(executor.WorkflowExecutionError, match=reason):
        executor.execute_workflow(workspace=root, revision_sha256=revision, skills_root=skills,
            agent_runner=runner, timeout_seconds=60, now=NOW)
    assert counter.read_text() == "1"
    receipts = root / "artifacts" / "execution-receipts"
    assert not receipts.exists() or not list(receipts.glob("*.json"))
    assert "workflow_execution_completed" not in (root / "events.jsonl").read_text()
