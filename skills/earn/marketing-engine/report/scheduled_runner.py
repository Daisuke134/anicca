#!/usr/bin/env python3
"""Canonical entrypoint for the eight Gate 6 runner lanes."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import run_contract
import run_with_contract


HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
REGISTRY_PATH = HERE / "runners.json"


def load_registry(path: pathlib.Path = REGISTRY_PATH) -> dict[str, dict]:
    body = json.loads(pathlib.Path(path).read_text())
    if body.get("schema_version") != "marketing.runners.v1":
        raise run_contract.ContractError("unsupported runner registry schema")
    runners = body.get("runners")
    if not isinstance(runners, dict) or set(runners) != set(run_contract.RUNNERS):
        raise run_contract.ContractError("runner registry must contain exactly the eight lanes")
    for runner_id, item in runners.items():
        if not isinstance(item.get("command"), list) or not item["command"]:
            raise run_contract.ContractError(f"{runner_id} command is required")
        if not isinstance(item.get("product_ids"), list):
            raise run_contract.ContractError(f"{runner_id} product_ids must be an array")
        reason = item.get("quarantine_reason")
        if reason is not None and (not isinstance(reason, str) or not reason):
            raise run_contract.ContractError(f"{runner_id} quarantine_reason is invalid")
    return runners


def resolve_command(command: list[str]) -> list[str]:
    values = {
        "repo": str(REPO_ROOT),
        "home": str(pathlib.Path.home()),
        "python": sys.executable,
    }
    return [part.format(**values) for part in command]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner", choices=sorted(run_contract.RUNNERS))
    parser.add_argument("--state-root", type=pathlib.Path,
                        default=HERE.parent / "state")
    parser.add_argument("--evidence-root", type=pathlib.Path,
                        default=HERE.parent / "evidence" / "runs")
    parser.add_argument("--no-send", action="store_true")
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args(argv)
    try:
        item = load_registry()[args.runner]
        result = run_with_contract.execute(
            runner_id=args.runner,
            command=resolve_command(item["command"]),
            state_root=args.state_root,
            evidence_root=args.evidence_root,
            environment="production",
            dry_run=False,
            product_ids=item["product_ids"],
            quarantine_reason=item["quarantine_reason"],
            send=not args.no_send,
            timeout=args.timeout,
        )
    except (OSError, json.JSONDecodeError, run_contract.ContractError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1
    print(json.dumps({
        "runner_id": result.event["runner_id"],
        "run_id": result.event["run_id"],
        "status": result.event["status"],
        "returncode": result.returncode,
        "delivery": result.delivery,
    }, ensure_ascii=False, sort_keys=True))
    return result.returncode if result.event["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
