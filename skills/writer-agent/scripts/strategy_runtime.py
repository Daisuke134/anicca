#!/usr/bin/env python3
"""Consume every active strategy version before a Writer generation starts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def consume_active_versions(
    *,
    run_id: str,
    active_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Verify active pointers against bytes and persist the run input hash."""

    if not run_id:
        raise ValueError("run_id is required")
    active_dir = Path(active_dir)
    versions: list[dict[str, Any]] = []
    manifests = sorted(active_dir.glob("*.json")) if active_dir.is_dir() else []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {
            "version_id",
            "status",
            "learning_cycle_id",
            "slice",
            "weight_file",
            "weight_hash",
        }
        if set(manifest) != required or manifest.get("status") != "active":
            raise ValueError(f"invalid active strategy manifest: {manifest_path}")
        weights_path = Path(manifest["weight_file"])
        if not weights_path.is_file():
            raise ValueError(f"active strategy weight file missing: {weights_path}")
        consumed_hash = _sha256(weights_path)
        if (
            consumed_hash != manifest["weight_hash"]
            or consumed_hash != manifest["version_id"]
        ):
            raise ValueError(
                f"active strategy hash drift: {manifest_path.name}"
            )
        versions.append(
            {
                "slice": manifest["slice"],
                "active_version_id": manifest["version_id"],
                "learning_cycle_id": manifest["learning_cycle_id"],
                "weight_file": weights_path.as_posix(),
                "consumed_hash": consumed_hash,
            }
        )

    receipt = {
        "run_id": run_id,
        "status": "consumed" if versions else "baseline",
        "versions": versions,
    }
    _write_json(Path(output_path), receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    consume = subparsers.add_parser("consume-active")
    consume.add_argument("--run-id", required=True)
    consume.add_argument("--active-dir", required=True, type=Path)
    consume.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    result = consume_active_versions(
        run_id=args.run_id,
        active_dir=args.active_dir,
        output_path=args.out,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
