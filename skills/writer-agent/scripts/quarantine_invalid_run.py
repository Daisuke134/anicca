#!/usr/bin/env python3
"""Record a proof-bound quarantine for a non-publishable immutable run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from publication_contract import ACTIVE_PAIRS


RUN_ID_RE = re.compile(r"(?:daily-\d{4}-\d{2}-\d{2}|\d{8}-\d{6})\Z")
RECEIPT_NAME = "run-quarantine.json"


class QuarantineError(ValueError):
    pass


def _present(value: Any) -> bool:
    return value not in (None, "", {}, [])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def _read_json(path: Path) -> dict[str, Any]:
    if not _regular(path):
        raise QuarantineError(f"missing or non-regular JSON: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError) as error:
        raise QuarantineError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise QuarantineError(f"JSON object required: {path}")
    return value


def _ledger_has_live(ledger_path: Path, run_id: str) -> bool:
    if not ledger_path.exists():
        return False
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise QuarantineError("ledger is unreadable") from error
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError) as error:
            raise QuarantineError("ledger contains malformed JSON") from error
        if not isinstance(row, dict) or row.get("run_id") != run_id:
            continue
        if row.get("published") is True or row.get("state") == "live":
            return True
        if any(_present(row.get(key)) for key in ("live_url", "public_id", "receipt", "published_at", "effect", "readback")):
            return True
    return False


def proof(state_root: Path, run_id: str) -> dict[str, Any]:
    if not RUN_ID_RE.fullmatch(run_id):
        raise QuarantineError("invalid run id")
    root = state_root.resolve(strict=True)
    raw_run_dir = root / "runs" / run_id
    if raw_run_dir.is_symlink() or not raw_run_dir.is_dir():
        raise QuarantineError("run is missing or symlinked")
    run_dir = raw_run_dir.resolve(strict=True)
    if run_dir.parent != root / "runs" or not run_dir.is_dir():
        raise QuarantineError("run is outside the state root")
    gates = run_dir / "gates"
    if gates.is_symlink() or not gates.is_dir() or gates.resolve(strict=True).parent != run_dir:
        raise QuarantineError("gates directory is missing or symlinked")
    state_path = gates / "publication-state.json"
    state = _read_json(state_path)
    if state.get("run_id") != run_id or state.get("publication_contract") != "active-four":
        raise QuarantineError("only active-four state for the same run may be quarantined")
    if state.get("run_dir") != str(run_dir):
        raise QuarantineError("state run directory mismatch")
    ledger_path = root / "articles.jsonl"
    if state.get("state_path") != str(state_path) or state.get("ledger_path") != str(ledger_path):
        raise QuarantineError("state or ledger path mismatch")
    if not _regular(ledger_path):
        raise QuarantineError("ledger is missing or symlinked")
    if _ledger_has_live(ledger_path, run_id):
        raise QuarantineError("run already has a live ledger receipt")
    pairs = state.get("pairs")
    if not isinstance(pairs, dict) or any(not isinstance(pair, dict) for pair in pairs.values()):
        raise QuarantineError("publication pairs are malformed")
    if not set(ACTIVE_PAIRS).issubset(pairs):
        raise QuarantineError("active publication pairs are missing")
    for pair in pairs.values():
        if pair.get("status") not in {"unavailable", "skipped"}:
            raise QuarantineError("publication pair is not explicitly non-live")
        if pair.get("status") == "live" or pair.get("published") is True:
            raise QuarantineError("run has a live publication pair")
        if any(_present(pair.get(key)) for key in ("live_url", "public_id", "receipt", "published_at", "effect", "readback", "existing_publication")):
            raise QuarantineError("publication pair has effect evidence")
    media = state.get("media")
    headline = Path(str(media.get("headline_image", {}).get("path", ""))) if isinstance(media, dict) else Path("")
    bodies = media.get("body_assets") if isinstance(media, dict) else None
    if not _regular(headline) or not isinstance(bodies, list) or not bodies:
        raise QuarantineError("canonical media proof is missing")
    if headline.resolve(strict=True).parent != run_dir:
        raise QuarantineError("headline media is outside run boundary")
    headline_sha = _sha256(headline)
    body_paths: list[str] = []
    body_shas: list[str] = []
    for item in bodies:
        if not isinstance(item, dict):
            raise QuarantineError("body media receipt is malformed")
        body = Path(str(item.get("path", "")))
        if not _regular(body) or body.resolve(strict=True).parent != run_dir:
            raise QuarantineError("body media is outside run boundary")
        body_sha = _sha256(body)
        body_paths.append(str(body.resolve(strict=True)))
        body_shas.append(body_sha)
    if headline_sha not in body_shas:
        raise QuarantineError("duplicate headline/body media proof is absent")
    return {
        "version": 1,
        "type": "run-quarantine",
        "reason": "duplicate-media",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "state_sha256": _sha256(state_path),
        "headline_sha256": headline_sha,
        "body_sha256": body_shas,
        "body_paths": body_paths,
    }


def receipt_is_valid(run_dir: Path, run_id: str) -> bool:
    receipt_path = run_dir / "gates" / RECEIPT_NAME
    try:
        stored = _read_json(receipt_path)
        root = run_dir.parent.parent
        expected = proof(root, run_id)
    except (OSError, QuarantineError):
        return False
    return stored == expected


def quarantine(state_root: Path, run_id: str) -> dict[str, Any]:
    expected = proof(state_root, run_id)
    receipt_path = state_root.resolve(strict=True) / "runs" / run_id / "gates" / RECEIPT_NAME
    gates = receipt_path.parent
    if gates.is_symlink() or not gates.is_dir() or gates.resolve(strict=True).parent != receipt_path.parent.parent:
        raise QuarantineError("gates directory changed during quarantine")
    if receipt_path.exists():
        if receipt_is_valid(receipt_path.parent.parent, run_id):
            return _read_json(receipt_path)
        raise QuarantineError("existing quarantine receipt conflicts with proof")
    receipt = expected
    fd, temporary = tempfile.mkstemp(prefix=f".{RECEIPT_NAME}.", dir=str(receipt_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, receipt_path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = quarantine(args.state_root, args.run_id)
    except (OSError, QuarantineError) as error:
        print(f"REFUSED: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
