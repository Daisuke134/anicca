#!/usr/bin/env python3
"""Deterministic, crash-safe producers for receipted Sol audit triggers."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


STATE_VERSION = 1
SAMPLE_ORDINALS = (5, 10, 15, 20, 25, 30)


class TriggerInvariant(ValueError):
    """A persisted trigger boundary is malformed or conflicts with this call."""


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": STATE_VERSION, "runs": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != STATE_VERSION
        or not isinstance(payload.get("runs"), list)
    ):
        raise TriggerInvariant("invalid quality-sample state")
    seen: set[str] = set()
    for expected_ordinal, row in enumerate(payload["runs"], start=1):
        if not isinstance(row, dict):
            raise TriggerInvariant("invalid quality-sample run row")
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in seen:
            raise TriggerInvariant("invalid or duplicate quality-sample run identity")
        if row.get("ordinal") != expected_ordinal:
            raise TriggerInvariant("quality-sample ordinals are not contiguous")
        seen.add(run_id)
    return payload


def expected_language(ordinal: int) -> str | None:
    if ordinal not in SAMPLE_ORDINALS:
        return None
    return "ja" if SAMPLE_ORDINALS.index(ordinal) % 2 == 0 else "en"


def file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise TriggerInvariant("article is missing or symlinked")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quality_sample(args: argparse.Namespace) -> dict[str, Any]:
    state_path = Path(args.state).resolve()
    receipt_path = Path(args.receipt).resolve()
    article_path = Path(args.article).resolve()
    if not args.run_id.strip() or not args.artifact_id.strip():
        raise TriggerInvariant("run and artifact identities are required")

    lock_path = state_path.with_name(f".{state_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = load_state(state_path)
        row = next((item for item in state["runs"] if item["run_id"] == args.run_id), None)
        if row is None:
            row = {"run_id": args.run_id, "ordinal": len(state["runs"]) + 1}
            state["runs"].append(row)
            atomic_write(state_path, state)

        ordinal = int(row["ordinal"])
        language = expected_language(ordinal)
        common = {
            "ordinal": ordinal,
            "expected_language": language,
            "receipt_path": str(receipt_path),
        }
        if language is None:
            return {"status": "NOT_SAMPLED", **common}
        if args.language != language:
            return {"status": "LANGUAGE_PENDING", **common}

        article_hash = file_sha256(article_path)
        receipt = {
            "schema_version": 1,
            "trigger": "quality_sample",
            "run_id": args.run_id,
            "artifact_id": args.artifact_id,
            "article_sha256": article_hash,
            "requested_reasoning_effort": "medium",
        }
        binding = {
            "artifact_id": args.artifact_id,
            "article_sha256": article_hash,
            "language": args.language,
            "receipt_path": str(receipt_path),
        }
        existing_binding = row.get("receipt_binding")
        if existing_binding is not None and existing_binding != binding:
            return {
                "status": "ALREADY_BOUND",
                **common,
                "bound_article_sha256": existing_binding.get("article_sha256"),
                "bound_receipt_path": existing_binding.get("receipt_path"),
            }
        if receipt_path.exists():
            existing_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if existing_receipt != receipt:
                raise TriggerInvariant("existing quality-sample receipt conflicts")
        else:
            atomic_write(receipt_path, receipt)
        if existing_binding is None:
            row["receipt_binding"] = binding
            atomic_write(state_path, state)
        return {"status": "RECEIPT_READY", **common}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("quality-sample")
    sample.add_argument("--state", required=True)
    sample.add_argument("--run-id", required=True)
    sample.add_argument("--artifact-id", required=True)
    sample.add_argument("--article", required=True)
    sample.add_argument("--language", required=True, choices=("ja", "en"))
    sample.add_argument("--receipt", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        result = quality_sample(args)
    except (TriggerInvariant, json.JSONDecodeError, OSError) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}), file=sys.stderr)
        return 64
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
