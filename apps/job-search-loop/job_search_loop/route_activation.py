from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .release_activation import activate


class RouteActivationError(ValueError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RouteActivationError(f"invalid gate evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise RouteActivationError(f"invalid gate evidence: {path.name}")
    return value


def validate_route_gate(
    release_root: Path, evidence_root: Path, *, expected_commit: str
) -> dict[str, Any]:
    release_root = Path(release_root).resolve()
    evidence_root = Path(evidence_root).resolve()
    if release_root.name != expected_commit or evidence_root.name != expected_commit:
        raise RouteActivationError("release and replay evidence must bind the expected commit")
    config_path = release_root / "runtime" / "agent-runner" / "config.json"
    snapshot_path = release_root / "apps" / "job-search-loop" / "config" / "model-route-replay.v1.json"
    config = _read(config_path)
    snapshot = _read(snapshot_path)
    classes = config.get("task_classes", {})
    expected_routes = {
        "repeatable-agent": ("gpt-5.6-luna", "medium"),
        "composition-agent": ("gpt-5.6-terra", "medium"),
        "browser-lane-agent": ("gpt-5.6-terra", "medium"),
        "job-search-terra-high": ("gpt-5.6-terra", "high"),
    }
    for name, (model, effort) in expected_routes.items():
        try:
            primary = classes[name]["candidates"][0]
        except (KeyError, IndexError, TypeError) as error:
            raise RouteActivationError(f"route map is missing {name}") from error
        if (primary.get("model"), primary.get("effort")) != (model, effort):
            raise RouteActivationError(f"route map mismatch for {name}")
    if classes["job-search-terra-high"].get("requires_explicit_escalation") is not True:
        raise RouteActivationError("Terra high route lacks explicit escalation")

    receipt = _read(evidence_root / "route-replay-receipt.json")
    claimed_receipt_sha = receipt.get("receipt_sha256")
    unsigned_receipt = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if claimed_receipt_sha != _digest(unsigned_receipt):
        raise RouteActivationError("replay receipt SHA-256 mismatch")
    if receipt.get("status") != "pass":
        raise RouteActivationError("replay receipt did not pass")
    if receipt.get("sample_count") != {"luna": 3, "terra": 3}:
        raise RouteActivationError("replay receipt requires three samples per route")
    if receipt.get("quality") != {"luna": 1.0, "terra": 1.0}:
        raise RouteActivationError("replay quality is incomplete")
    if not all(receipt.get(key) is True for key in (
        "evidence_not_weakened", "luna_cheaper", "luna_faster"
    )):
        raise RouteActivationError("replay performance/evidence gate failed")
    if receipt.get("snapshot_sha256") != _digest(snapshot):
        raise RouteActivationError("snapshot SHA-256 does not match candidate release")

    attempt_count = 0
    for route, model, effort in (
        ("luna", "gpt-5.6-luna", "medium"),
        ("terra", "gpt-5.6-terra", "medium"),
    ):
        for trial in range(1, 4):
            lane = evidence_root / f"{route}-{trial}"
            summary = _read(lane / "summary.json")
            attempts = [
                json.loads(line) for line in (lane / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if summary.get("status") != "success" or (
                summary.get("selected_model"), summary.get("selected_effort")
            ) != (model, effort):
                raise RouteActivationError(f"route replay summary mismatch: {route}-{trial}")
            if len(attempts) != 1 or attempts[0].get("rc") != 0 or attempts[0].get("schema_valid") is not True:
                raise RouteActivationError(f"route replay attempt invalid: {route}-{trial}")
            if (attempts[0].get("model"), attempts[0].get("effort")) != (model, effort):
                raise RouteActivationError(f"route replay attempt model mismatch: {route}-{trial}")
            attempt_count += 1
    gate = {
        "version": 1,
        "status": "approved",
        "candidate_commit": expected_commit,
        "route_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "snapshot_sha256": receipt["snapshot_sha256"],
        "replay_receipt_sha256": claimed_receipt_sha,
        "attempt_count": attempt_count,
    }
    gate["gate_sha256"] = _digest(gate)
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    release = args.data_root / "releases" / args.commit
    evidence = args.data_root / "route-replays" / args.commit
    gate = validate_route_gate(release, evidence, expected_commit=args.commit)
    activation = activate(data_root=args.data_root, commit=args.commit)
    output = {"gate": gate, "activation": activation}
    args.output.write_text(json.dumps(output, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
