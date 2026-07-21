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
ALLOWED_CLASSES = PROTECTED_CLASSES | {"ephemeral"}
TX_RE = re.compile(r"^[0-9a-f]{32}$")


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
    if not isinstance(finalizer, dict) or set(finalizer) != {"kind"}:
        raise ManifestError(f"artifact {raw['id']} finalizer schema is invalid")
    expected_finalizer = "off_volume_quarantine" if artifact_class == "ephemeral" else "preserve"
    if finalizer["kind"] != expected_finalizer:
        raise ManifestError(
            f"artifact {raw['id']} class {artifact_class} requires {expected_finalizer} finalizer"
        )
    return {
        "id": raw["id"],
        "path": str(path),
        "owner": raw["owner"],
        "class": artifact_class,
        "ttl_seconds": ttl,
        "quota_bytes": quota,
        "lease": lease,
        "finalizer": {"kind": expected_finalizer},
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
        return False, 0, "quarantine_unavailable"
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
) -> dict[str, int | str]:
    now = int(time.time()) if now is None else int(now)
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
        if entry["class"] != "ephemeral":
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
                if newest > now - entry["ttl_seconds"]:
                    reason = "ttl_not_expired"
                elif size <= entry["quota_bytes"]:
                    reason = "within_quota"
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
        if reason.startswith(("quarantine_", "artifact_unreadable:")):
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
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "ok" and result["errors"] == 0 else 3
    result = restore(
        transaction_id=args.transaction_id,
        quarantine_root=args.quarantine_root,
        ledger_path=args.ledger,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "restored" else 4


if __name__ == "__main__":
    sys.exit(main())
