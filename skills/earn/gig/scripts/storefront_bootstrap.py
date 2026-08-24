#!/usr/bin/env python3
"""Build the public AI/Mac skill inventory used for a first Storefront listing."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
SKILLS = REPO / "skills"
REGISTRY = SKILLS / "registry.json"


def _frontmatter(source: str) -> dict[str, str]:
    if not source.startswith("---\n"):
        return {}
    end = source.find("\n---", 4)
    if end < 0:
        return {}
    rows: dict[str, str] = {}
    lines = source[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line or line[:1].isspace():
            index += 1
            continue
        key, raw = line.split(":", 1)
        value = raw.strip().strip("'\"")
        if value in {"|", ">", "|-", ">-"}:
            continuation = []
            index += 1
            while index < len(lines) and lines[index][:1].isspace():
                continuation.append(lines[index].strip())
                index += 1
            value = " ".join(continuation)
        else:
            index += 1
        rows[key.strip()] = value
    return rows


def inventory(repo: Path = REPO) -> dict[str, Any]:
    skills = repo / "skills"
    registry_path = skills / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    live = {
        str(row.get("dir")): name
        for name, row in registry.get("slots", {}).items()
        if isinstance(row, dict) and row.get("status") == "live" and row.get("dir")
    }
    rows = []
    for path in sorted(skills.glob("**/SKILL.md")):
        source = path.read_text(encoding="utf-8")
        meta = _frontmatter(source)
        name = str(meta.get("name") or path.parent.name).strip()
        description = " ".join(str(meta.get("description") or "").split())[:1000]
        if not name or not description:
            continue
        relative_dir = path.parent.relative_to(repo).as_posix()
        rows.append({
            "name": name,
            "description": description,
            "skill_path": path.relative_to(repo).as_posix(),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "runtime": "live_adapter" if relative_dir in live else "agent_skill",
            "slot": live.get(relative_dir),
        })
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": 1,
        "source": "public_repo_skills",
        "skills": rows,
        "inventory_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ready", "skills": len(value["skills"]),
        "inventory_sha256": value["inventory_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
