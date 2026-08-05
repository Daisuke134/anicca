from __future__ import annotations

import hashlib
import json
import argparse
import os
from pathlib import Path
from typing import Any, Mapping


class ReplayError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def evaluate_route_replay(
    snapshot: Mapping[str, Any], route_results: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    if snapshot.get("version") != 1 or not isinstance(snapshot.get("cases"), list):
        raise ReplayError("snapshot must be a version-1 case set")
    if set(route_results) != {"luna", "terra"}:
        raise ReplayError("replay requires luna and terra results")
    snapshot_sha256 = _digest(snapshot)
    expected_cases = {case["case_id"]: case for case in snapshot["cases"]}
    quality: dict[str, float] = {}
    evidence_complete: dict[str, bool] = {}
    metrics: dict[str, dict[str, float]] = {}
    for route, payload in route_results.items():
        if payload.get("snapshot_sha256") != snapshot_sha256:
            raise ReplayError(f"{route} result does not match immutable snapshot")
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise ReplayError(f"{route} results must be an array")
        by_id = {
            row.get("case_id"): row for row in rows
            if isinstance(row, dict) and isinstance(row.get("case_id"), str)
        }
        earned = 0
        possible = 0
        route_evidence_complete = True
        for case_id, case in expected_cases.items():
            row = by_id.get(case_id, {})
            for field, expected in case.get("expected", {}).items():
                possible += 1
                earned += row.get(field) == expected
            spans = row.get("evidence_spans", [])
            required = case.get("required_evidence", [])
            complete = (
                isinstance(spans, list)
                and all(item in spans for item in required)
            )
            possible += 1
            earned += complete
            route_evidence_complete = route_evidence_complete and complete
        quality[route] = earned / possible if possible else 0.0
        evidence_complete[route] = route_evidence_complete
        try:
            metrics[route] = {
                "latency_seconds": float(payload["latency_seconds"]),
                "cost_usd": float(payload["cost_usd"]),
            }
        except (KeyError, TypeError, ValueError) as error:
            raise ReplayError(f"{route} metrics are invalid") from error
    evidence_not_weakened = all(evidence_complete.values())
    cheaper = metrics["luna"]["cost_usd"] < metrics["terra"]["cost_usd"]
    faster = metrics["luna"]["latency_seconds"] < metrics["terra"]["latency_seconds"]
    passed = (
        quality == {"luna": 1.0, "terra": 1.0}
        and evidence_not_weakened
        and cheaper
        and faster
    )
    receipt = {
        "version": 1,
        "status": "pass" if passed else "fail",
        "snapshot_sha256": snapshot_sha256,
        "case_count": len(expected_cases),
        "quality": quality,
        "evidence_complete": evidence_complete,
        "evidence_not_weakened": evidence_not_weakened,
        "metrics": metrics,
        "luna_cheaper": cheaper,
        "luna_faster": faster,
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def measured_result(result_path: Path, attempts_path: Path) -> dict[str, Any]:
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    attempts = [
        json.loads(line) for line in Path(attempts_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = next(
        (row for row in attempts if row.get("rc") == 0 and row.get("schema_valid") is True),
        None,
    )
    if selected is None:
        raise ReplayError("runner evidence has no successful schema-valid attempt")
    cost = selected.get("usage", {}).get("provider_cost_usd")
    if not isinstance(cost, (int, float)):
        raise ReplayError("runner evidence has no measured provider cost")
    return {
        **result,
        "latency_seconds": float(selected["duration_ms"]) / 1000,
        "cost_usd": float(cost),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--luna-result", type=Path, required=True)
    parser.add_argument("--luna-attempts", type=Path, required=True)
    parser.add_argument("--terra-result", type=Path, required=True)
    parser.add_argument("--terra-attempts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    receipt = evaluate_route_replay(snapshot, {
        "luna": measured_result(args.luna_result, args.luna_attempts),
        "terra": measured_result(args.terra_result, args.terra_attempts),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
