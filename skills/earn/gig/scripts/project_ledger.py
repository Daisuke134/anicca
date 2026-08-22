#!/usr/bin/env python3
"""Generic, request-scoped project state and append-only delivery ledger.

The runner supplies a request id and marketplace adapter; no customer or site is
embedded in this module.  State is a materialized view, while events.jsonl is
the audit trail and is never rewritten.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

PROJECT_DIRS = ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def effect_key(adapter: str, target: str, action: str, input_sha256: str) -> str:
    values = {"adapter": adapter, "target": target, "action": action, "input_sha256": input_sha256}
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("effect key fields are required")
    return f"economic:effect:v1:{_canonical_sha256(values)}"


def capability_result(
    capability: str, status: str, *, evidence: list[dict[str, Any]],
    errors: list[dict[str, Any]] | None = None, source_fact_ids: list[str] | None = None,
) -> dict[str, Any]:
    if status not in {"succeeded", "needs_work", "blocked", "failed"}:
        raise ValueError("invalid capability status")
    if not capability or not isinstance(evidence, list):
        raise ValueError("invalid capability result")
    return {"version": 1, "capability": capability, "status": status,
            "evidence": evidence, "errors": errors or [],
            "source_fact_ids": source_fact_ids or []}


def append_fact(
    root: str | Path, kind: str, payload: dict[str, Any], *, provenance: list[dict[str, Any]],
    capability: dict[str, Any] | None = None, effect: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    state = _read_state(root)
    if not state.get("request_id") or not state.get("adapter") or not kind or not provenance:
        raise ValueError("economic fact identity and provenance are required")
    body = {"version": 1, "kind": kind, "request_id": state["request_id"],
            "adapter": state["adapter"], "payload": payload, "provenance": provenance,
            "capability_result": capability, "effect_key": effect}
    fact = {**body, "fact_id": f"economic:fact:v1:{_canonical_sha256(body)}"}
    ledger = root / "events.jsonl"
    existing = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
    if fact["fact_id"] not in existing:
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": time.time(), "event": "economic_fact", "fact": fact},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    rebuild_graph(root)
    return fact


def rebuild_graph(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    facts: dict[str, dict[str, Any]] = {}
    if (root / "events.jsonl").is_file():
        for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            fact = row.get("fact") if isinstance(row, dict) and row.get("event") == "economic_fact" else None
            if isinstance(fact, dict) and isinstance(fact.get("fact_id"), str):
                facts[fact["fact_id"]] = fact
    state = _read_state(root)
    project_id = f"project:{state.get('adapter')}:{state.get('request_id')}"
    nodes = [{"id": project_id, "type": "project"}]
    edges = []
    for fact_id, fact in sorted(facts.items()):
        nodes.append({"id": fact_id, "type": "fact", "kind": fact.get("kind")})
        edges.append({"from": fact_id, "to": project_id, "type": "FACT_ABOUT"})
        for source in fact.get("provenance") or []:
            source_id = source.get("fact_id") if isinstance(source, dict) else None
            if isinstance(source_id, str) and source_id:
                nodes.append({"id": source_id, "type": "source_fact"})
                edges.append({"from": fact_id, "to": source_id, "type": "DERIVED_FROM"})
    graph = {"version": 1, "project_id": project_id,
             "nodes": sorted({row["id"]: row for row in nodes}.values(), key=lambda row: row["id"]),
             "edges": sorted(edges, key=lambda row: (row["from"], row["to"], row["type"]))}
    path = root / "context" / "economic-graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(graph, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return graph


def init_project(base: str | Path, request_id: str, adapter: str, state: dict[str, Any] | None = None) -> Path:
    if not request_id or not adapter:
        raise ValueError("request_id and adapter are required")
    root = Path(base) / request_id
    for name in PROJECT_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    initial = {"request_id": request_id, "adapter": adapter, **(state or {})}
    initial["request_id"] = request_id
    initial["adapter"] = adapter
    _write_state(root, initial)
    _append_event(root, "project_initialized", initial)
    return root


def _read_state(root: Path) -> dict[str, Any]:
    path = root / "state.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _write_state(root: Path, state: dict[str, Any]) -> None:
    tmp = root / "state.json.tmp"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(root / "state.json")


def _append_event(root: Path, event: str, state: dict[str, Any]) -> None:
    row = {"ts": time.time(), "request_id": state["request_id"], "adapter": state["adapter"], "event": event, "state": state}
    with (root / "events.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def append(root: str | Path, state: dict[str, Any], event: str) -> dict[str, Any]:
    root = Path(root)
    current = _read_state(root)
    if not current.get("request_id") or not current.get("adapter"):
        raise ValueError("project must be initialized")
    supplied = state.get("request_id")
    if supplied is not None and supplied != current["request_id"]:
        raise ValueError("request_id mismatch")
    merged = {**current, **state, "request_id": current["request_id"], "adapter": current["adapter"], "updated_at": time.time()}
    _write_state(root, merged)
    _append_event(root, event, merged)
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("event")
    parser.add_argument("--state", default="{}")
    args = parser.parse_args()
    append(args.root, json.loads(args.state), args.event)
