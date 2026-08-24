#!/usr/bin/env python3
"""Build, verify, and atomically promote immutable Paid releases."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import shutil
from pathlib import Path

ENTRYPOINT = "skills/earn/gig/scripts/paid_direct.py"
MANIFEST = "RELEASE-MANIFEST.json"
DEFAULT_REPO = Path(__file__).resolve().parents[4]


class ReleaseError(RuntimeError):
    pass


def _git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=not binary,
    )
    if result.returncode:
        raise ReleaseError(f"git {' '.join(args)} failed")
    return result.stdout


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    return _sha(path.read_bytes())


def _content_digest(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST or path.is_dir():
            continue
        if path.is_symlink():
            target = os.readlink(path)
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError as error:
                raise ReleaseError(f"release symlink escapes root: {relative}") from error
            rows.append(f"L\0{relative}\0{target}".encode())
        elif path.is_file():
            rows.append(f"F\0{relative}\0{_file_sha(path)}".encode())
        else:
            raise ReleaseError(f"unsupported release entry: {relative}")
    return _sha(b"\n".join(rows)), len(rows)


def _manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError("release manifest is missing or invalid") from error
    if not isinstance(value, dict):
        raise ReleaseError("release manifest is not an object")
    return value


def _remote_commit(repo: Path, commit: str) -> bool:
    refs = _git(repo, "for-each-ref", "--format=%(refname)", "--contains", commit, "refs/remotes")
    return bool(str(refs).strip())


def _archive(repo: Path, commit: str) -> bytes:
    return bytes(_git(repo, "archive", "--format=tar", commit, binary=True))


def _release_filter(member: tarfile.TarInfo, destination: str) -> tarfile.TarInfo:
    """Apply the stdlib data policy while allowing symlinks that stay inside the release."""
    if not member.issym():
        return tarfile.data_filter(member, destination)
    filtered = tarfile.tar_filter(member, destination)
    root = Path(destination).resolve()
    target = (root / Path(filtered.name).parent / filtered.linkname).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ReleaseError(f"release symlink escapes root: {filtered.name}") from error
    return filtered


def verify(repo: Path, release: Path) -> dict:
    release = release.resolve()
    manifest = _manifest(release / MANIFEST)
    required = {
        "version", "lane", "git_commit", "git_tree", "git_archive_sha256",
        "entrypoint", "entrypoint_sha256", "import_closure_sha256", "file_count",
    }
    if set(manifest) != required or manifest["version"] != 1 or manifest["lane"] != "paid":
        raise ReleaseError("release manifest contract mismatch")
    commit = str(manifest["git_commit"])
    if release.name != commit or len(commit) != 40 or not _remote_commit(repo, commit):
        raise ReleaseError("release is not bound to a pushed commit")
    tree = str(_git(repo, "rev-parse", f"{commit}^{{tree}}")).strip()
    archive = _archive(repo, commit)
    entrypoint = release / str(manifest["entrypoint"])
    content_digest, file_count = _content_digest(release)
    checks = (
        manifest["git_tree"] == tree,
        manifest["git_archive_sha256"] == _sha(archive),
        entrypoint.is_file() and not entrypoint.is_symlink(),
        entrypoint.is_file() and manifest["entrypoint_sha256"] == _file_sha(entrypoint),
        manifest["import_closure_sha256"] == content_digest,
        manifest["file_count"] == file_count,
    )
    if not all(checks):
        raise ReleaseError("release verification failed")
    return {"status": "verified", "release": str(release), "git_commit": commit}


def build(repo: Path, release_root: Path, revision: str) -> dict:
    repo, release_root = repo.resolve(), release_root.resolve()
    if str(_git(repo, "status", "--porcelain=v1", "--untracked-files=all")).strip():
        raise ReleaseError("refusing to build from a dirty repository")
    commit = str(_git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")).strip()
    if len(commit) != 40 or not _remote_commit(repo, commit):
        raise ReleaseError("refusing to build an unpushed commit")
    release_root.mkdir(parents=True, exist_ok=True)
    destination = release_root / commit
    if destination.exists():
        return {**verify(repo, destination), "status": "existing"}
    archive = _archive(repo, commit)
    stage = Path(tempfile.mkdtemp(prefix=f".{commit}.build-", dir=release_root))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
            source.extractall(stage, filter=_release_filter)
        entrypoint = stage / ENTRYPOINT
        if not entrypoint.is_file() or entrypoint.is_symlink():
            raise ReleaseError("Paid entrypoint is missing from archive")
        content_digest, file_count = _content_digest(stage)
        manifest = {
            "version": 1, "lane": "paid", "git_commit": commit,
            "git_tree": str(_git(repo, "rev-parse", f"{commit}^{{tree}}")).strip(),
            "git_archive_sha256": _sha(archive), "entrypoint": ENTRYPOINT,
            "entrypoint_sha256": _file_sha(entrypoint),
            "import_closure_sha256": content_digest, "file_count": file_count,
        }
        (stage / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        for path in sorted(stage.rglob("*"), reverse=True):
            if path.is_symlink():
                continue
            mode = path.stat().st_mode
            path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        os.replace(stage, destination)
        destination.chmod(destination.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    finally:
        if stage.exists():
            for path in stage.rglob("*"):
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
            import shutil
            shutil.rmtree(stage)
    return {**verify(repo, destination), "status": "built"}


def _replace_link(link: Path, target: Path) -> None:
    temporary = link.with_name(f".{link.name}.{os.getpid()}.tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def promote(repo: Path, release_root: Path, release: Path) -> dict:
    release_root, release = release_root.resolve(), release.resolve()
    release.relative_to(release_root)
    verified = verify(repo.resolve(), release)
    current, previous = release_root / "current", release_root / "previous"
    old = current.resolve() if current.is_symlink() else None
    if old == release:
        return {**verified, "status": "current", "previous": str(previous.resolve()) if previous.is_symlink() else None}
    if old and old.parent == release_root and old.is_dir():
        _replace_link(previous, old)
    _replace_link(current, release)
    return {**verified, "status": "promoted", "previous": str(old) if old else None}


def status(repo: Path, release_root: Path) -> dict:
    result = {"status": "ok", "current": None, "previous": None, "pinned": []}
    for name in ("current", "previous"):
        link = release_root / name
        if link.is_symlink():
            target = link.resolve()
            verify(repo.resolve(), target)
            result[name] = str(target)
            result["pinned"].append(str(target))
    return result


def gc(repo: Path, release_root: Path) -> dict:
    """Remove only reproducible, verified releases not pinned as current/previous."""
    release_root = release_root.resolve()
    pinned = {Path(path) for path in status(repo.resolve(), release_root)["pinned"]}
    removed: list[str] = []
    reclaimed = 0
    for candidate in sorted(release_root.iterdir()):
        if (candidate.is_symlink() or not candidate.is_dir() or candidate in pinned
                or len(candidate.name) != 40
                or not set(candidate.name) <= set("0123456789abcdef")):
            continue
        try:
            verify(repo.resolve(), candidate)
        except ReleaseError:
            continue
        reclaimed += sum(path.stat().st_size for path in candidate.rglob("*")
                         if not path.is_symlink() and path.is_file())
        for path in sorted(candidate.rglob("*"), reverse=True):
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IWUSR)
        candidate.chmod(candidate.stat().st_mode | stat.S_IWUSR)
        shutil.rmtree(candidate)
        removed.append(str(candidate))
    return {"status": "collected", "removed": removed, "bytes_reclaimed": reclaimed,
            "pinned": sorted(str(path) for path in pinned)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--release-root", type=Path, default=Path.home() / "gig/releases/paid")
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build"); build_parser.add_argument("revision")
    verify_parser = sub.add_parser("verify"); verify_parser.add_argument("release", type=Path)
    promote_parser = sub.add_parser("promote"); promote_parser.add_argument("release", type=Path)
    sub.add_parser("status")
    sub.add_parser("gc")
    args = parser.parse_args()
    try:
        if args.command == "build": result = build(args.repo, args.release_root, args.revision)
        elif args.command == "verify": result = verify(args.repo, args.release)
        elif args.command == "promote": result = promote(args.repo, args.release_root, args.release)
        elif args.command == "status": result = status(args.repo, args.release_root)
        else: result = gc(args.repo, args.release_root)
    except (OSError, ReleaseError, subprocess.SubprocessError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
