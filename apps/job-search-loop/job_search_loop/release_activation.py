from __future__ import annotations

import json
import hashlib
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any


COMMIT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LANES = ("daily", "inbox", "learning")


class ActivationError(RuntimeError):
    pass


def _validate_release(data_root: Path, commit: str) -> Path:
    if COMMIT_PATTERN.fullmatch(commit) is None:
        raise ActivationError("release commit is invalid")
    releases = (data_root / "releases").resolve()
    candidate = releases / commit
    if not candidate.is_dir() or candidate.resolve() != candidate:
        raise ActivationError("release directory is missing or not canonical")
    try:
        manifest = json.loads((candidate / "RELEASE.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ActivationError("release manifest is invalid") from error
    if manifest.get("commit") != commit:
        raise ActivationError("release manifest commit does not match")
    for path in (candidate, *candidate.rglob("*")):
        if stat.S_IMODE(path.stat().st_mode) & 0o222:
            raise ActivationError(f"release is writable: {path}")
    for lane in LANES:
        runner = candidate / f"apps/job-search-loop/scripts/run-{lane}.sh"
        if not runner.is_file() or not os.access(runner, os.X_OK):
            raise ActivationError(f"release runner is missing: {lane}")
    return candidate


def _link_commit(data_root: Path, name: str) -> str | None:
    link = data_root / name
    if not link.is_symlink():
        return None
    resolved = link.resolve()
    releases = (data_root / "releases").resolve()
    if resolved.parent != releases:
        raise ActivationError(f"{name} target escaped releases")
    return resolved.name


def _replace_link(data_root: Path, name: str, commit: str) -> None:
    temporary = data_root / f".{name}-{uuid.uuid4().hex}"
    try:
        temporary.symlink_to(Path("releases") / commit)
        os.replace(temporary, data_root / name)
    finally:
        temporary.unlink(missing_ok=True)


def _write_active_receipt(data_root: Path, candidate: Path, commit: str) -> None:
    manifest = candidate / "RELEASE.json"
    config = candidate / "runtime/agent-runner/config.json"
    if not config.is_file():
        raise ActivationError("release route config is missing")
    value = {
        "version": 1,
        "active_commit": commit,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "route_config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
    }
    target = data_root / "active-release.json"
    temporary = data_root / f".active-release-{uuid.uuid4().hex}.json"
    try:
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def activate(*, data_root: Path, commit: str) -> dict[str, Any]:
    data_root = Path(data_root).resolve()
    data_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    candidate = _validate_release(data_root, commit)
    current_commit = _link_commit(data_root, "current")
    if current_commit == commit:
        _write_active_receipt(data_root, candidate, commit)
        return {"status": "already_active", "active_commit": commit}
    if current_commit is not None:
        _validate_release(data_root, current_commit)
        _replace_link(data_root, "previous", current_commit)
    _replace_link(data_root, "current", commit)
    _write_active_receipt(data_root, candidate, commit)
    return {
        "status": "activated",
        "active_commit": commit,
        "previous_commit": current_commit,
        "release_root": str(candidate),
    }


def rollback(*, data_root: Path) -> dict[str, Any]:
    data_root = Path(data_root).resolve()
    current_commit = _link_commit(data_root, "current")
    previous_commit = _link_commit(data_root, "previous")
    if current_commit is None or previous_commit is None:
        raise ActivationError("rollback requires current and previous releases")
    _validate_release(data_root, current_commit)
    target = _validate_release(data_root, previous_commit)
    _replace_link(data_root, "current", previous_commit)
    _replace_link(data_root, "previous", current_commit)
    _write_active_receipt(data_root, target, previous_commit)
    return {
        "status": "rolled_back",
        "active_commit": previous_commit,
        "rollback_from_commit": current_commit,
        "release_root": str(target),
    }
