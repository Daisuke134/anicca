#!/usr/bin/env python3
"""Persist an already-applied live OpenClaw quarantine into its stale JSON store."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def persist(snapshot: dict[str, Any], backup: Path, apply: bool) -> dict[str, Any]:
    targets = [
        row for row in snapshot.get("records", [])
        if row.get("runtime") == "openclaw"
        and row.get("disposition") == "retire"
        and row.get("enabled") is True
    ]
    paths = {row.get("source_path") for row in targets}
    hashes = {row.get("source_sha256") for row in targets}
    if len(paths) != 1 or len(hashes) != 1:
        raise ValueError("OpenClaw targets must share one reviewed store and hash")
    store = Path(paths.pop())
    before = store.read_bytes()
    expected = hashes.pop()
    if digest(before) != expected:
        raise ValueError("OpenClaw store changed since reviewed inventory")
    document = json.loads(before)
    target_ids = {str(row["id"]) for row in targets}
    found: set[str] = set()
    changed: list[str] = []
    for job in document.get("jobs", []):
        identifier = str(job.get("id"))
        if identifier in target_ids:
            found.add(identifier)
            if job.get("enabled") is not False:
                job["enabled"] = False
                changed.append(identifier)
    missing = sorted(target_ids - found)
    if missing:
        raise ValueError(f"reviewed OpenClaw target missing from store: {missing}")
    encoded = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
    evidence = {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "apply" if apply else "dry_run",
        "store_path": str(store),
        "backup_path": str(backup),
        "before_sha256": digest(before),
        "after_sha256": digest(encoded),
        "target_count": len(target_ids),
        "changed_ids": sorted(changed),
        "status": "planned" if not apply else "persisted",
    }
    if apply:
        if backup.exists():
            raise ValueError(f"refusing to overwrite backup: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(store, backup)
        atomic_write(store, encoded)
    return evidence


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--snapshot", type=Path, required=True)
    result.add_argument("--backup", type=Path, required=True)
    result.add_argument("--evidence", type=Path)
    result.add_argument("--apply", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = persist(json.loads(args.snapshot.read_text()), args.backup, args.apply)
    if args.evidence:
        atomic_write(args.evidence, (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({"status": result["status"], "targets": result["target_count"], "changed": len(result["changed_ids"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
