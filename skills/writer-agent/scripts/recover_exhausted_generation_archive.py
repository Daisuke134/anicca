#!/usr/bin/env python3
"""Recover a hash-bound generation-state copy after a completed archive.

This is deliberately narrower than a resume operation: it only copies the
exact interrupted-safe state line emitted by article-daily into its immutable
archive after checking every manifest byte and proving that no public ledger
row or publication-state exists.  It never restores the prompt or run files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "writer.generation-exhaustion-receipt"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_sha256(manifest: list[dict[str, str]]) -> str:
    return hashlib.sha256(
        json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.recover-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _latest_state(log: Path, run_id: str) -> dict[str, Any]:
    found: dict[str, Any] | None = None
    for line in log.read_text(encoding="utf-8", errors="strict").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(value, dict)
            and value.get("run_id") == run_id
            and value.get("status") == "interrupted-safe"
            and isinstance(value.get("attempts"), list)
        ):
            found = value
    if found is None:
        raise ValueError("no interrupted-safe generation state in log")
    return found


def _public_rows(ledger: Path, run_id: str) -> int:
    count = 0
    if not ledger.is_file() or ledger.is_symlink():
        return count
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get("run_id") != run_id:
            continue
        if (
            row.get("published") is True
            or row.get("draft_url")
            or row.get("live_url")
            or row.get("state") == "live"
            or row.get("reality_gate") == "PASS"
        ):
            count += 1
    return count


def recover(state_dir: Path, run_id: str, log: Path, ledger: Path) -> dict[str, Any]:
    state = _latest_state(log, run_id)
    attempts = state["attempts"]
    final = attempts[-1]
    if (
        state.get("version") != 1
        or not isinstance(state.get("prompt_sha256"), str)
        or state.get("maximum_attempts") != 3
        or state.get("status") != "interrupted-safe"
        or final.get("status") != "interrupted-safe"
        or final.get("return_code") not in {124, 130, 143}
        or not isinstance(final.get("archive_manifest"), list)
    ):
        raise ValueError("generation state is not an exhausted safe archive")
    empty = sum(
        1 for item in attempts
        if isinstance(item, dict)
        and item.get("status") == "interrupted-safe"
        and item.get("archive_manifest") == []
    )
    charged = len(attempts) - min(empty, 1)
    if charged < int(state["maximum_attempts"]):
        raise ValueError("generation attempt budget is not exhausted")
    if _public_rows(ledger, run_id):
        raise ValueError("public ledger row exists")
    archive_root = Path(str(final.get("archive_root", ""))).resolve()
    expected_parent = (state_dir / "interrupted-generation" / run_id).resolve()
    if (
        archive_root.parent != expected_parent
        or archive_root.name != f"attempt-{final.get('attempt')}"
        or archive_root.is_symlink()
        or not archive_root.is_dir()
    ):
        raise ValueError("archive root is outside the run boundary")
    manifest = final["archive_manifest"]
    for item in manifest:
        relative = Path(str(item.get("path", "")))
        target = archive_root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or target.is_symlink()
            or not target.is_file()
            or item.get("sha256") != _sha256(target)
        ):
            raise ValueError(f"archive manifest mismatch: {relative}")
    if any(
        path.name == "publication-state.json"
        for path in archive_root.rglob("*")
        if path.is_file() or path.is_symlink()
    ):
        raise ValueError("publication state exists in archive")
    state_path = archive_root / "generation-state.json"
    _atomic_json(state_path, state)
    receipt = {
        "schema": SCHEMA,
        "version": 1,
        "run_id": run_id,
        "attempt": final.get("attempt"),
        "status": "interrupted-safe",
        "return_code": final.get("return_code"),
        "charged_attempts": charged,
        "maximum_attempts": int(state["maximum_attempts"]),
        "state_sha256": _sha256(state_path),
        "archive_manifest_sha256": _manifest_sha256(manifest),
        "publication_state_absent": True,
        "public_ledger_rows": 0,
    }
    _atomic_json(archive_root / "generation-exhaustion-receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(recover(args.state_dir, args.run_id, args.log, args.ledger), sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"REFUSED: {error}")
        return 75
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
