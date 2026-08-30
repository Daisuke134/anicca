#!/usr/bin/env python3
"""Build confirmed publish-init selections from one Phase A discovery result."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import sys


def _fail(message: str) -> int:
    print(f"build_publish_selection: {message}", file=sys.stderr)
    return 1


def _absolute_path(value: object) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        path = Path(raw).expanduser()
    except (OSError, ValueError):
        return None
    if not path.is_absolute():
        return None
    return path.resolve(strict=False)


def _logical_path(value: object) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or (len(raw) > 1 and raw[1] == ":") or any(part in {"", ".", ".."} for part in PurePosixPath(raw).parts):
        return ""
    return PurePosixPath(raw).as_posix()


def _write_atomic(path: Path, payload: dict) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(parent, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-id", default="")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(sys.stdin.read(), strict=False)
    except json.JSONDecodeError as exc:
        return _fail(f"Phase A response is invalid JSON: {exc}")
    if not isinstance(payload, dict):
        return _fail("Phase A response must be an object")
    if payload.get("status") != "needs_selection" or payload.get("action_type") != "llm_selection":
        return _fail("Phase A response is not a selection discovery")
    skill_root = _absolute_path(args.skill_dir)
    if skill_root is None or not skill_root.is_dir() or not (skill_root / "SKILL.md").is_file():
        return _fail("explicit skill directory is not a valid skill root")
    candidates = payload.get("skills")
    if not isinstance(candidates, list):
        return _fail("Phase A response has no skills array")

    matches: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return _fail("Phase A skills array contains a non-object")
        candidate_paths = {
            path
            for path in (
                _absolute_path(candidate.get("source_path")),
                _absolute_path(candidate.get("source_root")),
            )
            if path is not None
        }
        if skill_root not in candidate_paths:
            continue
        logical = _logical_path(candidate.get("path"))
        name = str(candidate.get("name") or "").strip()
        if not logical or not name:
            return _fail("matching Phase A skill candidate has invalid path or metadata name")
        purpose = str(candidate.get("purpose") or candidate.get("description") or name).strip()
        if not purpose:
            return _fail("matching Phase A skill candidate has no purpose")
        matches.append({"path": logical, "name": name, "purpose": purpose})

    if len(matches) != 1:
        return _fail("explicit skill does not map to exactly one Phase A candidate")
    selections = {
        "title": str(args.title).strip(),
        "description": str(args.title).strip(),
        "skills": [matches[0]],
    }
    if not selections["title"]:
        return _fail("title must not be empty")
    agent_id = str(args.agent_id or "").strip()
    if agent_id:
        selections["agent_id"] = agent_id
    try:
        output = Path(args.output).expanduser()
        _write_atomic(output, selections)
    except (OSError, ValueError) as exc:
        return _fail(f"could not write confirmed selections: {exc}")
    print(f"SELECTION_FILE={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
