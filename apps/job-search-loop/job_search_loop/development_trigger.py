from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Callable


Launchctl = Callable[[list[str]], tuple[int, str]]


def _object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _commit(release: Path) -> str:
    commit = str(_object(release).get("commit") or "")
    if re.fullmatch(r"[a-f0-9]{40}", commit) is None:
        raise ValueError("release commit is invalid")
    return commit


def _write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def create_request(request: Path, release: Path) -> dict[str, object]:
    value: dict[str, object] = {"version": 1, "commit": _commit(release)}
    _write(request, value)
    return value


def _launchctl(arguments: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        ["/bin/launchctl", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.returncode, completed.stdout


def consume_request(
    *,
    request: Path,
    release: Path,
    output: Path,
    uid: int,
    label: str,
    launchctl: Launchctl = _launchctl,
) -> dict[str, object]:
    metadata = request.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("development kickstart request must be a regular file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError("development kickstart request must be mode 0600")
    requested = _object(request)
    commit = _commit(release)
    if requested != {"version": 1, "commit": commit}:
        raise ValueError("development kickstart request does not match active release")
    target = f"gui/{uid}/{label}"
    returncode, raw = launchctl(["print", target])
    if returncode != 0:
        raise RuntimeError("development kickstart could not read launchd owner")
    state = next(
        (
            line.split("=", 1)[1].strip()
            for line in raw.splitlines()
            if line.strip().startswith("state =")
        ),
        "unknown",
    )
    if state != "not running":
        receipt: dict[str, object] = {
            "status": "owner_running",
            "commit": commit,
            "state": state,
        }
        _write(output, receipt)
        return receipt
    returncode, _raw = launchctl(["kickstart", target])
    if returncode != 0:
        raise RuntimeError("development kickstart failed")
    request.unlink()
    receipt = {"status": "kicked", "commit": commit, "state": state}
    _write(output, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--request", required=True, type=Path)
    create.add_argument("--release", required=True, type=Path)
    consume = subparsers.add_parser("consume")
    consume.add_argument("--request", required=True, type=Path)
    consume.add_argument("--release", required=True, type=Path)
    consume.add_argument("--output", required=True, type=Path)
    consume.add_argument("--uid", type=int, default=os.getuid())
    consume.add_argument("--label", default="ai.anicca.job-search-daily")
    args = parser.parse_args(argv)
    if args.command == "create":
        value = create_request(args.request, args.release)
    else:
        value = consume_request(
            request=args.request,
            release=args.release,
            output=args.output,
            uid=args.uid,
            label=args.label,
        )
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
