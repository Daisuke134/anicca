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


def seed_remote(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", str(remote), str(seed))
    git(seed, "config", "user.email", "cleanup@example.invalid")
    git(seed, "config", "user.name", "Cleanup Test")
    git(seed, "checkout", "-b", "main")
    commit_file(seed, "base.txt", "base")
    git(seed, "push", "-u", "origin", "main")
    return remote


def clone_repo(remote: Path, root: Path, name: str) -> Path:
    path = root / name
    git(root, "clone", str(remote), str(path))
    git(path, "config", "user.email", "cleanup@example.invalid")
    git(path, "config", "user.name", "Cleanup Test")
    return path


def test_sweep_removes_only_clean_remote_recoverable_unused_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = seed_remote(tmp_path)
    collection = tmp_path / "clones"
    collection.mkdir()

    clean = clone_repo(remote, collection, "anicca-clean")

    dirty = clone_repo(remote, collection, "anicca-dirty")
    (dirty / "base.txt").write_text("changed", encoding="utf-8")

    untracked = clone_repo(remote, collection, "anicca-untracked")
    (untracked / "scratch.txt").write_text("scratch", encoding="utf-8")

    unpushed = clone_repo(remote, collection, "anicca-unpushed")
    commit_file(unpushed, "local.txt", "not on remote")

    non_git = collection / "anicca-nongit"
    non_git.mkdir()
    (non_git / "file.txt").write_text("plain dir, no .git", encoding="utf-8")

    sibling = clone_repo(remote, collection, "other-sibling")

    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _path: "confirmed-closed")

    ledger = tmp_path / "ledger.jsonl"
    result = cleanup_control.sweep_git_clone_collection(
        collection_root=collection,
        child_name_prefix="anicca-",
        ledger_path=ledger,
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 1
    assert result["errors"] == 0
    assert not clean.exists()
    assert dirty.exists()
    assert untracked.exists()
    assert unpushed.exists()
    assert non_git.exists()
    assert sibling.exists()

    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    reasons = {event["path"]: event["reason"] for event in events}
    assert reasons[str(clean)] == "remote_recoverable_clone"
    assert reasons[str(dirty)] == "dirty_clone"
    assert reasons[str(untracked)] == "dirty_clone"
    assert reasons[str(unpushed)] == "head_not_on_remote"
    assert reasons[str(non_git)] == "not_a_git_repository"
    # the non-prefix sibling is never inspected or touched: no ledger event at all
    assert str(sibling) not in reasons
    # exactly one ledger event per matching child (clean, dirty, untracked, unpushed, non_git)
    assert len(events) == 5


def test_sweep_preserves_and_errors_when_lsof_state_is_open_or_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = seed_remote(tmp_path)
    collection = tmp_path / "clones"
    collection.mkdir()

    open_clone = clone_repo(remote, collection, "anicca-open")
    error_clone = clone_repo(remote, collection, "anicca-lsoferror")

    def fake_open_state(path: Path) -> str:
        if Path(path) == open_clone:
            return "open"
        if Path(path) == error_clone:
            return "error"
        return "confirmed-closed"

    monkeypatch.setattr(cleanup_control, "path_open_state", fake_open_state)

    ledger = tmp_path / "ledger.jsonl"
    result = cleanup_control.sweep_git_clone_collection(
        collection_root=collection,
        child_name_prefix="anicca-",
        ledger_path=ledger,
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 0
    assert result["preserved"] == 2
    assert result["errors"] == 1
    assert open_clone.exists()
    assert error_clone.exists()

    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    reasons = {event["path"]: event["reason"] for event in events}
    results = {event["path"]: event["result"] for event in events}
    assert reasons[str(open_clone)] == "open_clone"
    assert results[str(open_clone)] == "preserved"
    assert reasons[str(error_clone)] == "lsof_error"
    assert results[str(error_clone)] == "error"


def test_sweep_git_clone_collection_root_may_itself_be_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression guard: macOS /tmp (the real production path for this
    # manifest entry) is itself a symlink to /private/tmp. The collection
    # root being a symlink must not short-circuit the sweep into a no-op.
    remote = seed_remote(tmp_path)
    real_collection = tmp_path / "real-clones"
    real_collection.mkdir()
    clean = clone_repo(remote, real_collection, "anicca-clean")

    collection = tmp_path / "clones-symlink"
    collection.symlink_to(real_collection)

    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _path: "confirmed-closed")

    ledger = tmp_path / "ledger.jsonl"
    result = cleanup_control.sweep_git_clone_collection(
        collection_root=collection,
        child_name_prefix="anicca-",
        ledger_path=ledger,
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )

    assert result["removed"] == 1
    assert result["errors"] == 0
    assert not clean.exists()


def test_sweep_git_clone_collection_missing_root_is_a_noop(tmp_path: Path) -> None:
    result = cleanup_control.sweep_git_clone_collection(
        collection_root=tmp_path / "does-not-exist",
        child_name_prefix="anicca-",
        ledger_path=tmp_path / "ledger.jsonl",
        policy_version="cleanup-control-v1",
        manifest_sha256="test-manifest",
        now=1_000,
    )
    assert result == {"removed": 0, "preserved": 0, "errors": 0, "bytes_removed": 0}
    assert not (tmp_path / "ledger.jsonl").exists()


def test_sweep_dispatches_git_clone_collection_class_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote = seed_remote(tmp_path)
    collection = tmp_path / "clones"
    collection.mkdir()

    clean = clone_repo(remote, collection, "anicca-clean")
    dirty = clone_repo(remote, collection, "anicca-dirty")
    (dirty / "base.txt").write_text("changed", encoding="utf-8")

    monkeypatch.setattr(cleanup_control, "path_open_state", lambda _path: "confirmed-closed")

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "policy_version": "cleanup-control-v1",
                "artifacts": [
                    {
                        "id": "tmp-anicca-clones",
                        "path": str(collection),
                        "owner": "agent-temp-clones",
                        "class": "git_clone_collection",
                        "ttl_seconds": None,
                        "quota_bytes": 0,
                        "lease": None,
                        "finalizer": {
                            "kind": "remote_recoverable_remove",
                            "child_name_prefix": "anicca-",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = cleanup_control.sweep(
        manifest_path=manifest_path,
        quarantine_root=tmp_path / "quarantine",
        ledger_path=tmp_path / "ledger.jsonl",
        now=1_000,
        candidates=[collection],
    )

    assert result["status"] == "ok"
    assert result["errors"] == 0
    assert result["quarantined"] == 1
    assert not clean.exists()
    assert dirty.exists()


def test_manifest_requires_present_non_empty_child_name_prefix_for_git_clone_collection(
    tmp_path: Path,
) -> None:
    entry = {
        "id": "tmp-clones",
        "path": str(tmp_path / "clones"),
        "owner": "agent-temp-clones",
        "class": "git_clone_collection",
        "ttl_seconds": None,
        "quota_bytes": 0,
        "lease": None,
        "finalizer": {"kind": "remote_recoverable_remove", "child_name_prefix": "anicca-"},
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    _, _, entries = cleanup_control.load_manifest(manifest)
    assert entries[0]["class"] == "git_clone_collection"
    assert entries[0]["finalizer"] == {
        "kind": "remote_recoverable_remove",
        "child_name_prefix": "anicca-",
    }

    entry["finalizer"] = {"kind": "remote_recoverable_remove", "child_name_prefix": ""}
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    with pytest.raises(cleanup_control.ManifestError):
        cleanup_control.load_manifest(manifest)

    entry["finalizer"] = {"kind": "remote_recoverable_remove"}
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    with pytest.raises(cleanup_control.ManifestError):
        cleanup_control.load_manifest(manifest)

    entry["finalizer"] = {"kind": "off_volume_quarantine", "child_name_prefix": "anicca-"}
    manifest.write_text(
        json.dumps({"policy_version": "cleanup-control-v1", "artifacts": [entry]}),
        encoding="utf-8",
    )
    with pytest.raises(cleanup_control.ManifestError):
        cleanup_control.load_manifest(manifest)
