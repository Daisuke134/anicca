#!/usr/bin/env python3
"""Validate an agent-authored execution decision against cleanup and remote truth."""

from __future__ import annotations

import hashlib
import json
import copy
from typing import Any

import capafy_portfolio as portfolio


TOP_FIELDS = {"schema_version", "kind", "queue_source_digest", "assessed_at", "items"}
ITEM_FIELDS = {
    "agent_id", "decision", "reason", "proposed_title", "proposed_description",
    "evidence", "observable_success",
}
DECISIONS = {"already_satisfied", "submit_once", "stop", "retire"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def queue_digest(queue: dict) -> str:
    source = copy.deepcopy(queue)
    for item in source.get("items", []):
        if item.get("status") in {"verified", "retired"}:
            item["status"] = "queued"
            item["remote_url"] = None
    return "sha256:" + hashlib.sha256(_canonical(source)).hexdigest()


def validate_execution(queue: dict, remotes: dict[str, dict], value: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != TOP_FIELDS:
        return ["execution has unsupported or missing top-level fields"]
    if value.get("schema_version") != 1 or value.get("kind") != "capafy_cleanup_execution":
        errors.append("execution identity is invalid")
    if value.get("queue_source_digest") != queue_digest(queue):
        errors.append("queue source digest does not match")
    if not portfolio._utc(value.get("assessed_at")):
        errors.append("assessed_at is invalid")
    queued = {item["agent_id"]: item for item in queue.get("items", [])}
    for agent_id in queued:
        latest = (remotes.get(agent_id) or {}).get("latest_version")
        if not isinstance(latest, dict) or str(latest.get("agentId")) != agent_id:
            errors.append(f"{agent_id} remote agentId does not match")
    items = value.get("items")
    if not isinstance(items, list):
        return errors + ["items must be a list"]
    ids = [item.get("agent_id") for item in items if isinstance(item, dict)]
    if len(ids) != len(set(ids)) or set(ids) != set(queued):
        errors.append("items must cover every queued agent_id exactly once")
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
            errors.append(f"{prefix} has unsupported or missing fields")
            continue
        queued_item = queued.get(item["agent_id"])
        decision = item.get("decision")
        if decision not in DECISIONS:
            errors.append(f"{prefix}.decision is invalid")
        if decision == "retire" and (queued_item or {}).get("action") != "retire_candidate":
            errors.append(f"{prefix}.retire is only valid for retire_candidate")
        for field in ("reason", "observable_success"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{prefix}.{field} is required")
        if decision == "submit_once":
            for field in ("proposed_title", "proposed_description"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f"{prefix}.{field} is required for submit_once")
        elif item.get("proposed_title") is not None or item.get("proposed_description") is not None:
            errors.append(f"{prefix} proposals are only valid for submit_once")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be non-empty")
            continue
        for evidence_index, proof in enumerate(evidence):
            ep = f"{prefix}.evidence[{evidence_index}]"
            if not isinstance(proof, dict) or not portfolio._https(proof.get("url")):
                errors.append(f"{ep}.url must be HTTPS")
            elif not portfolio._utc(proof.get("observed_at")):
                errors.append(f"{ep}.observed_at is invalid")
            elif proof.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"{ep}.confidence is invalid")
            elif not isinstance(proof.get("claim"), str) or not proof["claim"].strip():
                errors.append(f"{ep}.claim is required")
    return errors


def apply_terminal_judgments(queue: dict, remotes: dict[str, dict], value: dict) -> dict:
    """Close judgments that need no remote mutation; leave submissions queued."""
    errors = validate_execution(queue, remotes, value)
    if errors:
        raise ValueError("execution is invalid: " + "; ".join(errors))
    result = copy.deepcopy(queue)
    decisions = {item["agent_id"]: item["decision"] for item in value["items"]}
    for item in result["items"]:
        decision = decisions[item["agent_id"]]
        if decision == "already_satisfied":
            item["status"] = "verified"
            item["remote_url"] = f"https://capafy.ai/agent/{item['agent_id']}"
        elif decision == "retire":
            item["status"] = "retired"
            item["remote_url"] = None
    return result
