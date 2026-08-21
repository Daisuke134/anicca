#!/usr/bin/env python3
"""Prepare an isolated worktree for a Writer characterization sub-agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    )
    return completed.stdout.strip()


def _atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def _investigation(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("investigation receipt is required")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("schema") != "writer.self-heal.unknown-investigation"
        or value.get("version") != 1
        or value.get("cause_status") != "EVIDENCE_BACKED_HYPOTHESIS"
        or value.get("next_action")
        != "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION"
        or value.get("evidence_gaps") != []
    ):
        raise ValueError("investigation is not ready for characterization")
    fingerprint = str(value.get("fingerprint") or "")
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint):
        raise ValueError("investigation fingerprint is invalid")
    return value


def prepare(
    repo: Path, base_ref: str, repair_root: Path, state_dir: Path,
    investigation_path: Path, observed_at: str,
) -> dict[str, Any]:
    repo = repo.resolve()
    if _git(repo, "status", "--porcelain"):
        raise ValueError("characterization source repository must be clean")
    base_head = _git(repo, "rev-parse", f"{base_ref}^{{commit}}")
    investigation_path = investigation_path.resolve()
    investigation = _investigation(investigation_path)
    fingerprint = investigation["fingerprint"]
    short = fingerprint[:12]
    branch = f"repair/writer-{short}-characterization"
    worktree = repair_root.resolve() / f"writer-{short}-characterization"
    if worktree.exists():
        raise ValueError("characterization worktree already exists")
    branch_exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo, check=False,
    ).returncode == 0
    if branch_exists:
        raise ValueError("characterization branch already exists")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), base_head],
        cwd=repo, check=True, capture_output=True, text=True,
    )

    task_dir = state_dir.resolve() / fingerprint
    agent_receipt = task_dir / "characterization-agent-receipt.json"
    prompt_path = task_dir / "characterization-prompt.txt"
    prompt = f"""You are the Writer self-heal characterization sub-agent.
Read the immutable investigation receipt at {investigation_path}.
Work only in the isolated checkout at {worktree} on branch {branch}.
Create the smallest automated test that reproduces the captured failure.
Do not modify production code. Only paths under skills/writer-agent/tests/ are allowed.
Run the exact new test and record the observed non-zero exit code; a syntax/import error is not an accepted characterization failure.
Do not publish, deploy, push, use credentials, or change runtime state.
Write JSON to {agent_receipt} with schema writer.self-heal.characterization-agent-receipt, version 1, fingerprint, test_path, command as an argv array, exit_code, failure_signature, and observed_at.
Stop after the captured failure is reproducible. Do not propose or implement a fix.
"""
    _atomic(prompt_path, prompt)
    result = {
        "schema": "writer.self-heal.characterization-plan",
        "version": 1,
        "observed_at": observed_at,
        "status": "READY_TO_GENERATE",
        "fingerprint": fingerprint,
        "cause_hypothesis": investigation["cause_hypothesis"],
        "investigation_receipt": {
            "path": str(investigation_path),
            "sha256": hashlib.sha256(investigation_path.read_bytes()).hexdigest(),
        },
        "repo_path": str(repo),
        "base_head": base_head,
        "branch": branch,
        "worktree_path": str(worktree),
        "allowed_paths": ["skills/writer-agent/tests/"],
        "prompt_path": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "agent_receipt_path": str(agent_receipt),
        "next_action": "RUN_CHARACTERIZATION_SUBAGENT",
    }
    _atomic(
        task_dir / "characterization-plan.json",
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--repair-root", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--investigation-receipt", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = prepare(
        args.repo, args.base_ref, args.repair_root, args.state_dir,
        args.investigation_receipt, args.observed_at,
    )
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.out is not None:
        _atomic(args.out, encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
