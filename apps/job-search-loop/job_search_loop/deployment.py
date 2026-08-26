from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path


class DeploymentError(RuntimeError):
    pass


def _launchd_state(label: str) -> dict[str, int | str | None]:
    completed = subprocess.run(
        ["/bin/launchctl", "print", f"gui/{os.getuid()}/{label}"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise DeploymentError("launchd owner is not loaded")
    state = re.search(r"^\s*state = (.+)$", completed.stdout, re.MULTILINE)
    runs = re.search(r"^\s*runs = (\d+)$", completed.stdout, re.MULTILINE)
    exit_code = re.search(
        r"^\s*last exit code = (-?\d+)$", completed.stdout, re.MULTILINE
    )
    return {
        "state": state.group(1).strip() if state else None,
        "runs": int(runs.group(1)) if runs else 0,
        "last_exit_code": int(exit_code.group(1)) if exit_code else None,
    }


def _verified_release(archive: Path, checksum: Path) -> tuple[str, str]:
    expected_fields = checksum.read_text(encoding="utf-8").strip().split()
    if len(expected_fields) != 2 or expected_fields[1] != archive.name:
        raise DeploymentError("release checksum record is invalid")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected_fields[0] != actual:
        raise DeploymentError("release archive checksum mismatch")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        roots = {Path(member.name).parts[0] for member in members if member.name}
        if len(roots) != 1 or any(
            member.issym() or member.islnk() or ".." in Path(member.name).parts
            for member in members
        ):
            raise DeploymentError("release archive layout is unsafe")
        root = next(iter(roots))
        metadata_member = bundle.getmember(f"{root}/RELEASE.json")
        metadata = json.loads(bundle.extractfile(metadata_member).read())
    commit = str(metadata.get("commit") or "")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise DeploymentError("release metadata commit is invalid")
    return root, commit


def _install_read_only(
    archive: Path, archive_root: str, commit: str, data_root: Path
) -> Path:
    releases = data_root / "releases"
    releases.mkdir(parents=True, exist_ok=True, mode=0o755)
    target = releases / commit
    if target.exists():
        metadata = json.loads((target / "RELEASE.json").read_text(encoding="utf-8"))
        if metadata.get("commit") != commit:
            raise DeploymentError("existing release identity mismatch")
        return target
    temporary_root = Path(tempfile.mkdtemp(prefix=".install-", dir=releases))
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(temporary_root, filter="data")
        extracted = temporary_root / archive_root
        os.replace(extracted, target)
    finally:
        if temporary_root.exists():
            temporary_root.rmdir()
    for path in sorted(target.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        os.chmod(path, 0o555 if path.is_dir() else (path.stat().st_mode & 0o555 or 0o444))
    os.chmod(target, 0o555)
    return target


def activate_and_kickstart(
    *,
    archive: Path,
    checksum: Path,
    data_root: Path,
    state_root: Path,
    label: str = "ai.anicca.job-search-daily",
    timeout_seconds: int = 1800,
) -> dict[str, object]:
    """Activate one immutable release and trigger only the existing launchd owner."""
    archive_root, commit = _verified_release(archive, checksum)
    release = _install_read_only(archive, archive_root, commit, data_root)
    deadline = time.monotonic() + timeout_seconds
    before = _launchd_state(label)
    while before["state"] != "not running":
        if time.monotonic() >= deadline:
            raise DeploymentError("hourly owner did not become idle")
        time.sleep(1)
        before = _launchd_state(label)

    current = data_root / "current"
    previous = str(current.resolve()) if current.is_symlink() else None
    temporary_link = data_root / f".current-{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(release)
    os.replace(temporary_link, current)

    evidence_root = state_root / "evidence"
    baseline = {path.name for path in evidence_root.glob("daily-*")}
    kickstart = subprocess.run(
        [
            "/bin/launchctl",
            "kickstart",
            "-k",
            f"gui/{os.getuid()}/{label}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if kickstart.returncode != 0:
        raise DeploymentError("launchd kickstart failed")

    run_directory = None
    after = before
    while time.monotonic() < deadline:
        candidates = sorted(
            (path for path in evidence_root.glob("daily-*") if path.name not in baseline),
            key=lambda path: path.name,
        )
        if candidates:
            run_directory = candidates[-1]
        after = _launchd_state(label)
        if (
            run_directory is not None
            and int(after["runs"] or 0) > int(before["runs"] or 0)
            and after["state"] == "not running"
        ):
            break
        time.sleep(2)
    else:
        raise DeploymentError("launchd owner did not finish before timeout")
    if after["last_exit_code"] != 0:
        raise DeploymentError("launchd owner exited nonzero")
    evidence_files = sorted(
        str(path) for path in run_directory.rglob("*") if path.is_file()
    )
    return {
        "version": 1,
        "commit": commit,
        "previous_release": previous,
        "active_release": str(release),
        "run_directory": str(run_directory),
        "evidence_files": evidence_files,
        "launchd_runs_before": before["runs"],
        "launchd_runs_after": after["runs"],
        "launchd_exit_code": after["last_exit_code"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--checksum", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    receipt = activate_and_kickstart(
        archive=args.archive,
        checksum=args.checksum,
        data_root=args.data_root,
        state_root=args.state_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
