#!/usr/bin/env python3
"""Thin Gig allowlist adapter for the shared bounded context packet builder."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


SHARED = Path(__file__).resolve().parents[2] / "agent-runner" / "context_packet.py"
SPEC = importlib.util.spec_from_file_location("shared_context_packet", SHARED)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("shared context packet module is unavailable")
context_packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context_packet)

PAID_FIELDS = (
    "request_id",
    "talkroom_id",
    "contract_id",
    "queue_class",
    "delivery_date",
    "talkroom_state",
    "buyer_feedback_sha256",
    "buyer_feedback_requirements_path",
    "buyer_feedback_pending_artifact",
    "buyer_reply_after_artifact_observed",
    "delivery_action",
    "blockers",
)
DELIVERY_FIELDS = (
    "present",
    "status",
    "artifact_version",
    "acceptance_status",
    "package_sha256",
    "acceptance_delta",
)


def paid_work_packet(item: dict[str, Any]) -> dict[str, Any]:
    return _paid_packet("gig_paid_work", item)


def paid_delivery_packet(item: dict[str, Any]) -> dict[str, Any]:
    return _paid_packet("gig_paid_delivery", item)


def _paid_packet(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    fields = {key: item[key] for key in PAID_FIELDS if key in item}
    evidence = item.get("delivery_evidence")
    if isinstance(evidence, dict):
        fields["delivery_evidence"] = {
            key: evidence[key] for key in DELIVERY_FIELDS if key in evidence
        }
    return context_packet.build_packet(kind=kind, fields=fields)


def reply_composition_packet(context: dict[str, Any]) -> dict[str, Any]:
    conversation = context.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError("conversation must be non-empty")
    rows: list[dict[str, str]] = []
    for row in conversation[-8:]:
        if not isinstance(row, dict) or row.get("side") not in {"buyer", "seller"}:
            raise ValueError("invalid conversation row")
        body = row.get("body")
        if type(body) is not str:
            raise ValueError("invalid conversation body")
        rows.append({"side": str(row["side"]), "body": body})
    fields: dict[str, Any] = {"conversation": rows}
    verified_research = context.get("verified_research")
    if isinstance(verified_research, dict):
        fields["verified_research"] = verified_research
    return context_packet.build_packet(kind="gig_reply_composition", fields=fields)


def serialize_packet(packet: dict[str, Any]) -> bytes:
    return context_packet.serialize_packet(packet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("paid-work", "paid-delivery"))
    args = parser.parse_args()
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise SystemExit("Gig context source must be an object")
    packet = (
        paid_work_packet(value)
        if args.kind == "paid-work"
        else paid_delivery_packet(value)
    )
    sys.stdout.buffer.write(serialize_packet(packet) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
