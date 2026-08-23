#!/usr/bin/env python3
"""Fail-closed readback for one user-reviewed Capafy creative."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(state_path: Path, agent_id: str, artifact_root: Path) -> dict:
    if not state_path.exists():
        return {"status": "none"}
    row = json.loads(state_path.read_text(encoding="utf-8"))
    if str(row.get("agent_id") or "") != agent_id:
        return {"status": "none"}
    status = str(row.get("status") or "")
    if status not in {"pending", "approved"}:
        raise ValueError("approval status must be pending or approved")
    artifact = Path(str(row.get("artifact_path") or "")).expanduser().resolve()
    root = artifact_root.expanduser().resolve()
    if root not in artifact.parents or not artifact.is_file():
        raise ValueError("approval artifact is outside the artifact root or missing")
    expected = str(row.get("artifact_sha256") or "")
    actual = sha256(artifact)
    if len(expected) != 64 or actual != expected:
        raise ValueError("approval artifact hash mismatch")
    if not str(row.get("review_message_id") or "").strip():
        raise ValueError("review message id is missing")
    return {
        "status": status,
        "agent_id": agent_id,
        "artifact_path": str(artifact),
        "artifact_sha256": actual,
        "review_message_id": str(row["review_message_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(args.state, args.agent_id, args.artifact_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
