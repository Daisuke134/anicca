from __future__ import annotations

import argparse
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .agent_runner import AgentRunner
from .workday_discovery import discover_one
from .workday_qualification import fetch_official_description, qualify_one


def search_until_qualified(
    *,
    discover: Callable[[], dict[str, Any]],
    qualify: Callable[[], dict[str, Any]],
    max_candidates: int,
) -> dict[str, Any]:
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    discoveries = []
    decisions = []
    for _ in range(max_candidates):
        discovery = discover()
        discoveries.append(discovery)
        if discovery.get("status") == "no_fresh_workday":
            return {
                "status": "sources_exhausted",
                "discoveries": discoveries,
                "decisions": decisions,
            }
        decision = qualify()
        decisions.append(decision)
        if decision.get("decision") == "qualified":
            return {
                "status": "qualified",
                "discoveries": discoveries,
                "decisions": decisions,
            }
        if decision.get("status") == "no_pending_workday_fit":
            return {
                "status": "sources_exhausted",
                "discoveries": discoveries,
                "decisions": decisions,
            }
    return {
        "status": "budget_exhausted",
        "discoveries": discoveries,
        "decisions": decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--candidate-memory", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-candidates", type=int, default=8)
    args = parser.parse_args()
    runner = AgentRunner(evidence_root=args.evidence_root, runner_path=args.runner)
    result = search_until_qualified(
        discover=lambda: discover_one(ledger_path=args.ledger),
        qualify=lambda: qualify_one(
            ledger_path=args.ledger,
            candidate_memory_path=args.candidate_memory,
            fetch_description=fetch_official_description,
            run_model=lambda prompt: runner.run(
                task="improve",
                prompt=prompt,
                schema_path=args.schema,
                workdir=args.workdir,
                run_id=f"workday-fit-{uuid.uuid4().hex}",
            ),
        ),
        max_candidates=args.max_candidates,
    )
    result["discovered"] = [
        row
        for discovery in result["discoveries"]
        for row in discovery.get("discovered", [])
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
