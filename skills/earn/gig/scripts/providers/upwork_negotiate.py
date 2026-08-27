#!/usr/bin/env python3
"""Create one sealed negotiation intent from the latest private Upwork room head."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve()
GIG_ROOT = HERE.parents[2]
DEFAULT_RUNNER = GIG_ROOT.parents[2] / "runtime/agent-runner/agent_runner.py"
DEFAULT_SCHEMA = GIG_ROOT / "schemas/upwork_negotiation_decision.schema.json"
DEFAULT_INBOX = Path.home() / "gig/state/upwork-inbox.jsonl"
DEFAULT_LOOP_STATE = Path.home() / "gig/state/upwork-free-loop.json"
DEFAULT_OWNER = Path.home() / ".config/anicca/gig/owner-profile.json"
DEFAULT_INTENTS = Path.home() / ".config/anicca/gig/upwork-negotiations"


class NegotiationError(ValueError):
    pass


def _object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NegotiationError(f"{label}_unreadable") from exc
    if not isinstance(value, dict):
        raise NegotiationError(f"{label}_invalid")
    return value


def latest_room_head(path: Path, room_id: str) -> dict[str, Any]:
    path = path.expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
        raise NegotiationError("upwork_inbox_not_private")
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NegotiationError("upwork_inbox_invalid") from exc
        if isinstance(row, dict) and row.get("kind") == "message_room" and row.get("resource_id") == room_id:
            matches.append(row)
    if not matches:
        raise NegotiationError("upwork_room_head_missing")
    head = max(matches, key=lambda row: int(row.get("revision", 0)))
    if (
        not re.fullmatch(r"[0-9a-f]{64}", str(head.get("event_id") or ""))
        or not re.fullmatch(r"[0-9a-f]{64}", str(head.get("head_sha256") or ""))
        or not isinstance(head.get("rendered_text"), str) or not head["rendered_text"]
    ):
        raise NegotiationError("upwork_room_head_invalid")
    return head


def capacity(loop_state: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
    contracts = loop_state.get("active_contracts")
    cap = owner.get("bounds", {}).get("concurrent_job_cap") if isinstance(owner.get("bounds"), dict) else None
    floor = owner.get("bounds", {}).get("minimum_margin_bps") if isinstance(owner.get("bounds"), dict) else None
    if not isinstance(contracts, list) or type(cap) is not int or cap < 1 or type(floor) is not int:
        raise NegotiationError("upwork_capacity_invalid")
    return {
        "active_contract_count": len(contracts), "concurrent_job_cap": cap,
        "capacity_available": len(contracts) < cap, "minimum_margin_bps": floor,
    }


def prompt(head: dict[str, Any], current_capacity: dict[str, Any], owner: dict[str, Any]) -> str:
    return """Decide one Upwork negotiation reply. Return only schema-valid JSON.
Use only OFFICIAL_ROOM, CAPACITY and OWNER. Copy source identity exactly. Never invent scope, price,
cost, deadline, experience, availability, client facts or results. no_reply is mandatory when the
latest message is ours or no client response is owed. decline when prohibited, deceptive, physical,
off-platform payment/contact, or infeasible. clarify when a required term is missing. counter when
scope expanded, price is below the minimum margin, deadline is infeasible, or terms conflict.
accept_terms only when scope, price, cost and deadline are explicit, feasible, capacity is available,
and computed margin meets the floor. Keep communication on Upwork. Do not claim work already done.
OFFICIAL_ROOM=""" + json.dumps(head, ensure_ascii=False, sort_keys=True) + "\nCAPACITY=" + json.dumps(current_capacity, sort_keys=True) + "\nOWNER=" + json.dumps(owner, ensure_ascii=False, sort_keys=True)


def validate_decision(
    decision: dict[str, Any], head: dict[str, Any], current_capacity: dict[str, Any],
    previous_bodies: list[str] | None = None,
) -> dict[str, Any]:
    if set(decision) != {"decision", "reason_codes", "source", "message"}:
        raise NegotiationError("upwork_negotiation_invalid")
    action, reasons, source, message = (
        decision.get("decision"), decision.get("reason_codes"),
        decision.get("source"), decision.get("message"),
    )
    if action not in {"accept_terms", "counter", "clarify", "decline", "no_reply"}:
        raise NegotiationError("upwork_negotiation_invalid")
    if not isinstance(reasons, list) or any(not isinstance(x, str) or not x for x in reasons):
        raise NegotiationError("upwork_negotiation_invalid")
    exact_source = {
        "room_id": head["resource_id"], "room_url": head["resource_url"],
        "event_id": head["event_id"], "head_sha256": head["head_sha256"],
        "revision": head["revision"],
    }
    if source != exact_source:
        raise NegotiationError("upwork_negotiation_source_mismatch")
    if action == "no_reply":
        if message is not None or not reasons:
            raise NegotiationError("upwork_negotiation_invalid")
    else:
        if not isinstance(message, dict) or set(message) != {
            "body", "scope", "price_usd", "expected_cost_usd", "margin_bps", "deadline",
        } or not isinstance(message.get("body"), str) or len(message["body"].strip()) < 20:
            raise NegotiationError("upwork_negotiation_invalid")
        normalized = " ".join(message["body"].lower().split())
        for previous in previous_bodies or []:
            if difflib.SequenceMatcher(None, normalized, " ".join(previous.lower().split())).ratio() >= 0.92:
                raise NegotiationError("upwork_negotiation_near_duplicate")
        if action in {"accept_terms", "counter"}:
            price, cost, margin = message.get("price_usd"), message.get("expected_cost_usd"), message.get("margin_bps")
            if (
                not current_capacity.get("capacity_available")
                or not isinstance(message.get("scope"), str) or len(message["scope"].strip()) < 20
                or not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0
                or not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0
                or type(margin) is not int
                or margin != round((price - cost) / price * 10000)
                or margin < current_capacity["minimum_margin_bps"]
                or not isinstance(message.get("deadline"), str)
            ):
                raise NegotiationError("upwork_negotiation_economics_invalid")
            try:
                deadline = date.fromisoformat(message["deadline"])
                observed = datetime.fromisoformat(head["observed_at"].replace("Z", "+00:00")).date()
            except (TypeError, ValueError) as exc:
                raise NegotiationError("upwork_negotiation_deadline_invalid") from exc
            if deadline < observed:
                raise NegotiationError("upwork_negotiation_deadline_invalid")
        elif action == "clarify" and not reasons:
            raise NegotiationError("upwork_negotiation_invalid")
    body = json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {**decision, "intent_sha256": hashlib.sha256(body.encode()).hexdigest()}


def previous_bodies(root: Path) -> list[str]:
    root = root.expanduser()
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o777 != 0o700:
        raise NegotiationError("upwork_negotiation_store_not_private")
    bodies = []
    for path in root.glob("*.json"):
        if path.is_symlink() or path.stat().st_mode & 0o777 != 0o600:
            raise NegotiationError("upwork_negotiation_store_not_private")
        item = _object(path, "prior_intent")
        message = item.get("message")
        if isinstance(message, dict) and isinstance(message.get("body"), str):
            bodies.append(message["body"])
    return bodies


def write_intent(intent: dict[str, Any], root: Path) -> Path:
    source = intent.get("source") if isinstance(intent, dict) else None
    event_id = source.get("event_id") if isinstance(source, dict) else None
    if not re.fullmatch(r"[0-9a-f]{64}", str(event_id or "")):
        raise NegotiationError("upwork_negotiation_intent_invalid")
    root = root.expanduser()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    path = root / f"{event_id}.json"
    body = json.dumps(intent, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != body:
        raise NegotiationError("upwork_negotiation_intent_immutable")
    if not path.exists():
        path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def existing_intent(
    head: dict[str, Any], current_capacity: dict[str, Any], root: Path,
) -> dict[str, Any] | None:
    event_id = str(head.get("event_id") or "")
    path = root.expanduser() / f"{event_id}.json"
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_mode & 0o777 != 0o600:
        raise NegotiationError("upwork_negotiation_store_not_private")
    stored = _object(path, "prior_intent")
    digest = stored.pop("intent_sha256", None)
    validated = validate_decision(stored, head, current_capacity)
    if validated["intent_sha256"] != digest:
        raise NegotiationError("upwork_negotiation_intent_invalid")
    return validated


def invoke(
    room_id: str, *, inbox: Path = DEFAULT_INBOX, loop_state: Path = DEFAULT_LOOP_STATE,
    owner_path: Path = DEFAULT_OWNER, runner: Path = DEFAULT_RUNNER,
    schema: Path = DEFAULT_SCHEMA, evidence_dir: Path, intents_dir: Path = DEFAULT_INTENTS,
    loop_state_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    head = latest_room_head(inbox, room_id)
    owner = _object(owner_path.expanduser(), "owner")
    current_capacity = capacity(
        loop_state_value if loop_state_value is not None
        else _object(loop_state.expanduser(), "loop_state"), owner,
    )
    replay = existing_intent(head, current_capacity, intents_dir)
    if replay is not None:
        return replay
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    summary_path = evidence_dir / "summary.json"
    if not summary_path.exists():
        result = subprocess.run([
            sys.executable, str(runner), "--task-class", "application-intent-planner",
            "--prompt-stdin", "--schema", str(schema), "--evidence-dir", str(evidence_dir),
            "--task-label", "upwork-negotiation", "--loop", "gig-upwork",
            "--workdir", str(Path.home()), "--timeout-seconds", "420",
            "--escalation-reason", "client-facing Upwork negotiation",
        ], input=prompt(head, current_capacity, owner), text=True, capture_output=True,
            timeout=450, check=False)
        if result.returncode != 0:
            raise NegotiationError("upwork_negotiation_planner_failed")
    summary = _object(summary_path, "summary")
    if summary.get("status") != "success":
        raise NegotiationError("upwork_negotiation_planner_failed")
    result_path = Path(str(summary.get("result_path") or "")).resolve()
    try:
        result_path.relative_to(evidence_dir.resolve())
    except ValueError as exc:
        raise NegotiationError("upwork_negotiation_result_unowned") from exc
    result = validate_decision(
        _object(result_path, "result"), head, current_capacity, previous_bodies(intents_dir),
    )
    write_intent(result, intents_dir)
    for item in evidence_dir.rglob("*"):
        if item.is_file() and not item.is_symlink():
            os.chmod(item, 0o600)
    return result
