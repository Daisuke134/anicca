#!/usr/bin/env python3
"""Validate and apply a non-destructive Capafy portfolio cleanup queue."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import capafy_portfolio as portfolio


TOP_FIELDS = {"schema_version", "kind", "portfolio_source_digest", "created_at", "items"}
ITEM_FIELDS = {
    "agent_id", "triggers", "related_agent_ids", "action", "action_reason",
    "stop_condition", "evidence", "status", "remote_url",
}
TRIGGERS = {"under_review", "draft", "rejected", "overlap"}
ACTIONS = {"repair", "reposition", "retire_candidate"}
QUEUE_STATUSES = {"queued", "submitted", "verified", "retired"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def validate_cleanup(snapshot: dict, value: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != TOP_FIELDS:
        return ["cleanup has unsupported or missing top-level fields"]
    if value.get("schema_version") != 1 or value.get("kind") != "capafy_portfolio_cleanup":
        errors.append("cleanup identity is invalid")
    if value.get("portfolio_source_digest") != portfolio.snapshot_digest(snapshot):
        errors.append("portfolio source digest does not match")
    if not portfolio._utc(value.get("created_at")):
        errors.append("created_at is invalid")
    products = {product["agent_id"]: product for product in snapshot.get("products", [])}
    mandatory = {
        product["agent_id"]
        for product in products.values()
        if product["observed_status"] in {"under_review", "draft", "rejected"}
    }
    items = value.get("items")
    if not isinstance(items, list):
        return errors + ["items must be a list"]
    received: set[str] = set()
    has_overlap = False
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
            errors.append(f"{prefix} has unsupported or missing fields")
            continue
        agent_id = item.get("agent_id")
        if agent_id not in products:
            errors.append(f"{prefix}.agent_id is not in the portfolio")
        elif agent_id in received:
            errors.append(f"duplicate cleanup agent_id: {agent_id}")
        else:
            received.add(agent_id)
        triggers = item.get("triggers")
        if not isinstance(triggers, list) or not triggers or any(t not in TRIGGERS for t in triggers):
            errors.append(f"{prefix}.triggers is invalid")
        elif "overlap" in triggers:
            has_overlap = True
        related = item.get("related_agent_ids")
        if not isinstance(related, list) or any(r not in products or r == agent_id for r in related):
            errors.append(f"{prefix}.related_agent_ids is invalid")
        if isinstance(triggers, list) and "overlap" in triggers and not related:
            errors.append(f"{prefix}.overlap requires related_agent_ids")
        if item.get("action") not in ACTIONS:
            errors.append(f"{prefix}.action is invalid; remote delete is forbidden")
        if not isinstance(item.get("action_reason"), str) or not item["action_reason"].strip():
            errors.append(f"{prefix}.action_reason is required")
        if not isinstance(item.get("stop_condition"), str) or not item["stop_condition"].strip():
            errors.append(f"{prefix}.stop_condition is required")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be non-empty")
        else:
            for evidence_index, proof in enumerate(evidence):
                ep = f"{prefix}.evidence[{evidence_index}]"
                if not isinstance(proof, dict):
                    errors.append(f"{ep} is invalid")
                    continue
                if not portfolio._https(proof.get("url")):
                    errors.append(f"{ep}.url must be HTTPS")
                if not portfolio._utc(proof.get("observed_at")):
                    errors.append(f"{ep}.observed_at is invalid")
                if proof.get("confidence") not in {"high", "medium", "low"}:
                    errors.append(f"{ep}.confidence is invalid")
                if not isinstance(proof.get("claim"), str) or not proof["claim"].strip():
                    errors.append(f"{ep}.claim is required")
        if item.get("status") not in QUEUE_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        remote_url = item.get("remote_url")
        if remote_url is not None and not portfolio._https(remote_url):
            errors.append(f"{prefix}.remote_url must be HTTPS or null")
        if item.get("status") in {"submitted", "verified"} and remote_url is None:
            errors.append(f"{prefix}.remote_url is required after submission")
    missing = sorted(mandatory - received)
    if missing:
        errors.append("mandatory non-online cleanup items are missing: " + ", ".join(missing))
    if not has_overlap:
        errors.append("cleanup must contain at least one evidence-backed overlap group")
    return errors


def apply_cleanup(snapshot: dict, value: dict) -> dict:
    errors = validate_cleanup(snapshot, value)
    if errors:
        raise ValueError("; ".join(errors))
    result = copy.deepcopy(snapshot)
    by_id = {item["agent_id"]: item for item in value["items"]}
    for product in result["products"]:
        item = by_id.get(product["agent_id"])
        if item is None:
            continue
        product["decision"] = item["action"]
        product["decision_reason"] = item["action_reason"]
        product["evidence"] = copy.deepcopy(item["evidence"])
    validation = portfolio.validate_snapshot(result)
    if validation:
        raise ValueError("applied portfolio is invalid: " + "; ".join(validation))
    return result


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", type=Path, required=True)
    parser.add_argument("--cleanup", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.portfolio.read_text(encoding="utf-8"))
        value = json.loads(args.cleanup.read_text(encoding="utf-8"))
        result = apply_cleanup(snapshot, value)
        _atomic_write(args.output or args.portfolio, result)
        print(json.dumps({"valid": True, "item_count": len(value["items"])}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
