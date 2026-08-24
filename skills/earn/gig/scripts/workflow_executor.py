#!/usr/bin/env python3
"""Execute one contract-frozen Skill locally and promote hash-bound artifacts.

This module has no marketplace capability.  The only process it invokes is the
existing generic agent runner, with a prompt that limits effects to a private
staging directory.  Upwork submission and delivery remain separate effect
fences.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from datetime import datetime, time as daytime, timezone
from pathlib import Path
from typing import Any

import project_ledger


class WorkflowExecutionError(ValueError):
    pass


DIGEST = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}")
GENERAL_AGENT_ID = "general-agent"
GENERAL_AGENT_VERSION = "1.0.0"
GENERAL_AGENT_CONTRACT = (
    "Use the general model and available local tools to produce the immutable contract scope. "
    "Choose the implementation method from the evidence; named Skills are optional cached playbooks."
)
SECRET_NAME = re.compile(r"(?:^|[._-])(secret|token|password|passwd|credential|private[-_]?key)(?:[._-]|$)", re.I)
SECRET_BODY = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\b(?:sk-(?:live-)?[A-Za-z0-9_-]{20,}|gh[opusr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})\b|"
    rb"(?i:\b(?:api[_-]?key|access[_-]?token|password|passwd)\s*[:=]\s*['\"](?!example|placeholder|changeme|\$\{)[^'\"\r\n]{12,}['\"])",
)


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def general_agent_workflow() -> dict[str, str]:
    return {
        "skill_id": GENERAL_AGENT_ID, "version": GENERAL_AGENT_VERSION,
        "bundle_sha256": hashlib.sha256(GENERAL_AGENT_CONTRACT.encode()).hexdigest(),
    }


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowExecutionError(reason) from exc
    if not isinstance(value, dict):
        raise WorkflowExecutionError(reason)
    return value


def _regular_private(path: Path, reason: str) -> None:
    try:
        entry = path.lstat()
    except OSError as exc:
        raise WorkflowExecutionError(reason) from exc
    if not stat.S_ISREG(entry.st_mode) or stat.S_IMODE(entry.st_mode) != 0o600:
        raise WorkflowExecutionError(reason)


def _secure_tree(root: Path) -> None:
    try:
        root.resolve(strict=True)
    except OSError as exc:
        raise WorkflowExecutionError("workspace_invalid") from exc
    for path in (root, *root.rglob("*")):
        try:
            entry = path.lstat()
        except OSError as exc:
            raise WorkflowExecutionError("workspace_invalid") from exc
        if stat.S_ISLNK(entry.st_mode):
            raise WorkflowExecutionError("workspace_symlink_rejected")


def _skill_bundle(skill_dir: Path) -> tuple[str, str, list[str]]:
    """Return bundle hash, SKILL.md hash and included relative paths.

    Bundle v1 hashes canonical rows of relative path + content SHA.  Cache and
    bytecode files are excluded.  A one-file Skill may also match its SKILL.md
    SHA because the pre-existing capability inventory used that source hash.
    """
    rows = []
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir)
        if any(part in {"__pycache__", ".pytest_cache"} for part in rel.parts) or path.suffix == ".pyc":
            continue
        entry = path.lstat()
        if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
            if stat.S_ISDIR(entry.st_mode):
                continue
            raise WorkflowExecutionError("skill_bundle_invalid")
        rows.append({"path": rel.as_posix(), "sha256": _sha_file(path)})
    skill_file = skill_dir / "SKILL.md"
    if not rows or not skill_file.is_file() or skill_file.is_symlink():
        raise WorkflowExecutionError("skill_uninstalled")
    return _sha_value({"version": 1, "files": rows}), _sha_file(skill_file), [row["path"] for row in rows]


def _skill_version(skill_file: Path) -> str:
    head = skill_file.read_text(encoding="utf-8")[:4096]
    match = re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)", head)
    if match is None:
        raise WorkflowExecutionError("skill_version_missing")
    return match.group(1)


def _validate_inputs(root: Path, revision: str, skills_root: Path, timeout_seconds: int,
                     now: datetime) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path | None, str, str]:
    if not DIGEST.fullmatch(revision):
        raise WorkflowExecutionError("revision_invalid")
    _secure_tree(root)
    requirement_path = root / "requirements" / "revisions" / f"{revision}.json"
    source_path = root / "source" / "manifests" / f"{revision}.json"
    _regular_private(requirement_path, "contract_revision_missing")
    _regular_private(source_path, "source_manifest_missing")
    contract, source = _read_json(requirement_path, "contract_revision_invalid"), _read_json(source_path, "source_manifest_invalid")
    contract_sha = _sha_value(contract)
    workflow_sha = source.get("workflow_sha256")
    if source.get("contract_sha256") != contract_sha or not isinstance(workflow_sha, str) or not DIGEST.fullmatch(workflow_sha):
        raise WorkflowExecutionError("contract_scope_changed")
    expected_revision = _sha_value({"contract_sha256": contract_sha, "workflow_sha256": workflow_sha})
    if expected_revision != revision:
        raise WorkflowExecutionError("contract_scope_changed")
    if source.get("terms_sha256") != contract.get("terms_sha256") or source.get("contract_readback_sha256") != contract.get("contract_readback_sha256"):
        raise WorkflowExecutionError("contract_source_changed")
    workflow_path = root / "source" / "workflows" / f"{workflow_sha}.json"
    _regular_private(workflow_path, "workflow_missing")
    workflow = _read_json(workflow_path, "workflow_invalid")
    if _sha_value(workflow) != workflow_sha or set(workflow) != {"skill_id", "version", "bundle_sha256"}:
        raise WorkflowExecutionError("workflow_changed")
    skill_id = workflow.get("skill_id")
    if not isinstance(skill_id, str) or not SAFE_ID.fullmatch(skill_id) or ".." in Path(skill_id).parts or Path(skill_id).is_absolute():
        raise WorkflowExecutionError("skill_id_invalid")
    skill_dir = None
    if skill_id == GENERAL_AGENT_ID:
        if workflow != general_agent_workflow():
            raise WorkflowExecutionError("general_agent_workflow_changed")
    else:
        skill_dir = skills_root / skill_id
        try:
            skill_dir.resolve(strict=True).relative_to(skills_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkflowExecutionError("skill_uninstalled") from exc
        bundle_sha, source_sha, bundle_paths = _skill_bundle(skill_dir)
        frozen = workflow.get("bundle_sha256")
        compatible = frozen == bundle_sha or (bundle_paths == ["SKILL.md"] and frozen == source_sha)
        if not compatible:
            raise WorkflowExecutionError("skill_bundle_changed")
        if _skill_version(skill_dir / "SKILL.md") != workflow.get("version"):
            raise WorkflowExecutionError("skill_version_changed")
    if now.tzinfo is None or now.utcoffset() is None or timeout_seconds < 1:
        raise WorkflowExecutionError("deadline_budget_invalid")
    try:
        deadline = datetime.combine(datetime.fromisoformat(str(contract["deadline"])).date(), daytime.max, tzinfo=timezone.utc)
    except (KeyError, ValueError, TypeError) as exc:
        raise WorkflowExecutionError("deadline_invalid") from exc
    if (deadline - now.astimezone(timezone.utc)).total_seconds() < timeout_seconds:
        raise WorkflowExecutionError("deadline_budget_expired")
    return contract, workflow, source, skill_dir, contract_sha, workflow_sha


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(_canonical(value)); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def _harden_private_tree(root: Path) -> None:
    for path in (root, *root.rglob("*")):
        entry = path.lstat()
        if stat.S_ISLNK(entry.st_mode):
            raise WorkflowExecutionError("generated_symlink_rejected")
        os.chmod(path, 0o700 if stat.S_ISDIR(entry.st_mode) else 0o600)


def _record_completed_fact(root: Path, receipt_path: Path, receipt: dict[str, Any]) -> None:
    project_ledger.append_fact(root, "workflow_execution_completed", {
        "execution_id": receipt["execution_id"], "revision_sha256": receipt["revision_sha256"],
        "workflow_sha256": receipt["workflow_sha256"],
        "artifact_sha256": [row["sha256"] for row in receipt["artifacts"]],
        "model_cost_usd": receipt["model_cost_usd"], "tool_cost_usd": receipt["tool_cost_usd"],
    }, provenance=[{"source": "contract_workflow_receipt", "sha256": _sha_file(receipt_path)}])


def _runner_cost(evidence: Path, summary: dict[str, Any]) -> tuple[float, float]:
    attempts = Path(str(summary.get("attempts_path") or evidence / "attempts.jsonl"))
    try:
        attempts.resolve().relative_to(evidence.resolve())
    except ValueError:
        raise WorkflowExecutionError("runner_evidence_escape")
    model = tool = 0.0
    if attempts.is_file() and not attempts.is_symlink():
        for line in attempts.read_text(encoding="utf-8").splitlines():
            try: row = json.loads(line)
            except json.JSONDecodeError: continue
            usage = row.get("usage") if isinstance(row, dict) else None
            if isinstance(usage, dict):
                model += float(usage.get("provider_cost_usd") or 0)
                tool += float(usage.get("tool_cost_usd") or 0)
    return round(model, 8), round(tool, 8)


def execute_workflow(*, workspace: str | Path, revision_sha256: str, skills_root: str | Path,
                     agent_runner: str | Path, timeout_seconds: int = 3600,
                     now: datetime | None = None) -> dict[str, Any]:
    root, skills_root = Path(workspace).expanduser(), Path(skills_root).expanduser()
    now = now or datetime.now(timezone.utc)
    contract, workflow, source, skill_dir, contract_sha, workflow_sha = _validate_inputs(
        root, revision_sha256, skills_root, timeout_seconds, now,
    )
    runner_input = Path(agent_runner).expanduser()
    try:
        runner_entry = runner_input.lstat()
    except OSError as exc:
        raise WorkflowExecutionError("runner_invalid") from exc
    if stat.S_ISLNK(runner_entry.st_mode) or not stat.S_ISREG(runner_entry.st_mode):
        raise WorkflowExecutionError("runner_invalid")
    runner = runner_input.resolve(strict=True)
    execution_id = _sha_value({"version": 1, "revision_sha256": revision_sha256,
                               "workflow_sha256": workflow_sha, "runner_sha256": _sha_file(runner)})
    execution_root = root / "work" / "executions" / execution_id
    execution_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(execution_root, 0o700)
    lock_fd = os.open(execution_root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt_path = root / "artifacts" / "execution-receipts" / f"{execution_id}.json"
        if receipt_path.is_file() and not receipt_path.is_symlink():
            receipt = _read_json(receipt_path, "completed_receipt_invalid")
            artifacts = receipt.get("artifacts")
            if (receipt.get("execution_id") != execution_id or receipt.get("state") != "completed"
                    or not isinstance(artifacts, list) or not artifacts):
                raise WorkflowExecutionError("completed_receipt_invalid")
            for artifact in artifacts:
                if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                    raise WorkflowExecutionError("completed_receipt_invalid")
                path = root / artifact["path"]
                try:
                    path.resolve(strict=True).relative_to(root.resolve())
                except (OSError, ValueError) as exc:
                    raise WorkflowExecutionError("completed_receipt_invalid") from exc
                if (path.is_symlink() or not path.is_file()
                        or _sha_file(path) != artifact.get("sha256")
                        or path.stat().st_size != artifact.get("bytes")):
                    raise WorkflowExecutionError("completed_artifact_changed")
            _record_completed_fact(root, receipt_path, receipt)
            _harden_private_tree(root)
            return receipt

        staging, evidence = execution_root / "staging", execution_root / "runner-evidence"
        staging.mkdir(parents=True, exist_ok=True, mode=0o700)
        evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        checkpoint = execution_root / "checkpoint.json"
        prior_checkpoint = (_read_json(checkpoint, "checkpoint_invalid")
                            if checkpoint.is_file() and not checkpoint.is_symlink() else {})
        resumable_runner = (
            prior_checkpoint.get("execution_id") == execution_id
            and prior_checkpoint.get("state") in {"runner_completed", "artifacts_validated"}
        )
        started_at = str(prior_checkpoint.get("started_at") or now.astimezone(timezone.utc).isoformat())
        started_ns = time.monotonic_ns()
        if not resumable_runner:
            _atomic_json(checkpoint, {"version": 1, "state": "runner_pending", "execution_id": execution_id,
                                      "revision_sha256": revision_sha256, "workflow_sha256": workflow_sha,
                                      "started_at": started_at})
        schema = execution_root / "result.schema.json"
        _atomic_json(schema, {"type": "object", "additionalProperties": False,
            "required": ["status", "reason", "artifacts"], "properties": {
                "status": {"enum": ["ok", "blocked"]}, "reason": {"type": "string", "minLength": 1},
                "artifacts": {"type": "array", "items": {"type": "string", "minLength": 1}}}})
        prompt = execution_root / "prompt.txt"
        execution_contract = (GENERAL_AGENT_CONTRACT if skill_dir is None else
                              "Execute exactly the frozen Skill at " + str(skill_dir / "SKILL.md") + ". Read it fully.")
        prompt.write_text(
            execution_contract + " "
            "The immutable contract scope is: " + str(contract["scope"]) + "\n"
            "Work only inside this WORKDIR. Create buyer-facing artifacts under artifacts/. "
            "Do not browse, use a marketplace, send messages, submit/deliver work, make payments, or cause any network/external effect. "
            "Do not write credentials or secrets. Return only the supplied schema; artifacts must be relative paths inside WORKDIR. "
            "Return blocked with an exact reason if required client inputs are absent.", encoding="utf-8")
        os.chmod(prompt, 0o600)
        command = [sys.executable, str(runner), "--task-class", "tool-agent", "--prompt-file", str(prompt),
                   "--schema", str(schema), "--evidence-dir", str(evidence), "--task-label", "contract-workflow",
                   "--loop", "gig", "--workdir", str(staging), "--timeout-seconds", str(timeout_seconds)]
        if not resumable_runner:
            try:
                completed = subprocess.run(command, capture_output=True, text=True,
                                           timeout=timeout_seconds + 30, check=False)
            except subprocess.TimeoutExpired as exc:
                raise WorkflowExecutionError("runner_timeout") from exc
            _harden_private_tree(root)
            if completed.returncode != 0:
                raise WorkflowExecutionError("runner_failed")
        summary_path = evidence / "summary.json"
        summary = _read_json(summary_path, "runner_summary_missing")
        if summary.get("status") != "success":
            raise WorkflowExecutionError("runner_failed")
        result_path = Path(str(summary.get("result_path") or ""))
        try: result_path.resolve(strict=True).relative_to(evidence.resolve())
        except (OSError, ValueError) as exc: raise WorkflowExecutionError("runner_result_escape") from exc
        result = _read_json(result_path, "runner_result_invalid")
        _atomic_json(checkpoint, {"version": 1, "state": "runner_completed", "execution_id": execution_id,
                                  "revision_sha256": revision_sha256, "workflow_sha256": workflow_sha,
                                  "started_at": started_at, "result_sha256": _sha_file(result_path)})
        if result.get("status") != "ok":
            raise WorkflowExecutionError("workflow_blocked:" + str(result.get("reason") or "unknown"))
        rows = result.get("artifacts")
        if not isinstance(rows, list) or not rows:
            raise WorkflowExecutionError("artifact_missing")
        candidates = []
        seen = set()
        for raw in rows:
            if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or ".." in Path(raw).parts or raw in seen:
                raise WorkflowExecutionError("artifact_path_invalid")
            seen.add(raw)
            source_path = staging / raw
            if not source_path.exists():
                raise WorkflowExecutionError("artifact_missing")
            try: source_path.resolve(strict=True).relative_to(staging.resolve())
            except (OSError, ValueError) as exc: raise WorkflowExecutionError("artifact_path_invalid") from exc
            if source_path.is_symlink() or not source_path.is_file() or source_path.stat().st_size < 1:
                raise WorkflowExecutionError("artifact_missing")
            body = source_path.read_bytes()
            if SECRET_NAME.search(source_path.name) or SECRET_BODY.search(body):
                raise WorkflowExecutionError("artifact_secret_leak")
            digest = hashlib.sha256(body).hexdigest()
            candidates.append((raw, source_path.name, body, digest))
        _atomic_json(checkpoint, {"version": 1, "state": "artifacts_validated", "execution_id": execution_id,
                                  "revision_sha256": revision_sha256, "workflow_sha256": workflow_sha,
                                  "started_at": started_at,
                                  "artifact_sha256": [item[3] for item in candidates]})
        promoted = []
        destination = root / "artifacts" / "revisions" / execution_id
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        for raw, basename, body, digest in candidates:
            target = destination / f"{digest}-{basename}"
            try:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                if target.is_symlink() or not target.is_file() or target.read_bytes() != body:
                    raise WorkflowExecutionError("artifact_promotion_collision")
            else:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(body); handle.flush(); os.fsync(handle.fileno())
            promoted.append({"source_path": raw, "path": target.relative_to(root).as_posix(),
                             "sha256": digest, "bytes": len(body)})
        model_cost, tool_cost = _runner_cost(evidence, summary)
        receipt = {"version": 1, "state": "completed", "execution_id": execution_id,
                   "revision_sha256": revision_sha256, "contract_sha256": contract_sha,
                   "workflow_sha256": workflow_sha, "skill_id": workflow["skill_id"],
                   "skill_version": workflow["version"], "artifacts": promoted,
                   "model_cost_usd": model_cost, "tool_cost_usd": tool_cost,
                   "elapsed_ms": round((time.monotonic_ns() - started_ns) / 1_000_000),
                   "completed_at": datetime.now(timezone.utc).isoformat(), "marketplace_effects": 0}
        _atomic_json(receipt_path, receipt)
        _record_completed_fact(root, receipt_path, receipt)
        _atomic_json(checkpoint, {"version": 1, "state": "completed", "execution_id": execution_id,
                                  "receipt_sha256": _sha_file(receipt_path)})
        _harden_private_tree(root)
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--revision-sha256", required=True)
    parser.add_argument("--skills-root", required=True, type=Path)
    parser.add_argument("--agent-runner", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    try:
        receipt = execute_workflow(workspace=args.workspace, revision_sha256=args.revision_sha256,
            skills_root=args.skills_root, agent_runner=args.agent_runner, timeout_seconds=args.timeout_seconds)
    except WorkflowExecutionError as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
