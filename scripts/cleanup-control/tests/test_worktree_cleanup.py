from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from test_cleanup_control import cleanup_control


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def commit_file(repo: Path, name: str, content: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", f"add {name}")
    return git(repo, "rev-parse", "HEAD")


def add_worktree(repo: Path, root: Path, branch: str) -> Path:
    path = root / branch.replace("/", "-")
    git(repo, "worktree", "add", "-b", branch, str(path), "main")
    return path


def test_worktree_policy_requires_every_safety_invariant() -> None:
    base = {
        "is_current": False,
        "is_locked": False,
        "is_clean": True,
        "remote_contains_head": True,
        "open_state": "confirmed-closed",
    }
    assert cleanup_control.worktree_reclaim_decision(**base) == "eligible"

    cases = {
        "is_current": "current_worktree",
        "is_locked": "locked_worktree",
        "is_clean": "dirty_worktree",
        "remote_contains_head": "head_not_on_remote",
        "open_state": "open_worktree",
    }
    for field, expected in cases.items():
        values = dict(base)
        values[field] = (
            True
            if field in {"is_current", "is_locked"}
            else False
            if field in {"is_clean", "remote_contains_head"}
            else "open"
        )
        assert cleanup_control.worktree_reclaim_decision(**values) == expected

    values = dict(base)
    values["open_state"] = "error"
    assert cleanup_control.worktree_reclaim_decision(**values) == "lsof_error"


def test_missing_registered_worktree_is_preserved_instead_of_crashing(tmp_path: Path) -> None:
    reason, head, refs = cleanup_control._inspect_worktree(
        tmp_path, tmp_path / "missing-worktree", False
    )
    assert (reason, head, refs) == ("path_missing", "", [])


def test_sweep_removes_only_clean_remote_recoverable_unused_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = tmp_path / "remote.git"
    primary = tmp_path / "repo"
    collection = primary / ".worktrees"
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "clone", str(remote), str(primary))
    git(primary, "config", "user.email", "cleanup@example.invalid")
    git(primary, "config", "user.name", "Cleanup Test")
    git(primary, "checkout", "-b", "main")
    commit_file(primary, "base.txt", "base")
    git(primary, "push", "-u", "origin", "main")

    safe = add_worktree(primary, collection, "safe")
    commit_file(safe, "safe.txt", "remote")
    git(safe, "push", "-u", "origin", "safe")

    dirty = add_worktree(primary, collection, "dirty")
    (dirty / "untracked.txt").write_text("keep", encoding="utf-8")

    unpushed = add_worktree(primary, collection, "unpushed")
    commit_file(unpushed, "local.txt", "not on remote")

    locked = add_worktree(primary, collection, "locked")
    commit_file(locked, "locked.txt", "remote")
    git(locked, "push", "-u", "origin", "locked")
    git(primary, "worktree", "lock", str(locked))

    open_path = add_worktree(primary, collection, "open")
    commit_file(open_path, "open.txt", "remote")
    git(open_path, "push", "-u", "origin", "open")

    monkeypatch.setattr(
        cleanup_control,
        "path_open_state",
        lambda path: "open" if Path(path) == open_path else "confirmed-closed",
    )
    ledger = tmp_path / "ledger.jsonl"
    result = cleanup_control.sweep_worktree_collection(
        collection_root=collection,
        ledger_path=ledger,
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 1
    assert result["errors"] == 0
    assert not safe.exists()
    assert dirty.exists()
    assert unpushed.exists()
    assert locked.exists()
    assert open_path.exists()

    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    reasons = {event["path"]: event["reason"] for event in events}
    assert reasons[str(safe)] == "remote_recoverable_worktree"
    assert reasons[str(dirty)] == "dirty_worktree"
    assert reasons[str(unpushed)] == "head_not_on_remote"
    assert reasons[str(locked)] == "locked_worktree"
    assert reasons[str(open_path)] == "open_worktree"


def test_sweep_supports_collection_outside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = tmp_path / "remote.git"
    primary = tmp_path / "repo"
    collection = tmp_path / "external-worktrees"
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "clone", str(remote), str(primary))
    git(primary, "config", "user.email", "cleanup@example.invalid")
    git(primary, "config", "user.name", "Cleanup Test")
    git(primary, "checkout", "-b", "main")
    commit_file(primary, "base.txt", "base")
    git(primary, "push", "-u", "origin", "main")

    safe = add_worktree(primary, collection, "safe-external")
    commit_file(safe, "safe.txt", "remote")
    git(safe, "push", "-u", "origin", "safe-external")
    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _path: "confirmed-closed")

    result = cleanup_control.sweep_worktree_collection(
        collection_root=collection,
        repository_root=primary,
        ledger_path=tmp_path / "ledger.jsonl",
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 1
    assert result["errors"] == 0
    assert not safe.exists()


def test_sweep_accepts_clean_worktree_recoverable_from_non_origin_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    origin = tmp_path / "origin.git"
    canonical = tmp_path / "canonical.git"
    primary = tmp_path / "repo"
    collection = primary / ".worktrees"
    git(tmp_path, "init", "--bare", str(origin))
    git(tmp_path, "init", "--bare", str(canonical))
    git(tmp_path, "clone", str(origin), str(primary))
    git(primary, "config", "user.email", "cleanup@example.invalid")
    git(primary, "config", "user.name", "Cleanup Test")
    git(primary, "checkout", "-b", "main")
    commit_file(primary, "base.txt", "base")
    git(primary, "push", "-u", "origin", "main")
    git(primary, "remote", "add", "canonical", str(canonical))
    git(primary, "push", "canonical", "main")

    safe = add_worktree(primary, collection, "safe-canonical")
    commit_file(safe, "safe.txt", "remote")
    git(safe, "push", "-u", "canonical", "safe-canonical")
    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _path: "confirmed-closed")

    result = cleanup_control.sweep_worktree_collection(
        collection_root=collection,
        ledger_path=tmp_path / "ledger.jsonl",
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 1
    assert result["errors"] == 0
    assert not safe.exists()


def test_manifest_accepts_only_remote_recoverable_worktree_finalizer(tmp_path: Path) -> None:
    entry = {
        "id": "worktrees",
        "path": str(tmp_path / ".worktrees"),
        "owner": "git",
        "class": "git_worktree_collection",
        "ttl_seconds": None,
        "quota_bytes": 0,
        "lease": None,
        "finalizer": {"kind": "remote_recoverable_remove"},
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )

    _, _, entries = cleanup_control.load_manifest(manifest)
    assert entries[0]["class"] == "git_worktree_collection"

    repository = tmp_path / "repo"
    entry["finalizer"] = {
        "kind": "remote_recoverable_remove",
        "repository_path": str(repository),
    }
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    _, _, entries = cleanup_control.load_manifest(manifest)
    assert entries[0]["finalizer"]["repository_path"] == str(repository)

    entry["finalizer"] = {"kind": "off_volume_quarantine"}
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    with pytest.raises(cleanup_control.ManifestError):
        cleanup_control.load_manifest(manifest)
