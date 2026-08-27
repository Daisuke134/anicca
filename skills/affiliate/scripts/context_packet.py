#!/usr/bin/env python3
"""Build the only redacted state packet exposed to the Affiliate Agent."""

from __future__ import annotations

import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = SKILL_ROOT / "config" / "command-registry.json"
GOAL_FIELDS = {"goal_id", "objective", "success_gate"}
JOB_FIELDS = {
    "job_id", "stage", "state", "placement_id", "effect_certainty", "next_due_at",
}
DUE_FIELDS = {"source", "composition", "revenue", "retry"}
RECEIPT_FIELDS = {
    "receipt_type", "state", "status", "effect_certainty", "readback_status",
    "placement_id", "transition_count", "transaction_count", "money_state",
    "net_state", "threshold_state", "currency", "approved_or_paid_net_usd",
    "approved_or_paid_net_minor_by_currency", "reversal_minor_by_currency",
    "cost_state", "cost_coverage_state",
}
TOOL_FIELDS = {
    "command", "effect_class", "input_schema", "output_schema", "effect_schema",
    "precondition_schema", "semantic_postcondition_schema",
}
URL = re.compile(r"https?://\S+", re.I)
INLINE_SECRET = re.compile(r"(?i)\b(password|secret|token|credential)\s*[:=]\s*\S+")


def _safe(value):
    if isinstance(value, str):
        return INLINE_SECRET.sub("[REDACTED]", URL.sub("[REDACTED_URL]", value))
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return None


def _select(value: dict | None, allowed: set[str]) -> dict:
    value = value if isinstance(value, dict) else {}
    return {key: _safe(value[key]) for key in sorted(allowed) if key in value}


def build(*, goal, unfinished_job, due_times, allowed_commands, receipts) -> dict:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    tools = {row["command"]: row for row in registry["commands"]}
    allowed_tools = [
        _select(tools[command], TOOL_FIELDS)
        for command in allowed_commands
        if command in tools
    ]
    return {
        "schema_version": 1,
        "goal": _select(goal, GOAL_FIELDS),
        "unfinished_job": _select(unfinished_job, JOB_FIELDS),
        "due_times": _select(due_times, DUE_FIELDS),
        "allowed_tools": allowed_tools,
        "receipts": [
            _select(receipt, RECEIPT_FIELDS)
            for receipt in receipts
            if isinstance(receipt, dict)
        ],
    }
