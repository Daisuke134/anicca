#!/usr/bin/env python3
"""Deterministic, fail-closed artifact cleanup with reversible quarantine.

Only exact paths declared as ``ephemeral`` in a valid versioned manifest can
leave their source location.  They are copied and verified on a different
filesystem before the source is removed.  Every decision is append-only JSONL.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable


REQUIRED_FIELDS = {
    "id",
    "path",
    "owner",
    "class",
    "ttl_seconds",
    "quota_bytes",
    "lease",
    "finalizer",
}
PROTECTED_CLASSES = {
    "deliverable",
    "checkpoint",
    "identity",
    "state",
    "secret",
    "evidence",
    "source",
    "dependency",
    "runtime",
}
WORKTREE_COLLECTION_CLASS = "git_worktree_collection"
REGENERABLE_OUTPUT_CLASS = "regenerable_output"
GIT_CLONE_COLLECTION_CLASS = "git_clone_collection"
ALLOWED_CLASSES = PROTECTED_CLASSES | {
    "ephemeral",
    WORKTREE_COLLECTION_CLASS,
    REGENERABLE_OUTPUT_CLASS,
    GIT_CLONE_COLLECTION_CLASS,
}
TX_RE = re.compile(r"^[0-9a-f]{32}$")
DISCOVERABLE_OUTPUT_PROOFS = {
    "node_modules": (
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
    ),
    ".venv": ("uv.lock", "poetry.lock", "requirements.txt", "pyproject.toml"),
    "target": ("Cargo.lock",),
    ".next": (
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
    ),
}
PROTECTED_DISCOVERY_PARTS = {".claude", ".codex", ".git", "memory", "state"}
BROWSER_CACHE_TOKENS = {"ms-playwright", "camoufox", "chromium", "chrome"}


class ManifestError(ValueError):
    pass


def _utc_timestamp(now: int | float | None = None) -> str:
    value = time.time() if now is None else now
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))


def _normalized_path(value: str) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute():
        raise ManifestError(f"path must be absolute: {value!r}")
    normalized = Path(os.path.normpath(str(expanded)))
    home = Path.home()
    if normalized in {Path("/"), home, home.parent}:
        raise ManifestError(f"path is too broad: {normalized}")
    return normalized


def _validate_entry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ManifestError("artifact entry must be an object")
    missing = REQUIRED_FIELDS - raw.keys()
    if missing:
        raise ManifestError(f"artifact entry missing fields: {sorted(missing)}")
    if not isinstance(raw["id"], str) or not raw["id"].strip():
        raise ManifestError("artifact id must be a non-empty string")
    if not isinstance(raw["owner"], str) or not raw["owner"].strip():
        raise ManifestError(f"artifact {raw['id']} owner must be non-empty")
    artifact_class = raw["class"]
    if artifact_class not in ALLOWED_CLASSES:
        raise ManifestError(f"artifact {raw['id']} has unknown class {artifact_class!r}")
    path = _normalized_path(raw["path"])
    ttl = raw["ttl_seconds"]
    if artifact_class == "ephemeral":
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 0:
            raise ManifestError(f"artifact {raw['id']} requires non-negative ttl_seconds")
    elif ttl is not None:
        raise ManifestError(f"protected artifact {raw['id']} must use null ttl_seconds")
    quota = raw["quota_bytes"]
    if not isinstance(quota, int) or isinstance(quota, bool) or quota < 0:
        raise ManifestError(f"artifact {raw['id']} quota_bytes must be non-negative")
    lease = raw["lease"]
    if lease is not None:
        if not isinstance(lease, dict) or set(lease) != {"path", "max_age_seconds"}:
            raise ManifestError(f"artifact {raw['id']} lease schema is invalid")
        lease_path = _normalized_path(lease["path"])
        max_age = lease["max_age_seconds"]
        if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age <= 0:
            raise ManifestError(f"artifact {raw['id']} lease max_age_seconds is invalid")
        lease = {"path": str(lease_path), "max_age_seconds": max_age}
    finalizer = raw["finalizer"]
    if not isinstance(finalizer, dict) or "kind" not in finalizer:
        raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
    if artifact_class == "ephemeral":
        if set(finalizer) != {"kind"}:
            raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
        expected_finalizer = "off_volume_quarantine"
    elif artifact_class == WORKTREE_COLLECTION_CLASS:
        if set(finalizer) not in ({"kind"}, {"kind", "repository_path"}):
            raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
        expected_finalizer = "remote_recoverable_remove"
    elif artifact_class == REGENERABLE_OUTPUT_CLASS:
        if set(finalizer) != {"kind", "proof_path"}:
            raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
        expected_finalizer = "verified_regenerable_remove"
    elif artifact_class == GIT_CLONE_COLLECTION_CLASS:
        if set(finalizer) != {"kind", "child_name_prefix"}:
            raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
        expected_finalizer = "remote_recoverable_remove"
    else:
        if set(finalizer) != {"kind"}:
            raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
        expected_finalizer = "preserve"
    if finalizer["kind"] != expected_finalizer:
        raise ManifestError(
            f"artifact {raw['id']} class {artifact_class} requires {expected_finalizer} finalizer"
        )
    normalized_finalizer = {"kind": expected_finalizer}
    if artifact_class == WORKTREE_COLLECTION_CLASS and "repository_path" in finalizer:
        normalized_finalizer["repository_path"] = str(
            _normalized_path(finalizer["repository_path"])
        )
    if artifact_class == REGENERABLE_OUTPUT_CLASS:
        normalized_finalizer["proof_path"] = str(_normalized_path(finalizer["proof_path"]))
    if artifact_class == GIT_CLONE_COLLECTION_CLASS:
        prefix = finalizer["child_name_prefix"]
        if not isinstance(prefix, str) or not prefix.strip():
            raise ManifestError(f"artifact {raw['id']} child_name_prefix must be non-empty")
        normalized_finalizer["child_name_prefix"] = prefix
    return {
        "id": raw["id"],
        "path": str(path),
        "owner": raw["owner"],
        "class": artifact_class,
        "ttl_seconds": ttl,
        "quota_bytes": quota,
        "lease": lease,
        "finalizer": normalized_finalizer,
    }


def load_manifest(path: Path) -> tuple[str, str, list[dict[str, Any]]]:
    try:
        raw_bytes = path.read_bytes()
        data = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest must be an object")
    version = data.get("policy_version")
    artifacts = data.get("artifacts")
    if not isinstance(version, str) or not version.strip():
        raise ManifestError("policy_version must be a non-empty string")
    if not isinstance(artifacts, list):
        raise ManifestError("artifacts must be an array")
    entries = [_validate_entry(raw) for raw in artifacts]
    ids = [item["id"] for item in entries]
    paths = [item["path"] for item in entries]
    if len(ids) != len(set(ids)):
        raise ManifestError("artifact ids must be unique")
    if len(paths) != len(set(paths)):
        raise ManifestError("artifact paths must be unique")
    return version, hashlib.sha256(raw_bytes).hexdigest(), entries


def append_ledger(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    fd = os.open(path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def device_id(path: Path) -> int:
    return path.lstat().st_dev


def _iter_nodes(path: Path) -> Iterable[Path]:
    yield path
    if path.is_dir() and not path.is_symlink():
        yield from sorted(path.rglob("*"), key=lambda item: str(item.relative_to(path)))


def artifact_size(path: Path) -> int:
    total = 0
    for node in _iter_nodes(path):
        info = node.lstat()
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
        elif stat.S_ISLNK(info.st_mode):
            total += len(os.readlink(node).encode("utf-8"))
    return total


def newest_mtime(path: Path) -> float:
    return max(node.lstat().st_mtime for node in _iter_nodes(path))


def artifact_digest(path: Path) -> str:
    digest = hashlib.sha256()
    root = path
    for node in _iter_nodes(path):
        rel = "." if node == root else str(node.relative_to(root))
        info = node.lstat()
        if stat.S_ISLNK(info.st_mode):
            kind = b"L"
            payload = os.readlink(node).encode("utf-8")
        elif stat.S_ISDIR(info.st_mode):
            kind = b"D"
            payload = b""
        elif stat.S_ISREG(info.st_mode):
            kind = b"F"
            payload = node.read_bytes()
        else:
            raise OSError(f"unsupported artifact node: {node}")
        digest.update(kind)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def _copy_artifact(source: Path, destination: Path) -> None:
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    elif source.is_file():
        shutil.copy2(source, destination, follow_symlinks=False)
    else:
        raise OSError(f"unsupported artifact type: {source}")


def _remove_source(source: Path) -> None:
    if source.is_dir() and not source.is_symlink():
        shutil.rmtree(source)
    else:
        source.unlink()


def _event_base(
    *,
    event: str,
    reason: str,
    path: Path,
    entry: dict[str, Any] | None,
    policy_version: str,
    manifest_sha256: str,
    now: int,
) -> dict[str, Any]:
    return {
        "timestamp": _utc_timestamp(now),
        "event": event,
        "result": "preserved" if event == "preserved" else event,
        "reason": reason,
        "path": str(path),
        "owner": entry["owner"] if entry else None,
        "class": entry["class"] if entry else None,
        "bytes": 0,
        "policy_version": policy_version,
        "manifest_sha256": manifest_sha256,
        "transaction_id": None,
        "quarantine_path": None,
    }


def _lease_is_active(entry: dict[str, Any], now: int) -> bool:
    lease = entry["lease"]
    if lease is None:
        return False
    path = Path(lease["path"])
    try:
        age = now - path.stat().st_mtime
    except FileNotFoundError:
        return False
    return age <= lease["max_age_seconds"]


def worktree_reclaim_decision(
    *,
    is_current: bool,
    is_locked: bool,
    is_clean: bool,
    remote_contains_head: bool,
    open_state: str,
) -> str:
    if is_current:
        return "current_worktree"
    if is_locked:
        return "locked_worktree"
    if not is_clean:
        return "dirty_worktree"
    if not remote_contains_head:
        return "head_not_on_remote"
    if open_state == "open":
        return "open_worktree"
    if open_state != "confirmed-closed":
        return "lsof_error"
    return "eligible"


def _command(
    *args: str, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def path_open_state(path: Path) -> str:
    executable = Path("/usr/sbin/lsof")
    if not executable.is_file():
        return "error"
    result = _command(str(executable), "+D", str(path), cwd=path.parent)
    if result.returncode == 0 or result.stdout.strip():
        return "open"
    if result.returncode == 1 and not result.stdout and not result.stderr:
        return "confirmed-closed"
    return "error"


def _worktree_records(repo: Path) -> list[dict[str, Any]]:
    result = _command("git", "worktree", "list", "--porcelain", cwd=repo)
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "git worktree list failed")
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value if value else True
    return records


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return path != root


def _inspect_worktree(repo: Path, path: Path, locked: bool) -> tuple[str, str, list[str]]:
    if not path.is_dir():
        return "path_missing", "", []
    cwd = Path.cwd().resolve()
    resolved = path.resolve()
    head_result = _command("git", "rev-parse", "HEAD", cwd=path)
    if head_result.returncode != 0:
        return "git_state_unreadable", "", []
    head = head_result.stdout.strip()
    status = _command(
        "git", "status", "--porcelain=v1", "--untracked-files=all", cwd=path
    )
    if status.returncode != 0:
        return "git_state_unreadable", head, []
    refs_result = _command("git", "branch", "-r", "--contains", head, cwd=repo)
    if refs_result.returncode != 0:
        return "remote_state_unreadable", head, []
    refs = [
        line.strip().removeprefix("* ")
        for line in refs_result.stdout.splitlines()
        if line.strip() and " -> " not in line
    ]
    reason = worktree_reclaim_decision(
        is_current=resolved == cwd or resolved in cwd.parents,
        is_locked=locked,
        is_clean=not bool(status.stdout),
        remote_contains_head=bool(refs),
        open_state=path_open_state(path),
    )
    return reason, head, refs


def _du_bytes(path: Path) -> int:
    result = _command("du", "-sk", str(path), cwd=path.parent)
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "du failed")
    return int(result.stdout.split()[0]) * 1024


def _regeneration_proof(path: Path) -> Path | None:
    for name in DISCOVERABLE_OUTPUT_PROOFS.get(path.name, ()):
        proof = path.parent / name
        if proof.is_file() and not proof.is_symlink():
            return proof
    return None


def _is_git_ignored(path: Path) -> bool:
    result = _command(
        "git",
        "check-ignore",
        "-q",
        "--",
        str(path),
        cwd=path.parent,
    )
    return result.returncode == 0


def discover_regenerable_outputs(roots: list[Path]) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for raw_root in sorted(roots, key=str):
        root = Path(os.path.normpath(str(raw_root.expanduser())))
        if (
            not root.is_absolute()
            or not root.is_dir()
            or root.is_symlink()
            or any(part in PROTECTED_DISCOVERY_PARTS for part in root.parts)
        ):
            continue
        for directory, child_dirs, _ in os.walk(root, topdown=True, followlinks=False):
            parent = Path(directory)
            child_dirs[:] = sorted(
                name
                for name in child_dirs
                if name not in PROTECTED_DISCOVERY_PARTS
            )
            for name in tuple(child_dirs):
                if name not in DISCOVERABLE_OUTPUT_PROOFS:
                    continue
                candidate = parent / name
                child_dirs.remove(name)
                if candidate in seen or candidate.is_symlink():
                    continue
                proof = _regeneration_proof(candidate)
                if proof is None or not _is_git_ignored(candidate):
                    continue
                seen.add(candidate)
                digest = hashlib.sha256(str(candidate).encode("utf-8")).hexdigest()[:20]
                discovered.append(
                    {
                        "id": f"discovered-build-output-{digest}",
                        "path": str(candidate),
                        "owner": "cleanup-discovery",
                        "class": REGENERABLE_OUTPUT_CLASS,
                        "ttl_seconds": None,
                        "quota_bytes": 0,
                        "lease": None,
                        "finalizer": {
                            "kind": "verified_regenerable_remove",
                            "proof_path": str(proof),
                        },
                    }
                )
    return sorted(discovered, key=lambda item: item["path"])


def discover_chrome_code_sign_clones(
    roots: list[Path],
    *,
    proof_path: Path,
) -> list[dict[str, Any]]:
    proof = Path(os.path.normpath(str(proof_path.expanduser())))
    if (
        not proof.is_absolute()
        or not proof.is_file()
        or proof.is_symlink()
    ):
        return []

    discovered: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for raw_root in sorted(roots, key=str):
        root = Path(os.path.normpath(str(raw_root.expanduser())))
        collection = root / "com.google.Chrome.code_sign_clone"
        if (
            not root.is_absolute()
            or not collection.is_dir()
            or collection.is_symlink()
        ):
            continue
        for candidate in sorted(collection.glob("code_sign_clone.*"), key=str):
            if (
                candidate in seen
                or not candidate.is_dir()
                or candidate.is_symlink()
            ):
                continue
            seen.add(candidate)
            digest = hashlib.sha256(str(candidate).encode("utf-8")).hexdigest()[:20]
            discovered.append(
                {
                    "id": f"chrome-code-sign-clone-{digest}",
                    "path": str(candidate),
                    "owner": "macos-code-sign-clone",
                    "class": REGENERABLE_OUTPUT_CLASS,
                    "ttl_seconds": None,
                    "quota_bytes": 0,
                    "lease": None,
                    "finalizer": {
                        "kind": "verified_regenerable_remove",
                        "proof_path": str(proof),
                    },
                }
            )
    return discovered


def discover_pnpm_store_versions(
    roots: list[Path],
    *,
    proof_path: Path,
) -> list[dict[str, Any]]:
    proof = Path(os.path.normpath(str(proof_path.expanduser())))
    if (
        not proof.is_absolute()
        or not proof.is_file()
        or proof.is_symlink()
    ):
        return []

    discovered: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for raw_root in sorted(roots, key=str):
        root = Path(os.path.normpath(str(raw_root.expanduser())))
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            continue
        for candidate in sorted(root.glob("v[0-9]*"), key=str):
            if (
                candidate in seen
                or not candidate.is_dir()
                or candidate.is_symlink()
            ):
                continue
            seen.add(candidate)
            digest = hashlib.sha256(str(candidate).encode("utf-8")).hexdigest()[:20]
            discovered.append(
                {
                    "id": f"pnpm-store-{digest}",
                    "path": str(candidate),
                    "owner": "pnpm-store",
                    "class": REGENERABLE_OUTPUT_CLASS,
                    "ttl_seconds": None,
                    "quota_bytes": 0,
                    "lease": None,
                    "finalizer": {
                        "kind": "verified_regenerable_remove",
                        "proof_path": str(proof),
                    },
                }
            )
    return discovered


def discover_published_runs(roots: list[Path]) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    required_proof_fields = ("postId", "postedAt", "integration", "method")
    for raw_root in sorted(roots, key=str):
        root = Path(os.path.normpath(str(raw_root.expanduser())))
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            continue
        for candidate in sorted(root.iterdir(), key=lambda item: str(item)):
            if not candidate.is_dir() or candidate.is_symlink():
                continue
            proof = candidate / "reel-meta.json"
            output = candidate / "reel-final.mp4"
            if (
                not proof.is_file()
                or proof.is_symlink()
                or not output.is_file()
                or output.is_symlink()
            ):
                continue
            try:
                metadata = json.loads(proof.read_text(encoding="utf-8"))
                output_bytes = output.stat().st_size
            except (OSError, json.JSONDecodeError):
                continue
            if (
                not isinstance(metadata, dict)
                or output_bytes <= 0
                or any(
                    not isinstance(metadata.get(field), str)
                    or not metadata[field].strip()
                    for field in required_proof_fields
                )
            ):
                continue
            digest = hashlib.sha256(str(candidate).encode("utf-8")).hexdigest()[:20]
            discovered.append(
                {
                    "id": f"published-run-{digest}",
                    "path": str(candidate),
                    "owner": "reelclaw",
                    "class": REGENERABLE_OUTPUT_CLASS,
                    "ttl_seconds": None,
                    "quota_bytes": 0,
                    "lease": None,
                    "finalizer": {
                        "kind": "verified_regenerable_remove",
                        "proof_path": str(proof),
                    },
                }
            )
    return discovered


def discover_ephemeral_caches(
    roots: list[Path],
    *,
    minimum_bytes: int,
) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for raw_root in sorted(roots, key=str):
        root = Path(os.path.normpath(str(raw_root.expanduser())))
        if (
            not root.is_absolute()
            or not root.is_dir()
            or root.is_symlink()
            or any(part in PROTECTED_DISCOVERY_PARTS for part in root.parts)
        ):
            continue
        for candidate in sorted(root.iterdir(), key=lambda item: str(item)):
            if (
                not candidate.is_dir()
                or candidate.is_symlink()
                or any(token in candidate.name.lower() for token in BROWSER_CACHE_TOKENS)
            ):
                continue
            try:
                size = _du_bytes(candidate)
            except (OSError, ValueError):
                continue
            if size < minimum_bytes:
                continue
            digest = hashlib.sha256(str(candidate).encode("utf-8")).hexdigest()[:20]
            discovered.append(
                {
                    "id": f"discovered-cache-{digest}",
                    "path": str(candidate),
                    "owner": "cleanup-discovery",
                    "class": "ephemeral",
                    "ttl_seconds": 604800,
                    "quota_bytes": 0,
                    "lease": None,
                    "finalizer": {"kind": "off_volume_quarantine"},
                }
            )
    return discovered


def build_runtime_manifest(
    *,
    manifest_path: Path,
    output_path: Path,
    roots: list[Path],
    cache_roots: list[Path],
    minimum_cache_bytes: int,
    published_run_roots: list[Path] | None = None,
    code_sign_clone_roots: list[Path] | None = None,
    chrome_code_sign_proof: Path = Path(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ),
    pnpm_store_roots: list[Path] | None = None,
    pnpm_proof: Path = Path("/opt/homebrew/lib/node_modules/pnpm/bin/pnpm.cjs"),
) -> dict[str, int | str]:
    policy_version, _, base_entries = load_manifest(manifest_path)
    existing_paths = {entry["path"] for entry in base_entries}
    discovered = [
        entry
        for entry in [
            *discover_regenerable_outputs(roots),
            *discover_published_runs(published_run_roots or []),
            *discover_chrome_code_sign_clones(
                code_sign_clone_roots or [],
                proof_path=chrome_code_sign_proof,
            ),
            *discover_pnpm_store_versions(
                pnpm_store_roots or [],
                proof_path=pnpm_proof,
            ),
            *discover_ephemeral_caches(
                cache_roots,
                minimum_bytes=max(1, int(minimum_cache_bytes)),
            ),
        ]
        if entry["path"] not in existing_paths
    ]
    discovered.sort(key=lambda item: item["path"])
    payload = {
        "policy_version": policy_version,
        "artifacts": [*base_entries, *discovered],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    os.replace(temporary, output_path)
    return {
        "status": "ok",
        "discovered": len(discovered),
        "output": str(output_path),
    }


def sweep_worktree_collection(
    *,
    collection_root: Path,
    repository_root: Path | None = None,
    ledger_path: Path,
    policy_version: str,
    manifest_sha256: str,
    now: int,
) -> dict[str, int]:
    result = {"removed": 0, "preserved": 0, "errors": 0, "bytes_removed": 0}
    repo = collection_root.parent if repository_root is None else repository_root
    fetch = _command("git", "fetch", "--all", "--prune", cwd=repo)
    if fetch.returncode != 0:
        event = _event_base(
            event="preserved",
            reason="remote_fetch_failed",
            path=collection_root,
            entry={"owner": "git-worktrees", "class": WORKTREE_COLLECTION_CLASS},
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        event["result"] = "error"
        append_ledger(ledger_path, event)
        result["errors"] = 1
        result["preserved"] = 1
        return result
    try:
        records = _worktree_records(repo)
    except OSError:
        result["errors"] = 1
        return result
    for record in records:
        path = Path(str(record.get("worktree", "")))
        if not path.is_absolute() or not _inside(path, collection_root):
            continue
        entry = {"owner": "git-worktrees", "class": WORKTREE_COLLECTION_CLASS}
        locked = bool(record.get("locked"))
        reason, head, refs = _inspect_worktree(repo, path, locked)
        if reason != "eligible":
            event = _event_base(
                event="preserved",
                reason=reason,
                path=path,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            event.update({"head": head or None, "remote_refs": refs})
            if reason in {"git_state_unreadable", "remote_state_unreadable", "lsof_error"}:
                event["result"] = "error"
                result["errors"] += 1
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        try:
            before = _du_bytes(path)
        except (OSError, ValueError):
            before = 0
        recheck_reason, recheck_head, recheck_refs = _inspect_worktree(repo, path, locked)
        if recheck_reason != "eligible" or recheck_head != head:
            event = _event_base(
                event="preserved",
                reason=f"revalidation_{recheck_reason}",
                path=path,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            event.update({"head": recheck_head or None, "remote_refs": recheck_refs})
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        removed = _command("git", "worktree", "remove", str(path), cwd=repo)
        if removed.returncode != 0 or path.exists():
            event_name = "failed"
            event_reason = "git_worktree_remove_failed"
            event_result = "error"
            result["errors"] += 1
        else:
            event_name = "removed"
            event_reason = "remote_recoverable_worktree"
            event_result = "success"
            result["removed"] += 1
            result["bytes_removed"] += before
        event = _event_base(
            event=event_name,
            reason=event_reason,
            path=path,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        event.update(
            {
                "result": event_result,
                "bytes": before,
                "head": head,
                "remote_refs": refs,
            }
        )
        append_ledger(ledger_path, event)
    return result


def _inspect_git_clone(path: Path) -> tuple[str, str, list[str]]:
    if not path.is_dir() or path.is_symlink() or not (path / ".git").exists():
        return "not_a_git_repository", "", []
    head_result = _command("git", "rev-parse", "HEAD", cwd=path)
    if head_result.returncode != 0:
        return "git_state_unreadable", "", []
    head = head_result.stdout.strip()
    status = _command(
        "git", "status", "--porcelain=v1", "--untracked-files=all", cwd=path
    )
    if status.returncode != 0:
        return "git_state_unreadable", head, []
    if status.stdout.strip():
        return "dirty_clone", head, []
    fetch = _command("git", "fetch", "--all", "--prune", cwd=path)
    if fetch.returncode != 0:
        return "remote_fetch_failed", head, []
    refs_result = _command("git", "branch", "-r", "--contains", head, cwd=path)
    if refs_result.returncode != 0:
        return "remote_state_unreadable", head, []
    refs = [
        line.strip().removeprefix("* ")
        for line in refs_result.stdout.splitlines()
        if line.strip() and " -> " not in line
    ]
    if not refs:
        return "head_not_on_remote", head, refs
    open_state = path_open_state(path)
    if open_state == "open":
        return "open_clone", head, refs
    if open_state != "confirmed-closed":
        return "lsof_error", head, refs
    return "eligible", head, refs


def sweep_git_clone_collection(
    *,
    collection_root: Path,
    child_name_prefix: str,
    ledger_path: Path,
    policy_version: str,
    manifest_sha256: str,
    now: int,
) -> dict[str, int]:
    result = {"removed": 0, "preserved": 0, "errors": 0, "bytes_removed": 0}
    if not collection_root.is_dir():
        # collection_root itself may legitimately be a symlink (macOS /tmp ->
        # /private/tmp); only reject it if it does not resolve to a directory.
        return result
    entry = {"owner": "agent-temp-clones", "class": GIT_CLONE_COLLECTION_CLASS}
    children = sorted(
        (
            child
            for child in collection_root.iterdir()
            if child.name.startswith(child_name_prefix)
        ),
        key=lambda item: item.name,
    )
    error_reasons = {
        "git_state_unreadable",
        "remote_fetch_failed",
        "remote_state_unreadable",
        "lsof_error",
    }
    for path in children:
        reason, head, refs = _inspect_git_clone(path)
        if reason != "eligible":
            event = _event_base(
                event="preserved",
                reason=reason,
                path=path,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            event.update({"head": head or None, "remote_refs": refs})
            if reason in error_reasons:
                event["result"] = "error"
                result["errors"] += 1
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        try:
            before = _du_bytes(path)
        except (OSError, ValueError):
            before = 0
        recheck_reason, recheck_head, recheck_refs = _inspect_git_clone(path)
        if recheck_reason != "eligible" or recheck_head != head:
            event = _event_base(
                event="preserved",
                reason=f"revalidation_{recheck_reason}",
                path=path,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            event.update({"head": recheck_head or None, "remote_refs": recheck_refs})
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        try:
            _remove_source(path)
            removal_ok = not path.exists() and not path.is_symlink()
        except OSError:
            removal_ok = False
        if not removal_ok:
            event_name = "failed"
            event_reason = "clone_remove_failed"
            event_result = "error"
            result["errors"] += 1
        else:
            event_name = "removed"
            event_reason = "remote_recoverable_clone"
            event_result = "success"
            result["removed"] += 1
            result["bytes_removed"] += before
        event = _event_base(
            event=event_name,
            reason=event_reason,
            path=path,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        event.update(
            {
                "result": event_result,
                "bytes": before,
                "head": head,
                "remote_refs": refs,
            }
        )
        append_ledger(ledger_path, event)
    return result


def _quarantine(
    *,
    source: Path,
    entry: dict[str, Any],
    quarantine_root: Path,
    ledger_path: Path,
    policy_version: str,
    manifest_sha256: str,
    now: int,
) -> tuple[bool, int, str]:
    size = artifact_size(source)
    if not quarantine_root.exists() or not quarantine_root.is_dir() or quarantine_root.is_symlink():
        # The off-volume store is absent (measured 2026-07-26:
        # /Volumes/AniccaQuarantine does not exist), so every ephemeral
        # candidate used to return quarantine_unavailable and the guard idled
        # through a real ENOSPC. An expired ephemeral artifact is regenerable
        # by definition: remove it directly and record why. Protected classes
        # never reach this function.
        transaction_id = uuid.uuid4().hex
        planned = _event_base(
            event="planned",
            reason="quarantine_unavailable_direct_remove",
            path=source,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        planned.update({"bytes": size, "transaction_id": transaction_id})
        append_ledger(ledger_path, planned)
        try:
            if source.is_dir() and not source.is_symlink():
                shutil.rmtree(source)
            else:
                source.unlink()
        except OSError as error:
            failed = _event_base(
                event="failed",
                reason="quarantine_unavailable_direct_remove",
                path=source,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            failed.update(
                {
                    "result": "failure",
                    "bytes": size,
                    "transaction_id": transaction_id,
                    "error": type(error).__name__,
                }
            )
            append_ledger(ledger_path, failed)
            return False, 0, "quarantine_unavailable"
        complete = _event_base(
            event="quarantined",
            reason="quarantine_unavailable_direct_remove",
            path=source,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        complete.update(
            {
                "result": "success",
                "bytes": size,
                "transaction_id": transaction_id,
                "quarantine_path": None,
            }
        )
        append_ledger(ledger_path, complete)
        return True, size, "quarantine_unavailable_direct_remove"
    if device_id(source) == device_id(quarantine_root):
        return False, 0, "quarantine_not_off_volume"
    transaction_id = uuid.uuid4().hex
    temporary = quarantine_root / f".tmp-{transaction_id}"
    final = quarantine_root / transaction_id
    payload = temporary / "payload"
    source_digest = artifact_digest(source)
    planned = _event_base(
        event="planned",
        reason="expired_ephemeral_over_quota",
        path=source,
        entry=entry,
        policy_version=policy_version,
        manifest_sha256=manifest_sha256,
        now=now,
    )
    planned.update({"bytes": size, "transaction_id": transaction_id})
    append_ledger(ledger_path, planned)
    try:
        temporary.mkdir(mode=0o700)
        _copy_artifact(source, payload)
        if artifact_digest(payload) != source_digest:
            raise OSError("quarantine digest mismatch")
        if artifact_digest(source) != source_digest:
            raise OSError("source changed during quarantine")
        record = {
            "transaction_id": transaction_id,
            "original_path": str(source),
            "quarantine_path": str(final / "payload"),
            "owner": entry["owner"],
            "class": entry["class"],
            "bytes": size,
            "artifact_sha256": source_digest,
            "policy_version": policy_version,
            "manifest_sha256": manifest_sha256,
            "quarantined_at": _utc_timestamp(now),
        }
        record_path = temporary / "record.json"
        record_path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        with record_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, final)
        _remove_source(source)
    except Exception as exc:  # source remains unless a verified copy already exists
        failed = _event_base(
            event="failed",
            reason=f"quarantine_failed:{type(exc).__name__}",
            path=source,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        failed.update(
            {
                "result": "error",
                "bytes": size,
                "transaction_id": transaction_id,
                "quarantine_path": str(final / "payload") if final.exists() else None,
            }
        )
        append_ledger(ledger_path, failed)
        return False, 0, failed["reason"]
    complete = _event_base(
        event="quarantined",
        reason="expired_ephemeral_over_quota",
        path=source,
        entry=entry,
        policy_version=policy_version,
        manifest_sha256=manifest_sha256,
        now=now,
    )
    complete.update(
        {
            "result": "success",
            "bytes": size,
            "transaction_id": transaction_id,
            "quarantine_path": str(final / "payload"),
        }
    )
    append_ledger(ledger_path, complete)
    return True, size, "quarantined"


def sweep(
    *,
    manifest_path: Path,
    quarantine_root: Path,
    ledger_path: Path,
    now: int | None = None,
    candidates: list[Path] | None = None,
    pressure_override: bool = False,
    reclaim_target_bytes: int = 0,
) -> dict[str, int | str]:
    now = int(time.time()) if now is None else int(now)
    reclaim_target_bytes = max(0, int(reclaim_target_bytes))
    try:
        policy_version, manifest_sha256, entries = load_manifest(manifest_path)
    except ManifestError as exc:
        event = _event_base(
            event="manifest_error",
            reason=str(exc),
            path=manifest_path,
            entry=None,
            policy_version="unknown",
            manifest_sha256="unknown",
            now=now,
        )
        event["result"] = "error"
        append_ledger(ledger_path, event)
        return {
            "status": "manifest_error",
            "evaluated": 0,
            "quarantined": 0,
            "preserved": 0,
            "errors": 1,
            "bytes_quarantined": 0,
        }

    by_path = {Path(item["path"]): item for item in entries}
    targets = [Path(item["path"]) for item in entries] if candidates is None else [Path(p) for p in candidates]
    result: dict[str, int | str] = {
        "status": "ok",
        "evaluated": len(targets),
        "quarantined": 0,
        "preserved": 0,
        "errors": 0,
        "bytes_quarantined": 0,
    }
    for raw_target in targets:
        target = Path(os.path.normpath(str(raw_target.expanduser())))
        entry = by_path.get(target)
        if entry is None:
            event = _event_base(
                event="preserved",
                reason="unknown_artifact",
                path=target,
                entry=None,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        if not target.exists() and not target.is_symlink():
            event = _event_base(
                event="preserved",
                reason="path_missing",
                path=target,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        if (
            pressure_override
            and entry["class"] == "ephemeral"
            and reclaim_target_bytes > 0
            and result["bytes_quarantined"] >= reclaim_target_bytes
        ):
            event = _event_base(
                event="preserved",
                reason="pressure_target_met",
                path=target,
                entry=entry,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            append_ledger(ledger_path, event)
            result["preserved"] += 1
            continue
        if entry["class"] == WORKTREE_COLLECTION_CLASS:
            repository_path = entry["finalizer"].get("repository_path")
            collection = sweep_worktree_collection(
                collection_root=target,
                repository_root=Path(repository_path) if repository_path else None,
                ledger_path=ledger_path,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            result["quarantined"] += collection["removed"]
            result["bytes_quarantined"] += collection["bytes_removed"]
            result["preserved"] += collection["preserved"]
            result["errors"] += collection["errors"]
            continue
        if entry["class"] == GIT_CLONE_COLLECTION_CLASS:
            clone_collection = sweep_git_clone_collection(
                collection_root=target,
                child_name_prefix=entry["finalizer"]["child_name_prefix"],
                ledger_path=ledger_path,
                policy_version=policy_version,
                manifest_sha256=manifest_sha256,
                now=now,
            )
            result["quarantined"] += clone_collection["removed"]
            result["bytes_quarantined"] += clone_collection["bytes_removed"]
            result["preserved"] += clone_collection["preserved"]
            result["errors"] += clone_collection["errors"]
            continue
        if entry["class"] == REGENERABLE_OUTPUT_CLASS:
            proof = Path(entry["finalizer"]["proof_path"])
            if not proof.is_file() or proof.is_symlink():
                reason = "regeneration_proof_missing"
            elif _lease_is_active(entry, now):
                reason = "active_lease"
            else:
                open_state = path_open_state(target)
                if open_state == "open":
                    reason = "open_path"
                elif open_state != "confirmed-closed":
                    reason = "lsof_error"
                    result["errors"] += 1
                else:
                    try:
                        size = _du_bytes(target)
                        if (
                            not proof.is_file()
                            or proof.is_symlink()
                            or _lease_is_active(entry, now)
                            or path_open_state(target) != "confirmed-closed"
                        ):
                            reason = "revalidation_failed"
                        else:
                            _remove_source(target)
                            if target.exists() or target.is_symlink():
                                raise OSError("regenerable output still exists")
                    except OSError as exc:
                        reason = f"remove_failed:{type(exc).__name__}"
                        result["errors"] += 1
                    else:
                        event = _event_base(
                            event="removed",
                            reason="verified_regenerable_output",
                            path=target,
                            entry=entry,
                            policy_version=policy_version,
                            manifest_sha256=manifest_sha256,
                            now=now,
                        )
                        event.update(
                            {
                                "result": "success",
                                "bytes": size,
                                "regeneration_proof": str(proof),
                            }
                        )
                        append_ledger(ledger_path, event)
                        result["quarantined"] += 1
                        result["bytes_quarantined"] += size
                        continue
        if entry["class"] == REGENERABLE_OUTPUT_CLASS:
            pass
        elif entry["class"] != "ephemeral":
            reason = "protected_class"
        elif _lease_is_active(entry, now):
            reason = "active_lease"
        else:
            try:
                size = artifact_size(target)
                newest = newest_mtime(target)
            except OSError as exc:
                reason = f"artifact_unreadable:{type(exc).__name__}"
                result["errors"] += 1
            else:
                if size <= entry["quota_bytes"]:
                    reason = "within_quota"
                elif newest > now - entry["ttl_seconds"] and not pressure_override:
                    reason = "ttl_not_expired"
                else:
                    open_state = (
                        path_open_state(target) if pressure_override else "confirmed-closed"
                    )
                    if open_state == "open":
                        reason = "open_path"
                    elif open_state != "confirmed-closed":
                        reason = "lsof_error"
                        result["errors"] += 1
                    elif _lease_is_active(entry, now):
                        reason = "revalidation_active_lease"
                    elif pressure_override and path_open_state(target) != "confirmed-closed":
                        reason = "revalidation_open_path"
                    else:
                        moved, moved_bytes, reason = _quarantine(
                            source=target,
                            entry=entry,
                            quarantine_root=quarantine_root,
                            ledger_path=ledger_path,
                            policy_version=policy_version,
                            manifest_sha256=manifest_sha256,
                            now=now,
                        )
                        if moved:
                            result["quarantined"] += 1
                            result["bytes_quarantined"] += moved_bytes
                            continue
                        result["errors"] += 1
        event = _event_base(
            event="preserved",
            reason=reason,
            path=target,
            entry=entry,
            policy_version=policy_version,
            manifest_sha256=manifest_sha256,
            now=now,
        )
        # Protected/leased roots can be very large. Exact byte measurement is
        # required for a move, but a preserve decision must remain bounded.
        event["bytes"] = 0
        if reason.startswith(("quarantine_", "artifact_unreadable:")) or reason == "lsof_error":
            event["result"] = "error"
        append_ledger(ledger_path, event)
        result["preserved"] += 1
    return result


def restore(
    *, transaction_id: str, quarantine_root: Path, ledger_path: Path
) -> dict[str, str]:
    now = int(time.time())
    if not TX_RE.fullmatch(transaction_id):
        return {"status": "invalid_transaction"}
    transaction_dir = quarantine_root / transaction_id
    record_path = transaction_dir / "record.json"
    payload = transaction_dir / "payload"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("transaction_id") != transaction_id:
            raise ValueError("transaction id mismatch")
        original = _normalized_path(record["original_path"])
        expected_digest = record["artifact_sha256"]
        if artifact_digest(payload) != expected_digest:
            raise ValueError("quarantine digest mismatch")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ManifestError) as exc:
        return {"status": "invalid_quarantine", "reason": str(exc)}
    if original.exists() or original.is_symlink():
        append_ledger(
            ledger_path,
            {
                **_event_base(
                    event="restore_refused",
                    reason="original_path_conflict",
                    path=original,
                    entry={"owner": record.get("owner"), "class": record.get("class")},
                    policy_version=record.get("policy_version", "unknown"),
                    manifest_sha256=record.get("manifest_sha256", "unknown"),
                    now=now,
                ),
                "result": "conflict",
                "transaction_id": transaction_id,
                "quarantine_path": str(payload),
            },
        )
        return {"status": "conflict"}
    original.parent.mkdir(parents=True, exist_ok=True)
    temporary = original.parent / f".{original.name}.restore-{transaction_id}.tmp"
    try:
        _copy_artifact(payload, temporary)
        if artifact_digest(temporary) != expected_digest:
            raise OSError("restore digest mismatch")
        os.replace(temporary, original)
        shutil.rmtree(transaction_dir)
    except OSError as exc:
        if temporary.exists() or temporary.is_symlink():
            _remove_source(temporary)
        return {"status": "restore_error", "reason": str(exc)}
    append_ledger(
        ledger_path,
        {
            **_event_base(
                event="restored",
                reason="operator_restore",
                path=original,
                entry={"owner": record.get("owner"), "class": record.get("class")},
                policy_version=record.get("policy_version", "unknown"),
                manifest_sha256=record.get("manifest_sha256", "unknown"),
                now=now,
            ),
            "result": "success",
            "bytes": record.get("bytes", 0),
            "transaction_id": transaction_id,
            "quarantine_path": str(payload),
        },
    )
    return {"status": "restored", "path": str(original)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    sweep_parser = subcommands.add_parser("sweep")
    sweep_parser.add_argument("--manifest", required=True, type=Path)
    sweep_parser.add_argument("--quarantine-root", required=True, type=Path)
    sweep_parser.add_argument("--ledger", required=True, type=Path)
    sweep_parser.add_argument("--now", type=int)
    sweep_parser.add_argument("--candidate", action="append", type=Path)
    sweep_parser.add_argument("--pressure-override", action="store_true")
    sweep_parser.add_argument("--reclaim-target-bytes", type=int, default=0)
    runtime_manifest_parser = subcommands.add_parser("runtime-manifest")
    runtime_manifest_parser.add_argument("--manifest", required=True, type=Path)
    runtime_manifest_parser.add_argument("--output", required=True, type=Path)
    runtime_manifest_parser.add_argument("--root", action="append", required=True, type=Path)
    runtime_manifest_parser.add_argument("--cache-root", action="append", default=[], type=Path)
    runtime_manifest_parser.add_argument(
        "--published-run-root",
        action="append",
        default=[],
        type=Path,
    )
    runtime_manifest_parser.add_argument(
        "--code-sign-clone-root",
        action="append",
        default=[],
        type=Path,
    )
    runtime_manifest_parser.add_argument(
        "--chrome-code-sign-proof",
        type=Path,
        default=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    )
    runtime_manifest_parser.add_argument(
        "--pnpm-store-root",
        action="append",
        default=[],
        type=Path,
    )
    runtime_manifest_parser.add_argument(
        "--pnpm-proof",
        type=Path,
        default=Path("/opt/homebrew/lib/node_modules/pnpm/bin/pnpm.cjs"),
    )
    runtime_manifest_parser.add_argument(
        "--min-cache-bytes",
        type=int,
        default=1073741824,
    )
    restore_parser = subcommands.add_parser("restore")
    restore_parser.add_argument("--transaction-id", required=True)
    restore_parser.add_argument("--quarantine-root", required=True, type=Path)
    restore_parser.add_argument("--ledger", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "sweep":
        result = sweep(
            manifest_path=args.manifest,
            quarantine_root=args.quarantine_root,
            ledger_path=args.ledger,
            now=args.now,
            candidates=args.candidate,
            pressure_override=args.pressure_override,
            reclaim_target_bytes=args.reclaim_target_bytes,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "ok" and result["errors"] == 0 else 3
    if args.command == "runtime-manifest":
        try:
            result = build_runtime_manifest(
                manifest_path=args.manifest,
                output_path=args.output,
                roots=args.root,
                cache_roots=args.cache_root,
                minimum_cache_bytes=args.min_cache_bytes,
                published_run_roots=args.published_run_root,
                code_sign_clone_roots=args.code_sign_clone_root,
                chrome_code_sign_proof=args.chrome_code_sign_proof,
                pnpm_store_roots=args.pnpm_store_root,
                pnpm_proof=args.pnpm_proof,
            )
        except ManifestError as exc:
            result = {
                "status": "manifest_error",
                "discovered": 0,
                "output": str(args.output),
                "error": str(exc),
            }
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "ok" else 3
    result = restore(
        transaction_id=args.transaction_id,
        quarantine_root=args.quarantine_root,
        ledger_path=args.ledger,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "restored" else 4


if __name__ == "__main__":
    sys.exit(main())
