#!/usr/bin/env python3
"""Seed tracked topic cards into gitignored operational state exactly once."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = ("queue", "in-progress", "done")


class TopicStateError(ValueError):
    """Tracked seeds or operational topic state conflict."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    with source.open("rb") as reader, temporary.open("wb") as writer:
        writer.write(reader.read())
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(temporary, destination)


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        value = {}
    cards = value.get("cards") if isinstance(value, dict) else {}
    return {
        "version": 1,
        "cards": cards if isinstance(cards, dict) else {},
    }


def initialize(skill_dir: Path) -> dict[str, Any]:
    skill_dir = Path(skill_dir).resolve(strict=True)
    source_root = skill_dir / "topics"
    runtime_root = skill_dir / "state/topics"
    manifest_path = runtime_root / "seed-manifest.json"
    lock_path = runtime_root / ".seed.lock"
    for stage in STAGES:
        (runtime_root / stage).mkdir(parents=True, exist_ok=True)
    imported: list[str] = []
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        manifest = _load_manifest(manifest_path)
        for stage in STAGES:
            source_dir = source_root / stage
            for source in sorted(source_dir.glob("*.md")):
                if source.name == ".gitkeep":
                    continue
                digest = _sha256(source)
                recorded = manifest["cards"].get(source.name)
                if isinstance(recorded, dict):
                    if recorded.get("sha256") != digest:
                        raise TopicStateError(
                            f"tracked topic seed changed after import: {source.name}"
                        )
                    continue
                existing = [
                    runtime_root / candidate / source.name
                    for candidate in STAGES
                    if (runtime_root / candidate / source.name).exists()
                ]
                if len(existing) > 1:
                    raise TopicStateError(
                        f"runtime topic exists in multiple stages: {source.name}"
                    )
                if existing:
                    if _sha256(existing[0]) != digest:
                        raise TopicStateError(
                            f"runtime topic conflicts with tracked seed: {source.name}"
                        )
                    destination_stage = existing[0].parent.name
                else:
                    destination_stage = stage
                    _atomic_copy(source, runtime_root / stage / source.name)
                    imported.append(f"{stage}/{source.name}")
                manifest["cards"][source.name] = {
                    "sha256": digest,
                    "source_stage": stage,
                    "initial_runtime_stage": destination_stage,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
        _atomic_json(manifest_path, manifest)
    return {
        "runtime_root": str(runtime_root),
        "imported": imported,
        "tracked_cards": len(manifest["cards"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=Path.home() / "profitable-claude/skills/article-writer",
    )
    args = parser.parse_args()
    print(json.dumps(initialize(args.skill_dir), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
