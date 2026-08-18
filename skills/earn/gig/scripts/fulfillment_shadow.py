#!/usr/bin/env python3
"""Run the P1-1 effect-free fulfillment graph against an authoritative queue item."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import build_fulfillment_shadow, existing_runner_model


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def authoritative_action(item: dict[str, Any], state: dict[str, Any]) -> str:
    """Project ledger wins when this exact buyer input was already answered."""
    feedback = str(item.get("buyer_feedback_sha256") or "")
    if (
        feedback
        and feedback == str(state.get("handled_buyer_feedback_sha256") or "")
        and state.get("material_event_outcome") == "buyer_answer_sent"
    ):
        return "await_buyer_feedback"
    delivery_action = str(item.get("delivery_action") or "work_required").lower()
    if delivery_action in {"formal", "progress", "none"}:
        return "deliver_existing"
    return "WORK_REQUIRED"


def decision_fingerprint(item: dict[str, Any], state: dict[str, Any]) -> str:
    semantic = {
        "decision_contract_version": 3,
        "talkroom_id": item.get("talkroom_id"),
        "buyer_feedback_sha256": item.get("buyer_feedback_sha256"),
        "delivery_action": item.get("delivery_action"),
        "blockers": item.get("blockers") or [],
        "delivery_evidence": item.get("delivery_evidence") or {},
        "handled_buyer_feedback_sha256": state.get("handled_buyer_feedback_sha256"),
        "material_event_outcome": state.get("material_event_outcome"),
        "current_package_sha256": state.get("current_package_sha256"),
        "formal_delivery_confirmed": state.get("formal_delivery_confirmed"),
    }
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--project-state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--state-root", type=Path, default=Path.home() / "gig")
    parser.add_argument("--evidence-root", type=Path, default=Path.home() / "gig" / "evidence" / "deep-agent-shadow")
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cache-status-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    items = queue.get("items") or []
    if not items:
        atomic_json(args.output, {"status": "queue_empty", "send_performed": False})
        return 0
    item = items[0]
    state = json.loads(args.project_state.read_text(encoding="utf-8"))
    contract_id = str(item.get("talkroom_id") or state.get("request_id") or "")
    expected = authoritative_action(item, state)
    fingerprint = decision_fingerprint(item, state)
    cache_path = args.state_root / "deep-agent" / "decisions" / f"coconala:{contract_id}.json"
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cached = None
    if isinstance(cached, dict) and cached.get("decision_fingerprint") == fingerprint:
        if args.cache_status_only:
            return 0
        reused = dict(cached)
        reused.update(
            {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "queue_path": str(args.queue.resolve()),
                "project_state_path": str(args.project_state.resolve()),
                "reused": True,
            }
        )
        atomic_json(args.output, reused)
        return 0 if reused.get("status") == "match" else 1
    if args.cache_status_only:
        return 2
    model = existing_runner_model(
        skill_root=args.skill_root,
        evidence_root=args.evidence_root,
        workdir=args.skill_root.parents[1],
    )
    graph, runtime, config = build_fulfillment_shadow(
        model=model,
        contract_id=contract_id,
        state_root=args.state_root,
    )
    context = {"queue_item": item, "project_state": state}
    context_json = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    context_sha256 = hashlib.sha256(context_json.encode()).hexdigest()
    try:
        written = runtime.backend.write(
            "/context/current-queue.json",
            context_json,
        )
        if written.error:
            raise RuntimeError(written.error)
        result = graph.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Use the authoritative context JSON included at the end of this message; do not translate "
                            "its virtual Store path into an OS path or search the host filesystem. The project ledger "
                            "is authoritative. "
                            "If handled_buyer_feedback_sha256 equals the queue buyer_feedback_sha256 and the outcome "
                            "is buyer_answer_sent, do not recreate or resend work: next_action is await_buyer_feedback. "
                            "In that wait state, every todo must have status pending, never in_progress or completed. "
                            "If delivery_action is formal, progress, or none, the accepted artifact is already at the "
                            "delivery boundary: next_action is deliver_existing. Otherwise keep concrete unfinished "
                            "work as pending todos and next_action WORK_REQUIRED. "
                            "Use write_todos once, then return content containing only JSON with keys next_action, reason, "
                            f"and context_sha256. context_sha256 must equal {context_sha256}. Do not claim or perform any "
                            f"customer effect. Authoritative context JSON: {context_json}"
                        ),
                    }
                ]
            },
            config,
        )
        observed = json.loads(str(result["messages"][-1].content))
        actual = str(observed.get("next_action") or "")
        context_readback_valid = observed.get("context_sha256") == context_sha256
        todos = result.get("todos") or []
        todo_status_valid = not (
            actual == "await_buyer_feedback"
            and any(todo.get("status") != "pending" for todo in todos)
        )
        evidence = {
            "status": "match" if actual == expected and todo_status_valid and context_readback_valid else "mismatch",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "thread_id": config["configurable"]["thread_id"],
            "effect_mode": config["metadata"]["effect_mode"],
            "queue_path": str(args.queue.resolve()),
            "project_state_path": str(args.project_state.resolve()),
            "buyer_feedback_sha256": item.get("buyer_feedback_sha256"),
            "handled_buyer_feedback_sha256": state.get("handled_buyer_feedback_sha256"),
            "expected_next_action": expected,
            "shadow_next_action": actual,
            "shadow_reason": observed.get("reason"),
            "context_sha256": context_sha256,
            "context_readback_valid": context_readback_valid,
            "todos": todos,
            "todo_status_valid": todo_status_valid,
            "send_performed": False,
            "effect_tools_exposed": 0,
            "decision_fingerprint": fingerprint,
            "reused": False,
        }
        atomic_json(args.output, evidence)
        atomic_json(cache_path, evidence)
        return 0 if evidence["status"] == "match" else 1
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
