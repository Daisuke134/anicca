#!/usr/bin/env python3
"""Run one private contract workspace through build and independent QA, with zero market effects."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import deliverable_verifier
import project_ledger
import workflow_executor


class ProjectWorkerError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _atomic(path: Path, value: Any) -> None:
    body = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != body:
            raise ProjectWorkerError("project_worker_receipt_collision")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(body); handle.flush(); os.fsync(handle.fileno())


def _review_with_agent(root: Path, execution: dict[str, Any], contract: dict[str, Any],
                       agent_runner: Path) -> tuple[str, dict[str, Any]]:
    review_id = hashlib.sha256(_canonical({
        "execution_id": execution["execution_id"], "contract_sha256": execution["contract_sha256"],
    })).hexdigest()
    evidence = root / "acceptance" / "reviewer-evidence" / review_id
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    schema = evidence / "review.schema.json"
    review_schema = {
        "type": "object", "additionalProperties": False,
        "required": ["verdict", "reason", "criteria", "factual_claims"],
        "properties": {
            "verdict": {"enum": ["PASS", "REVISE", "BLOCKED"]},
            "reason": {"type": "string", "minLength": 1},
            "criteria": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["clause", "status", "evidence"], "properties": {
                    "clause": {"type": "string"}, "status": {"enum": ["PASS", "FAIL"]},
                    "evidence": {"type": "string"}}}},
            "factual_claims": {"type": "array", "items": {"type": "object",
                "additionalProperties": False, "required": ["claim", "evidence"], "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                }}},
        },
    }
    _atomic(schema, review_schema)
    prompt = evidence / "prompt.txt"
    artifacts = [{"path": row["path"], "sha256": row["sha256"]} for row in execution["artifacts"]]
    _atomic(prompt, {"instruction": "Independently inspect every artifact against the exact contract scope. Do not edit files or cause external effects. Return only the schema.",
                     "contract_scope": contract["scope"], "artifacts": artifacts})
    completed = subprocess.run([
        sys.executable, str(agent_runner), "--task-class", "diagnostic-agent",
        "--prompt-file", str(prompt), "--schema", str(schema), "--evidence-dir", str(evidence),
        "--task-label", "contract-independent-qa", "--loop", "gig", "--workdir", str(root),
        "--timeout-seconds", "300", "--read-only",
    ], capture_output=True, text=True, timeout=330, check=False)
    if completed.returncode != 0:
        raise ProjectWorkerError("independent_reviewer_failed")
    summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
    result = Path(str(summary.get("result_path") or "")).resolve()
    try:
        result.relative_to(evidence.resolve())
    except ValueError as exc:
        raise ProjectWorkerError("independent_reviewer_result_unowned") from exc
    return f"reviewer:{review_id}", json.loads(result.read_text(encoding="utf-8"))


def run_project(*, workspace: str | Path, revision_sha256: str, skills_root: str | Path,
                agent_runner: str | Path, reviewer: Callable[[Path, dict[str, Any], dict[str, Any]], tuple[str, dict[str, Any]]] | None = None,
                now: datetime | None = None) -> dict[str, Any]:
    root = Path(workspace).expanduser()
    lock_fd = os.open(root / ".project-worker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        verification_path = root / "acceptance" / f"{revision_sha256}.json"
        if verification_path.is_file() and not verification_path.is_symlink():
            return json.loads(verification_path.read_text(encoding="utf-8"))
        execution = workflow_executor.execute_workflow(
            workspace=root, revision_sha256=revision_sha256, skills_root=skills_root,
            agent_runner=agent_runner, now=now or datetime.now(timezone.utc),
        )
        contract_path = root / "requirements" / "revisions" / f"{revision_sha256}.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        reviewer_fn = reviewer
        if reviewer_fn is None:
            reviewer_fn = lambda r, e, c: _review_with_agent(r, e, c, Path(agent_runner))
        context_id, review = reviewer_fn(root, execution, contract)
        verification = deliverable_verifier.verify_deliverables(
            workspace=root, execution_receipt=execution, reviewer_context_id=context_id, review=review,
        )
        receipt = {"version": 1, "state": "qa_complete", "revision_sha256": revision_sha256,
                   "execution_id": execution["execution_id"], "verification": verification,
                   "marketplace_effects": 0}
        _atomic(verification_path, receipt)
        project_ledger.append(root, {"next_action": verification["next_action"],
            "qa_status": verification["status"], "qa_receipt": str(verification_path)}, "project_qa_completed")
        for path in (root, *root.rglob("*")):
            if path.is_symlink():
                raise ProjectWorkerError("project_worker_symlink_rejected")
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--revision-sha256", required=True)
    parser.add_argument("--skills-root", required=True, type=Path)
    parser.add_argument("--agent-runner", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run_project(workspace=args.workspace, revision_sha256=args.revision_sha256,
        skills_root=args.skills_root, agent_runner=args.agent_runner), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
