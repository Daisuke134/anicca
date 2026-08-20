#!/usr/bin/env python3
"""Move mutable publication-control paths to the canonical Writer Agent root."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


VERSION = 1


class PathMigrationError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _replace(value: Any, old: str, new: str) -> tuple[Any, int]:
    if isinstance(value, str):
        if value == old or value.startswith(old + os.sep):
            return new + value[len(old) :], 1
        return value, 0
    if isinstance(value, list):
        result: list[Any] = []
        count = 0
        for item in value:
            migrated, replacements = _replace(item, old, new)
            result.append(migrated)
            count += replacements
        return result, count
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        count = 0
        for key, item in value.items():
            migrated, replacements = _replace(item, old, new)
            result[key] = migrated
            count += replacements
        return result, count
    return value, 0


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _control_paths(state_root: Path) -> list[Path]:
    paths: list[Path] = []
    for gates in sorted((state_root / "runs").glob("*/gates")):
        # Every gate receipt can carry an absolute artifact/state path.  The
        # first migration only covered publication-state.json and left
        # media-create receipts pointing at the retired root, so the next
        # managed boundary rejected an otherwise intact run.  Keep the scope
        # to regular JSON receipts under the canonical run gates; raw logs and
        # article bytes are intentionally untouched.
        paths.extend(
            path
            for path in sorted(gates.iterdir())
            if path.is_file()
            and (path.name.endswith(".json") or path.name == "publication-state.json.bak")
        )
    return paths


def migrate_publication_states(
    *,
    state_root: Path,
    legacy_root: Path,
    canonical_root: Path,
    receipt_path: Path,
    migrated_at: str,
) -> dict[str, Any]:
    state_root = Path(state_root).absolute()
    legacy = str(Path(legacy_root).absolute())
    canonical = str(Path(canonical_root).absolute())
    receipt_path = Path(receipt_path).absolute()
    if legacy == canonical:
        raise PathMigrationError("legacy and canonical roots must differ")
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("version") != VERSION
            or receipt.get("legacy_root") != legacy
            or receipt.get("canonical_root") != canonical
        ):
            raise PathMigrationError("existing path-migration receipt conflicts")
        for path in _control_paths(state_root):
            if legacy in path.read_text(encoding="utf-8"):
                raise PathMigrationError(
                    "legacy path reappeared after completed migration"
                )
        return receipt

    prepared: list[tuple[Path, bytes, bytes, int]] = []
    for path in _control_paths(state_root):
        before = path.read_bytes()
        try:
            value = json.loads(before)
        except json.JSONDecodeError as error:
            raise PathMigrationError(f"invalid publication control: {path}") from error
        migrated, replacements = _replace(value, legacy, canonical)
        if replacements == 0:
            continue
        after = (
            json.dumps(
                migrated,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        prepared.append((path, before, after, replacements))

    files = [
        {
            "path": str(path),
            "before_sha256": _sha256(before),
            "after_sha256": _sha256(after),
            "replacements": replacements,
        }
        for path, before, after, replacements in prepared
    ]
    receipt = {
        "version": VERSION,
        "migrated_at": migrated_at,
        "legacy_root": legacy,
        "canonical_root": canonical,
        "migrated": len(files),
        "replacements": sum(item["replacements"] for item in files),
        "files": files,
    }
    for path, _before, after, _replacements in prepared:
        _atomic_write(path, after)
    _atomic_write(
        receipt_path,
        (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--canonical-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise PathMigrationError("--apply is required")
    if (
        not args.legacy_root.exists()
        or not args.canonical_root.is_dir()
        or args.legacy_root.resolve() != args.canonical_root.resolve()
    ):
        raise PathMigrationError(
            "legacy root must be a live alias of the canonical root"
        )
    result = migrate_publication_states(
        state_root=args.state_root,
        legacy_root=args.legacy_root,
        canonical_root=args.canonical_root,
        receipt_path=args.receipt,
        migrated_at=datetime.now(timezone.utc).isoformat(),
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, PathMigrationError) as error:
        print(f"REFUSED: {error}", file=os.sys.stderr)
        raise SystemExit(2)
