#!/usr/bin/env python3
"""Thin Gig allowlist adapter for the shared bounded context packet builder."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import date
from pathlib import Path
import sys
from typing import Any


SHARED = Path(__file__).resolve().parents[4] / "runtime/agent-runner/context_packet.py"
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
    "buyer_feedback_identity_sha256",
    "buyer_feedback_message_identities",
    "buyer_feedback_requirements_path",
    "buyer_feedback_pending_artifact",
    # C3a: initial_request (build v1 from the buyer's brief) vs revision (the
    # buyer has already seen an artifact). Without it the builder cannot tell a
    # never-delivered order from a returned one, and its prompt assumes revision.
    "buyer_feedback_stage",
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
VERIFIED_APPLICATION_INPUT_FIELDS = (
    "request_id",
    "offer_id",
    "requester_user_id",
    "title",
    "proposal_body",
    "price_jpy",
    "deliver_date",
    "offer_url",
)
VERIFIED_APPLICATION_FIELDS = ("title", "proposal_body", "price_jpy", "deliver_date")
REPLY_CONVERSATION_BODY_BYTES = 512


def _truncate_utf8(value: str, limit: int) -> str:
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value
    suffix = "…"
    room = max(0, limit - len(suffix.encode("utf-8")))
    return raw[:room].decode("utf-8", errors="ignore") + suffix


def _verified_application(value: Any, expected_user_id: Any = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("verified_application must be an object")
    fields = {key: value[key] for key in VERIFIED_APPLICATION_INPUT_FIELDS if key in value}
    if set(fields) != set(VERIFIED_APPLICATION_INPUT_FIELDS):
        raise ValueError("verified_application fields missing")
    if not all(re.fullmatch(r"\d+", str(fields.get(key) or "")) for key in (
        "request_id", "offer_id", "requester_user_id"
    )):
        raise ValueError("verified_application identity invalid")
    if expected_user_id is None or not re.fullmatch(r"\d+", str(expected_user_id)):
        raise ValueError("verified_application counterparty missing")
    if str(fields["requester_user_id"]) != str(expected_user_id):
        raise ValueError("verified_application counterparty mismatch")
    proposal_body = fields.get("proposal_body")
    if (
        type(fields.get("price_jpy")) is not int
        or fields["price_jpy"] <= 0
        or type(fields.get("title")) is not str
        or not fields["title"].strip()
        or len(fields["title"].strip().encode("utf-8")) > 512
        or type(proposal_body) is not str
        or not proposal_body.strip()
        or len(proposal_body.strip().encode("utf-8")) > 1024
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fields.get("deliver_date") or ""))
        or not re.fullmatch(
            r"https://coconala\.com/mypage/offers/\d+", str(fields.get("offer_url") or "")
        )
    ):
        raise ValueError("verified_application fields invalid")
    try:
        date.fromisoformat(str(fields["deliver_date"]))
    except ValueError as error:
        raise ValueError("verified_application date invalid") from error
    return {key: fields[key] for key in VERIFIED_APPLICATION_FIELDS}


def paid_work_packet(item: dict[str, Any]) -> dict[str, Any]:
    return _paid_packet("gig_paid_work", item)


def paid_work_packet_with_context(
    item: dict[str, Any], project_root: Path,
) -> dict[str, Any]:
    """The paid-work packet plus the project's compiled combined context.

    ``project_context_compiler`` has written ``context/current.json`` every pass since it
    was added and nothing ever read it back, so the builder received a *path* to the
    buyer's requirements and no content at all -- while the judge read the whole talkroom.
    This is the read-back.

    The bounds are raised, not removed: the compiler already fits its digest into
    ``COMBINED_MAX_BYTES`` and keeps bodies as file references, and these ceilings are the
    backstop that fails loudly if it ever stops doing so.
    """
    fields = {key: item[key] for key in PAID_FIELDS if key in item}
    evidence = item.get("delivery_evidence")
    if isinstance(evidence, dict):
        fields["delivery_evidence"] = {
            key: evidence[key] for key in DELIVERY_FIELDS if key in evidence
        }
    compiled = _project_context(project_root)
    if compiled is not None:
        fields["project_context"] = compiled
    return context_packet.build_packet(
        kind="gig_paid_work",
        fields=fields,
        max_bytes=24576,
        string_bytes=3200,
        list_items=32,
        map_items=32,
        max_depth=8,
    )


def _project_context(project_root: Path) -> dict[str, Any] | None:
    path = Path(project_root).expanduser() / "context" / "current.json"
    try:
        compiled = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    combined = compiled.get("combined_context") if isinstance(compiled, dict) else None
    if not isinstance(combined, dict) or not combined.get("sources_present"):
        return None
    return combined


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
        rows.append({
            "side": str(row["side"]),
            "body": _truncate_utf8(body, REPLY_CONVERSATION_BODY_BYTES),
        })
    fields: dict[str, Any] = {"conversation": rows}
    verified_research = context.get("verified_research")
    if isinstance(verified_research, dict):
        fields["verified_research"] = verified_research
    if context.get("verified_application") is not None:
        fields["verified_application"] = _verified_application(
            context["verified_application"], context.get("counterparty_user_id")
        )
    return context_packet.build_packet(
        kind="gig_reply_composition", fields=fields, string_bytes=1024
    )


def serialize_packet(packet: dict[str, Any]) -> bytes:
    return context_packet.serialize_packet(packet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("paid-work", "paid-delivery"))
    parser.add_argument(
        "--project-root", type=Path,
        help="include the project's compiled combined context (paid-work only)",
    )
    args = parser.parse_args()
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise SystemExit("Gig context source must be an object")
    if args.kind == "paid-work":
        packet = (
            paid_work_packet_with_context(value, args.project_root)
            if args.project_root is not None
            else paid_work_packet(value)
        )
    else:
        packet = paid_delivery_packet(value)
    sys.stdout.buffer.write(serialize_packet(packet) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
