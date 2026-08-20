#!/usr/bin/env python3
"""Replay immutable Writer receipts into machine-readable self-heal SLO work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from writer_observability_evidence import build_evidence_index  # noqa: E402
from writer_observability_trace import TraceError, build_trace  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_fingerprint(run_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        digest.update(str(path.relative_to(run_dir)).encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _read_cases(path: Path, state_dir: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "writer.observability.replay-cases" or value.get("version") != 1:
        raise ValueError("unsupported replay case manifest")
    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("replay case manifest has no cases")
    rows = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("replay case must be an object")
        execution_id = str(case.get("execution_id") or "").strip()
        run_id = str(case.get("run_id") or "").strip()
        checkpoint = str(case.get("checkpoint") or "").strip()
        if not execution_id or not run_id or not checkpoint:
            raise ValueError("replay case requires execution_id, run_id, checkpoint")
        run_dir = (state_dir / "runs" / run_id).resolve()
        if run_dir.parent != (state_dir / "runs").resolve() or not run_dir.is_dir():
            raise ValueError(f"invalid run directory for {execution_id}")
        checkpoint_path = (run_dir / checkpoint).resolve()
        if run_dir not in checkpoint_path.parents or not checkpoint_path.is_file():
            raise ValueError(f"missing checkpoint for {execution_id}: {checkpoint}")
        rows.append({**case, "execution_id": execution_id, "run_id": run_id,
                     "checkpoint": checkpoint, "run_dir": run_dir,
                     "checkpoint_path": checkpoint_path})
    return rows


def _cause(reason: str) -> str:
    lowered = reason.lower()
    if reason == "expected_receipt_missing":
        return "missing_receipt"
    if reason == "invalid_receipt":
        return "state_corruption"
    if "stale" in lowered:
        return "state_contract"
    if "403" in lowered or "s3" in lowered:
        return "dependency_or_credential"
    if any(token in lowered for token in ("editor", "anchor", "selector", "dom")):
        return "dom_selector"
    if "timeout" in lowered:
        return "process_timeout"
    return "unclassified"


def _slo_work(execution_id: str, run_id: str, span: dict[str, Any]) -> dict[str, Any]:
    reason = str(span.get("reason") or "unknown")
    fingerprint = hashlib.sha256(
        f"{execution_id}\0{span['phase']}\0{reason}".encode()
    ).hexdigest()
    work = {
        "work_id": fingerprint,
        "execution_id": execution_id,
        "run_id": run_id,
        "trace_id": span["trace_id"],
        "span_id": span["span_id"],
        "phase": span["phase"],
        "reason": reason,
        "cause_class": _cause(reason),
        "owner": "writer-self-heal",
        "state": "open",
        "next_action": "enqueue_repair",
        "source_receipt": span.get("source_receipt"),
    }
    destination = span.get("destination")
    if isinstance(destination, dict):
        work.update({
            "destination": destination.get("pair"),
            "artifact_id": destination.get("artifact_id"),
            "revenue_role": destination.get("revenue_role"),
            "blocking": destination.get("blocking"),
            "error_signature": destination.get("error_signature") or reason,
        })
    return work


def replay(manifest: Path, state_dir: Path, observed_at: str) -> dict[str, Any]:
    cases = _read_cases(manifest, state_dir)
    initial = {case["run_id"]: _tree_fingerprint(case["run_dir"]) for case in cases}
    replays = []
    work: dict[str, dict[str, Any]] = {}
    for case in cases:
        trace = build_trace(case["run_dir"], observed_at)
        evidence = build_evidence_index(case["run_dir"], observed_at)
        breaches = []
        for span in trace["spans"]:
            if span["state"] != "error":
                continue
            item = _slo_work(case["execution_id"], case["run_id"], span)
            breaches.append(item["work_id"])
            work[item["work_id"]] = item
        replays.append({
            "execution_id": case["execution_id"],
            "run_id": case["run_id"],
            "kind": case.get("kind", "recorded"),
            "checkpoint": case["checkpoint"],
            "checkpoint_sha256": _sha256(case["checkpoint_path"]),
            "trace_id": trace["spans"][0]["trace_id"] if trace["spans"] else None,
            "span_count": len(trace["spans"]),
            "incident_count": evidence["incident_count"],
            "slo_work_ids": breaches,
        })
    final = {case["run_id"]: _tree_fingerprint(case["run_dir"]) for case in cases}
    if initial != final:
        raise RuntimeError("immutable replay changed a source run tree")
    return {
        "schema": "writer.observability.slo-replay",
        "version": 1,
        "observed_at": observed_at,
        "source_trees_unchanged": True,
        "replay_count": len(replays),
        "replays": replays,
        "slo_work_count": len(work),
        "slo_work": list(work.values()),
    }


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        value = replay(args.manifest, args.state_dir.resolve(), args.observed_at)
    except (OSError, ValueError, RuntimeError, TraceError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.out:
        _atomic(args.out, value)
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
