#!/usr/bin/env python3
"""Create one private immutable workspace from a canonical marketplace contract."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import project_ledger


class WorkspaceError(ValueError):
    pass


CONTRACT_KEYS = {
    "version", "provider", "contract_id", "offer_id", "scope", "deadline",
    "terms_sha256", "contract_readback_sha256",
}
WORKFLOW_KEYS = {"skill_id", "version", "bundle_sha256"}
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
DIGEST = re.compile(r"[0-9a-f]{64}")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate(contract: Any, workflow: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(contract, dict) or set(contract) != CONTRACT_KEYS:
        raise WorkspaceError("canonical_contract_invalid")
    if not isinstance(workflow, dict) or set(workflow) != WORKFLOW_KEYS:
        raise WorkspaceError("workflow_invalid")
    try:
        date.fromisoformat(contract["deadline"])
    except (TypeError, ValueError) as exc:
        raise WorkspaceError("canonical_contract_invalid") from exc
    if (
        contract["version"] != 1
        or not KEY.fullmatch(str(contract["provider"]))
        or not KEY.fullmatch(str(contract["contract_id"]))
        or not KEY.fullmatch(str(contract["offer_id"]))
        or not isinstance(contract["scope"], str) or not contract["scope"].strip()
        or not DIGEST.fullmatch(str(contract["terms_sha256"]))
        or not DIGEST.fullmatch(str(contract["contract_readback_sha256"]))
        or not all(isinstance(workflow[key], str) and workflow[key].strip() for key in WORKFLOW_KEYS)
        or not DIGEST.fullmatch(workflow["bundle_sha256"])
    ):
        raise WorkspaceError("canonical_contract_invalid")
    return contract, workflow


def _exclusive_json(path: Path, value: Any) -> bool:
    body = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != body:
            raise WorkspaceError("immutable_workspace_collision")
        return False
    with os.fdopen(fd, "wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _secure_tree(root: Path) -> None:
    for path in [root, *root.rglob("*")]:
        if path.is_symlink():
            raise WorkspaceError("workspace_symlink_rejected")
        os.chmod(path, 0o700 if path.is_dir() else 0o600)


def create_workspace(base: str | Path, contract: Any, workflow: Any) -> dict[str, str]:
    contract, workflow = _validate(contract, workflow)
    base = Path(base).expanduser()
    if base.is_symlink():
        raise WorkspaceError("workspace_root_invalid")
    provider_root = base / contract["provider"]
    if provider_root.is_symlink():
        raise WorkspaceError("workspace_symlink_rejected")
    provider_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(base, 0o700)
    os.chmod(provider_root, 0o700)
    root = provider_root / contract["contract_id"]
    try:
        root.resolve(strict=False).relative_to(base.resolve())
    except ValueError as exc:
        raise WorkspaceError("workspace_path_escape") from exc
    if root.is_symlink():
        raise WorkspaceError("workspace_symlink_rejected")

    lock = provider_root / f".{contract['contract_id']}.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        contract_sha, workflow_sha = _sha(contract), _sha(workflow)
        revision_sha = _sha({"contract_sha256": contract_sha, "workflow_sha256": workflow_sha})
        if not (root / "state.json").exists():
            project_ledger.init_project(provider_root, contract["contract_id"], contract["provider"], {
                "contract_sha256": contract_sha, "workflow_sha256": workflow_sha,
                "deadline": contract["deadline"], "next_action": "execute_workflow",
            })
        state = json.loads((root / "state.json").read_text(encoding="utf-8"))
        if state.get("request_id") != contract["contract_id"] or state.get("adapter") != contract["provider"]:
            raise WorkspaceError("shared_client_workspace_rejected")
        _secure_tree(root)
        requirement = root / "requirements" / "revisions" / f"{revision_sha}.json"
        created = _exclusive_json(requirement, contract)
        source = root / "source" / "manifests" / f"{revision_sha}.json"
        _exclusive_json(source, {
            "version": 1, "contract_sha256": contract_sha, "workflow_sha256": workflow_sha,
            "terms_sha256": contract["terms_sha256"],
            "contract_readback_sha256": contract["contract_readback_sha256"],
        })
        _exclusive_json(root / "source" / "workflows" / f"{workflow_sha}.json", workflow)
        artifacts = root / "artifacts" / "manifests" / f"{revision_sha}.json"
        _exclusive_json(artifacts, {
            "version": 1, "revision_sha256": revision_sha, "artifacts": [],
        })
        _exclusive_json(root / "client-data-policy.json", {
            "version": 1, "classification": "owner_only", "public_paths": [],
            "logs": "hashes_only", "commit_client_content": False,
        })
        if created:
            project_ledger.append_fact(
                root, "contract_workspace_revision", {
                    "revision_sha256": revision_sha, "contract_sha256": contract_sha,
                    "workflow_sha256": workflow_sha,
                }, provenance=[{
                    "source": "upwork_contract_readback",
                    "sha256": contract["contract_readback_sha256"],
                }],
            )
        _secure_tree(root)
    return {
        "workspace": str(root), "revision_sha256": revision_sha,
        "requirement": str(requirement), "source_manifest": str(source),
        "artifact_manifest": str(artifacts),
    }


def load_workspace(base: str | Path, provider: str, contract_id: str) -> dict[str, str]:
    """Resume the latest durable revision for one existing marketplace owner."""
    if not KEY.fullmatch(provider) or not KEY.fullmatch(contract_id):
        raise WorkspaceError("workspace_identity_invalid")
    base = Path(base).expanduser()
    root = base / provider / contract_id
    try:
        root.resolve(strict=True).relative_to(base.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise WorkspaceError("workspace_not_found") from exc
    if root.is_symlink() or not root.is_dir():
        raise WorkspaceError("workspace_symlink_rejected")
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    if state.get("request_id") != contract_id or state.get("adapter") != provider:
        raise WorkspaceError("shared_client_workspace_rejected")
    revision_sha = None
    for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        fact = row.get("fact") if row.get("event") == "economic_fact" else None
        if isinstance(fact, dict) and fact.get("kind") == "contract_workspace_revision":
            candidate = (fact.get("payload") or {}).get("revision_sha256")
            if DIGEST.fullmatch(str(candidate or "")):
                revision_sha = candidate
    if revision_sha is None:
        raise WorkspaceError("workspace_revision_missing")
    paths = {
        "requirement": root / "requirements" / "revisions" / f"{revision_sha}.json",
        "source_manifest": root / "source" / "manifests" / f"{revision_sha}.json",
        "artifact_manifest": root / "artifacts" / "manifests" / f"{revision_sha}.json",
    }
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise WorkspaceError("workspace_revision_missing")
    return {"workspace": str(root), "revision_sha256": revision_sha,
            **{key: str(path) for key, path in paths.items()}}
