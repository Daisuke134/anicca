#!/usr/bin/env python3
"""Execute and independently verify a Writer characterization sub-agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any


FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
INFRASTRUCTURE_FAILURES = (
    "error collecting",
    "syntaxerror",
    "importerror",
    "modulenotfounderror",
    "filenotfounderror",
    "no tests ran",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"unsafe JSON path: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _git(worktree: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=worktree, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _safe_relative_path(value: str, allowed_prefix: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("./"):
        raise ValueError(f"unsafe relative path: {value}")
    if not value.startswith(allowed_prefix) or value == allowed_prefix:
        raise ValueError(f"path outside allowed scope: {value}")
    return value


def _changed_paths(worktree: Path) -> list[str]:
    lines = _git(worktree, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    paths: list[str] = []
    for line in lines:
        if len(line) < 4:
            raise ValueError(f"unparseable git status entry: {line}")
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value)
    return sorted(paths)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def execute(
    plan_path: Path | str,
    model_runner: Path | str,
    out_path: Path | str,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    plan_path = Path(plan_path)
    model_runner = Path(model_runner)
    out_path = Path(out_path)
    plan = _read_json(plan_path)
    if (
        plan.get("schema") != "writer.self-heal.characterization-plan"
        or plan.get("version") != 1
        or plan.get("status") != "READY_TO_GENERATE"
    ):
        raise ValueError("unsupported characterization plan")
    fingerprint = plan.get("fingerprint")
    if not isinstance(fingerprint, str) or FINGERPRINT_RE.fullmatch(fingerprint) is None:
        raise ValueError("invalid incident fingerprint")
    if plan.get("allowed_paths") != ["skills/writer-agent/tests/"]:
        raise ValueError("characterization plan must be test-only")

    worktree = Path(plan["worktree_path"])
    if not worktree.is_absolute() or worktree.is_symlink() or not worktree.is_dir():
        raise ValueError("unsafe characterization worktree")
    prompt_path = Path(plan["prompt_path"])
    if not prompt_path.is_absolute() or prompt_path.is_symlink() or not prompt_path.is_file():
        raise ValueError("unsafe prompt path")
    if not model_runner.is_absolute() or model_runner.is_symlink() or not model_runner.is_file():
        raise ValueError("unsafe model runner")
    if not os.access(model_runner, os.X_OK):
        raise ValueError("model runner is not executable")
    if _git(worktree, "branch", "--show-current") != plan.get("branch"):
        raise ValueError("worktree branch does not match plan")
    if _git(worktree, "rev-parse", "HEAD") != plan.get("base_head"):
        raise ValueError("worktree base does not match plan")
    if _changed_paths(worktree):
        raise ValueError("characterization worktree must start clean")

    agent_run = subprocess.run(
        [str(model_runner), "agent", "--prompt-file", str(prompt_path)],
        cwd=worktree,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    changed_paths = _changed_paths(worktree)
    if not changed_paths:
        raise ValueError("characterization agent produced no test")
    allowed_prefix = "skills/writer-agent/tests/"
    for changed_path in changed_paths:
        _safe_relative_path(changed_path, allowed_prefix)

    agent_receipt_path = Path(plan["agent_receipt_path"])
    agent_receipt = _read_json(agent_receipt_path)
    if (
        agent_receipt.get("schema") != "writer.self-heal.characterization-agent-receipt"
        or agent_receipt.get("version") != 1
        or agent_receipt.get("fingerprint") != fingerprint
    ):
        raise ValueError("invalid characterization agent receipt")
    test_path = _safe_relative_path(agent_receipt.get("test_path", ""), allowed_prefix)
    if test_path not in changed_paths:
        raise ValueError("receipt test was not created by this agent run")
    command = agent_receipt.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
        raise ValueError("safe argv command required")
    if command != ["python3", "-m", "pytest", "-q", test_path]:
        raise ValueError("verification command must use exact pytest argv")
    failure_signature = agent_receipt.get("failure_signature")
    if not isinstance(failure_signature, str) or not failure_signature.strip():
        raise ValueError("failure signature required")

    verification_environment = os.environ.copy()
    verification_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    verification_environment["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    verification = subprocess.run(
        command,
        cwd=worktree,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=verification_environment,
    )
    verified_changed_paths = _changed_paths(worktree)
    for changed_path in verified_changed_paths:
        try:
            _safe_relative_path(changed_path, allowed_prefix)
        except ValueError as error:
            raise ValueError(
                "verification changed path outside allowed scope"
            ) from error
    if verified_changed_paths != changed_paths:
        raise ValueError("verification changed the characterization test set")
    combined_output = verification.stdout + verification.stderr
    lowered_output = combined_output.lower()
    if verification.returncode == 0:
        raise ValueError("generated characterization test did not reproduce the failure")
    if any(marker in lowered_output for marker in INFRASTRUCTURE_FAILURES):
        raise ValueError("generated test failed because of collection or infrastructure")
    if failure_signature not in combined_output:
        raise ValueError("observed failure does not contain the claimed signature")

    change_receipts = []
    for changed_path in changed_paths:
        changed_file = worktree / changed_path
        if changed_file.is_symlink() or not changed_file.is_file():
            raise ValueError(f"changed path is not a regular file: {changed_path}")
        change_receipts.append({
            "path": changed_path,
            "sha256": hashlib.sha256(changed_file.read_bytes()).hexdigest(),
        })
    result = {
        "schema": "writer.self-heal.characterization-receipt",
        "version": 1,
        "status": "RED_VERIFIED",
        "fingerprint": fingerprint,
        "worktree_path": str(worktree),
        "branch": plan["branch"],
        "base_head": plan["base_head"],
        "test_path": test_path,
        "command": command,
        "observed_exit_code": verification.returncode,
        "failure_signature": failure_signature,
        "output_excerpt": combined_output[-4000:],
        "changed_paths": changed_paths,
        "change_receipts": change_receipts,
        "agent_receipt_path": str(agent_receipt_path),
        "agent_receipt_sha256": hashlib.sha256(agent_receipt_path.read_bytes()).hexdigest(),
        "model_runner_exit_code": agent_run.returncode,
        "model_runner_output_excerpt": (agent_run.stdout + agent_run.stderr)[-2000:],
        "next_action": "GENERATE_CANDIDATE_FIX",
    }
    _atomic_write_json(out_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--model-runner", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()
    print(json.dumps(execute(args.plan, args.model_runner, args.out, args.timeout_seconds)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
