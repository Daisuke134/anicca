from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_worker  # noqa: E402
from project_workspace import create_workspace  # noqa: E402
from test_workflow_executor import NOW, _contract, _runner  # noqa: E402
import workflow_executor  # noqa: E402


def test_general_project_builds_reviews_once_and_never_touches_marketplace(tmp_path, monkeypatch):
    workflow = workflow_executor.general_agent_workflow()
    made = create_workspace(tmp_path / "projects", _contract(), workflow)
    runner, build_count = _runner(tmp_path / "builder.py"), tmp_path / "build-count"
    monkeypatch.setenv("FAKE_RUNNER_COUNTER", str(build_count))
    review_count = 0

    def review(_root, _execution, contract):
        nonlocal review_count
        review_count += 1
        return "fresh-reviewer", {"verdict": "PASS", "reason": "Exact scope satisfied.",
            "criteria": [{"clause": contract["scope"], "status": "PASS", "evidence": "Artifact inspected."}],
            "factual_claims": []}

    first = project_worker.run_project(
        workspace=made["workspace"], revision_sha256=made["revision_sha256"],
        skills_root=tmp_path / "empty-skills", agent_runner=runner, reviewer=review, now=NOW,
    )
    replay = project_worker.run_project(
        workspace=made["workspace"], revision_sha256=made["revision_sha256"],
        skills_root=tmp_path / "empty-skills", agent_runner=runner, reviewer=review, now=NOW,
    )

    assert first == replay and first["verification"]["status"] == "PASS"
    assert first["marketplace_effects"] == 0 and build_count.read_text() == "1" and review_count == 1
