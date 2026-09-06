#!/usr/bin/env python3
"""Manage fail-closed leases for Life Manager task worktrees."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository(path: Path) -> tuple[Path, Path]:
    root = Path(run("git", "-C", str(path), "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    common = Path(run("git", "-C", str(root), "rev-parse", "--git-common-dir").stdout.strip())
    if not common.is_absolute():
        common = (root / common).resolve()
    return root, common


def worktrees(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in run("git", "-C", str(root), "worktree", "list", "--porcelain").stdout.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "locked":
            current[key] = value or True
        elif key in {"bare", "detached", "prunable"}:
            current[key] = True
        else:
            current[key] = value
    return records


def record_for(root: Path, target: Path) -> dict[str, object]:
    resolved = target.resolve()
    for record in worktrees(root):
        if Path(str(record["worktree"])).resolve() == resolved:
            return record
    raise SystemExit(f"not a registered worktree: {target}")


def lease_path(common: Path, target: Path) -> Path:
    digest = hashlib.sha256(str(target.resolve()).encode()).hexdigest()
    return common / "worktree-leases" / f"{digest}.json"


def load_lease(common: Path, target: Path) -> dict[str, object]:
    path = lease_path(common, target)
    if not path.exists():
        raise SystemExit(f"no managed lease for {target}")
    return json.loads(path.read_text())


def save_lease(common: Path, target: Path, data: dict[str, object]) -> None:
    path = lease_path(common, target)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def create_lease(common: Path, target: Path, data: dict[str, object]) -> None:
    path = lease_path(common, target)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def require_owner(lease: dict[str, object], owner: str) -> None:
    if lease.get("owner") != owner:
        raise SystemExit(f"owner mismatch: lease belongs to {lease.get('owner')!r}")


def validate_lease(lease: object, target: Path, record: dict[str, object], path: Path) -> tuple[dict[str, object] | None, str | None]:
    if not isinstance(lease, dict):
        return None, "lease is not an object"
    if type(lease.get("schema_version")) is not int or lease.get("schema_version") != 1 or lease.get("worktree") != str(target.resolve()):
        return None, "schema or worktree mismatch"
    for field in ("owner", "task"):
        if not isinstance(lease.get(field), str) or not str(lease[field]).strip():
            return None, f"invalid {field}"
    head = lease.get("head")
    if not isinstance(head, str) or len(head) != 40 or any(character not in "0123456789abcdef" for character in head.lower()):
        return None, "invalid head"
    if record.get("locked") != f"managed-lease:{path}":
        return None, "native lock missing or reason mismatch"
    try:
        timestamps = [datetime.fromisoformat(str(lease[field]).replace("Z", "+00:00")) for field in ("created_at", "heartbeat_at", "expires_at")]
        if any(value.tzinfo is None for value in timestamps) or not timestamps[0] <= timestamps[1] < timestamps[2]:
            raise ValueError("timezone or ordering invalid")
    except (KeyError, TypeError, ValueError):
        return None, "invalid timestamps"
    return lease, None


def acquire(args: argparse.Namespace) -> None:
    if not args.owner.strip() or not args.task.strip():
        raise SystemExit("owner and task must be non-empty")
    target, common = repository(Path(args.path))
    record = record_for(target, target)
    path = lease_path(common, target)
    if record.get("locked") or path.exists():
        raise SystemExit(f"worktree already locked or leased: {target}")
    timestamp = now()
    data = {
        "schema_version": 1,
        "owner": args.owner,
        "task": args.task,
        "worktree": str(target),
        "head": record.get("HEAD"),
        "created_at": iso(timestamp),
        "heartbeat_at": iso(timestamp),
        "expires_at": iso(timestamp + timedelta(hours=args.ttl_hours)),
    }
    run("git", "-C", str(target), "worktree", "lock", "--reason", f"managed-lease:{path}", str(target))
    try:
        create_lease(common, target, data)
    except Exception:
        run("git", "-C", str(target), "worktree", "unlock", str(target), check=False)
        raise
    print(json.dumps(data, sort_keys=True))


def heartbeat(args: argparse.Namespace) -> None:
    target, common = repository(Path(args.path))
    record = record_for(target, target)
    lease = load_lease(common, target)
    lease, error = validate_lease(lease, target, record, lease_path(common, target))
    if error:
        raise SystemExit(f"invalid managed lease: {error}")
    assert lease is not None
    require_owner(lease, args.owner)
    timestamp = now()
    lease["heartbeat_at"] = iso(timestamp)
    lease["expires_at"] = iso(timestamp + timedelta(hours=args.ttl_hours))
    lease["head"] = run("git", "-C", str(target), "rev-parse", "HEAD").stdout.strip()
    save_lease(common, target, lease)
    print(json.dumps(lease, sort_keys=True))


def audit(args: argparse.Namespace) -> None:
    root, common = repository(Path(args.path))
    timestamp = now()
    output = []
    for record in worktrees(root):
        target = Path(str(record["worktree"]))
        path = lease_path(common, target)
        item = {"worktree": str(target), "locked": bool(record.get("locked"))}
        if path.exists():
            try:
                raw = json.loads(path.read_text())
                lease, error = validate_lease(raw, target.resolve(), record, path)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                lease, error = None, f"unreadable lease: {exc}"
            if error:
                item.update(state="invalid", error=error)
            else:
                assert lease is not None
                expires = datetime.fromisoformat(str(lease["expires_at"]).replace("Z", "+00:00"))
                item.update(owner=lease.get("owner"), task=lease.get("task"), expires_at=lease["expires_at"], state="active" if expires > timestamp else "expired")
        else:
            item["state"] = "unmanaged-locked" if record.get("locked") else "unmanaged"
        output.append(item)
    print(json.dumps(output, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("acquire", "heartbeat"):
        command = commands.add_parser(name)
        command.add_argument("--path", default=".")
        command.add_argument("--owner", required=True)
        command.add_argument("--ttl-hours", type=int, default=24)
        if name == "acquire":
            command.add_argument("--task", required=True)
        command.set_defaults(handler=acquire if name == "acquire" else heartbeat)
    command = commands.add_parser("audit")
    command.add_argument("--path", default=".")
    command.set_defaults(handler=audit)
    return result


def main() -> int:
    args = parser().parse_args()
    if getattr(args, "ttl_hours", 1) <= 0:
        raise SystemExit("ttl-hours must be positive")
    args.handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
