from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from .release_activation import ActivationError, LANES, _link_commit, _validate_release


class GuardianError(RuntimeError):
    pass


def release_health(data_root: Path, launcher_root: Path | None = None) -> dict[str, Any]:
    data_root = Path(data_root).resolve()
    receipt_path = data_root / "active-release.json"
    if receipt_path.stat().st_mode & 0o777 != 0o600:
        raise GuardianError("active release receipt permissions are invalid")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GuardianError("active release receipt is invalid") from error
    if not isinstance(receipt, dict) or set(receipt) != {
        "version", "active_commit", "manifest_sha256", "route_config_sha256"
    } or receipt.get("version") != 1:
        raise GuardianError("active release receipt contract is invalid")
    try:
        linked_commit = _link_commit(data_root, "current")
        candidate = _validate_release(data_root, str(receipt["active_commit"]))
    except (ActivationError, OSError) as error:
        raise GuardianError(str(error)) from error
    if linked_commit != receipt["active_commit"]:
        raise GuardianError("active release pointer differs from receipt")
    checks = {
        "manifest_sha256": candidate / "RELEASE.json",
        "route_config_sha256": candidate / "runtime/agent-runner/config.json",
    }
    for field, path in checks.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt[field]:
            raise GuardianError(f"active release {field} mismatch")
    launcher_root = Path(launcher_root or (
        Path.home() / ".local/libexec/anicca/job-search"
    )).resolve()
    stable_count = 0
    for lane in LANES:
        launcher = launcher_root / lane
        if (
            not launcher.is_file() or not os.access(launcher, os.X_OK)
            or stat.S_IMODE(launcher.stat().st_mode) & 0o222
        ):
            raise GuardianError(f"stable launcher is unhealthy: {lane}")
        stable_count += 1
    return {
        "version": 1,
        "status": "healthy",
        "active_commit": linked_commit,
        "runner_count": len(LANES),
        "stable_launcher_count": stable_count,
        "manifest_sha256": receipt["manifest_sha256"],
        "route_config_sha256": receipt["route_config_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    release = subparsers.add_parser("release")
    release.add_argument("--data-root", type=Path, required=True)
    release.add_argument("--launcher-root", type=Path, required=True)
    release.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = release_health(args.data_root, args.launcher_root)
    args.output.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps({
        "status": report["status"],
        "active_commit": report["active_commit"],
        "runner_count": report["runner_count"],
        "stable_launcher_count": report["stable_launcher_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
