#!/usr/bin/env python3
"""Complete domain validation for one Agent action or durable wait."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL_ROOT / "config" / "command-registry.json"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
AUTHORITIES = {
    "READ_ONLY", "WRITE_LOCAL", "SECRET_LOCAL", "MODEL_EXTERNAL",
    "WRITE_EXTERNAL", "MONEY_RECONCILE", "REPORT",
}
WAIT_REASONS = {
    "NO_DUE_ACTION", "EXTERNAL_COOLDOWN", "BUDGET_BLOCKED",
    "QUARANTINED", "NEEDS_READBACK",
}


class ProposalError(ValueError):
    pass


def _commands() -> dict[str, dict]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {row["command"]: row for row in value["commands"]}


def validate(proposal: dict) -> dict:
    if not isinstance(proposal, dict):
        raise ProposalError("proposal must be an object")
    has_action = "action" in proposal
    has_wait = "wait" in proposal
    expected = {"schema_version", "goal_id", "job_id", "rationale"} | (
        {"action"} if has_action and not has_wait else {"wait"} if has_wait and not has_action else set()
    )
    if set(proposal) != expected or has_action == has_wait or proposal.get("schema_version") != 1:
        raise ProposalError("proposal shape is invalid")
    if not all(ID.fullmatch(proposal.get(key, "")) for key in ("goal_id", "job_id")):
        raise ProposalError("proposal identity is invalid")
    rationale = proposal.get("rationale")
    if not isinstance(rationale, str) or not 1 <= len(rationale) <= 1000:
        raise ProposalError("proposal rationale is invalid")
    if has_wait:
        wait = proposal["wait"]
        if not isinstance(wait, dict) or set(wait) != {"reason", "next_due_at"}:
            raise ProposalError("wait shape is invalid")
        if wait.get("reason") not in WAIT_REASONS:
            raise ProposalError("wait reason is invalid")
        due = wait.get("next_due_at")
        try:
            parsed = datetime.fromisoformat(due.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise ProposalError("wait due time is invalid") from error
        if len(due) > 64 or parsed.tzinfo is None:
            raise ProposalError("wait due time is invalid")
        return proposal
    action = proposal["action"]
    if not isinstance(action, dict) or set(action) != {"command", "authority", "argv", "confidence"}:
        raise ProposalError("action shape is invalid")
    command = _commands().get(action.get("command"))
    confidence = action.get("confidence")
    argv = action.get("argv")
    valid_argv = (
        isinstance(argv, list) and len(argv) <= 32
        and all(isinstance(item, str) and len(item) <= 1024 for item in argv)
    )
    if (
        command is None
        or action.get("authority") not in AUTHORITIES
        or action.get("authority") != command["effect_class"]
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
        or not valid_argv
    ):
        raise ProposalError("action contract is invalid")
    return proposal


def apply(proposal: dict, dispatch):
    proposal = validate(proposal)
    if "wait" in proposal:
        return {"state": "WAITING", **proposal["wait"]}
    return dispatch(proposal["action"])
