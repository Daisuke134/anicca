#!/usr/bin/env python3
"""Build the public AI/Mac skill inventory used for a first Storefront listing."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
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


def select_capability(
    value: dict[str, Any], *, runner: Path, schema: Path,
    evidence_dir: Path, workdir: Path, timeout_seconds: int = 180,
) -> dict[str, Any]:
    prompt = """Choose the single strongest first Coconala service from CAPABILITY_INVENTORY and
return only the strict schema object. The AI/Mac/tool system is the delivery workforce: never use
the account owner's personal labor, experience, health, time, identity, credentials, or external
authority as a capability. Select only an outcome that this installed skill can produce and verify
from buyer-supplied inputs. Prefer clear recurring business value, low marginal compute/tool cost,
bounded scope, objective quality checks, and low refund/deadline risk. service_query is a natural
Japanese phrase suitable for checking official Coconala demand, not listing copy. Do not select
trading, account creation, outreach, marketplace operation, regulated advice, physical work, or a
skill that merely orchestrates another money loop. If no listed skill supports an honest standalone
buyer deliverable, choose no_op and set skill_path/service_query/outcome/deliverable/inputs to null.
CAPABILITY_INVENTORY=""" + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    completed = subprocess.run([
        sys.executable, str(runner), "--task-class", "storefront-proposal-agent",
        "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
        "--task-label", "gig-storefront-bootstrap-select", "--loop", "gig-storefront",
        "--workdir", str(workdir), "--timeout-seconds", str(timeout_seconds),
    ], input=prompt, text=True, capture_output=True, timeout=timeout_seconds + 30, check=False)
    if completed.returncode != 0:
        raise RuntimeError("storefront_bootstrap_selection_failed")
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    result_path = Path(str(summary.get("result_path") or "")).resolve(strict=True)
    result_path.relative_to(evidence_dir.resolve())
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if summary.get("status") != "success" or min(
        (evidence_dir / "summary.json").stat().st_mtime, result_path.stat().st_mtime
    ) < started:
        raise RuntimeError("storefront_bootstrap_selection_stale")
    nullable = ("skill_path", "service_query", "buyer_outcome", "deliverable", "required_buyer_inputs")
    if result.get("decision") == "no_op":
        if any(result.get(key) is not None for key in nullable) or not result.get("no_op_reason"):
            raise RuntimeError("storefront_bootstrap_noop_invalid")
        return result
    known = {row["skill_path"] for row in value["skills"]}
    if (result.get("decision") != "sell" or result.get("skill_path") not in known
            or not all(result.get(key) for key in nullable)
            or result.get("no_op_reason") is not None):
        raise RuntimeError("storefront_bootstrap_selection_invalid")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "select"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    args = parser.parse_args()
    if args.command == "inventory":
        value = inventory()
        summary = {"status": "ready", "skills": len(value["skills"]),
                   "inventory_sha256": value["inventory_sha256"]}
    else:
        if not all((args.inventory, args.runner, args.schema, args.evidence_dir)):
            parser.error("select requires --inventory --runner --schema --evidence-dir")
        value = json.loads(args.inventory.read_text(encoding="utf-8"))
        result = select_capability(
            value, runner=args.runner, schema=args.schema,
            evidence_dir=args.evidence_dir, workdir=args.workdir,
        )
        value = result
        summary = {"status": "ready", "decision": result["decision"],
                   "skill_path": result.get("skill_path")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
