#!/usr/bin/env python3
"""Deterministic ground-truth verification for speedy reply actions."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


BROWSER_ERROR_CODES = frozenset({
    "network_enable_failed",
    "bring_to_front_failed",
    "submit_form_failed",
    "refresh_thread_failed",
    "network_drain_failed",
    "post_click_read_failed",
    "click_transport_failed",
    "submit_rejected_external_contact",
    "submit_rejected_message_validation",
    "submit_rejected_sending_unavailable",
    "submit_rejected_other_validation",
    "submit_rejected_no_validation",
})


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_url(value: Any) -> str:
    parsed = urlsplit(str(value or ""))
    if parsed.hostname not in {"coconala.com", "www.coconala.com"}:
        raise ValueError("invalid Coconala URL")
    return f"https://coconala.com{parsed.path}"


def _new_outgoing_sent_at(
    before: dict[str, Any],
    after: dict[str, Any],
    outgoing_hash: str,
) -> str | None:
    before_messages = before.get("seller_messages")
    after_messages = after.get("seller_messages")
    if isinstance(before_messages, list) and isinstance(after_messages, list):
        remaining: list[tuple[str, str]] = []
        for message in before_messages:
            if isinstance(message, dict):
                remaining.append((
                    str(message.get("body_sha256") or ""),
                    str(message.get("sent_at") or ""),
                ))
        new_matches: list[str] = []
        for message in after_messages:
            if not isinstance(message, dict):
                continue
            signature = (
                str(message.get("body_sha256") or ""),
                str(message.get("sent_at") or ""),
            )
            if signature in remaining:
                remaining.remove(signature)
            elif signature[0] == outgoing_hash and signature[1]:
                new_matches.append(signature[1])
        return new_matches[0] if len(new_matches) == 1 else None
    before_hashes = list(before.get("seller_message_hashes") or [])
    after_hashes = list(after.get("seller_message_hashes") or [])
    if (
        after_hashes.count(outgoing_hash) == before_hashes.count(outgoing_hash) + 1
        and int(after.get("seller_count") or 0) == int(before.get("seller_count") or 0) + 1
    ):
        value = str(after.get("seller_sent_at") or "")
        return value or None
    return None


def verify_reply(
    intent: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Return ``replied`` only when authoritative post-send facts match."""
    talkroom_id = str(intent["talkroom_id"])
    thread_url = _canonical_url(intent["talkroom_url"])
    outgoing_hash = str(intent["outgoing_hash"])
    if urlsplit(thread_url).path not in {
        f"/talkrooms/{talkroom_id}",
        f"/mypage/direct_message/{talkroom_id}",
    }:
        return {
            "status": "evidence_invalid",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": outgoing_hash if re.fullmatch(r"[0-9a-f]{64}", outgoing_hash) else None,
            "seller_sent_at": None,
            "last_sender": "",
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": ["intent_thread_identity_mismatch"],
        }
    if not re.fullmatch(r"[0-9a-f]{64}", outgoing_hash):
        return {
            "status": "evidence_invalid",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": None,
            "seller_sent_at": None,
            "last_sender": "",
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": ["invalid_outgoing_hash"],
        }
    if not after.get("seller_sent_at"):
        errors = ["post_send_ground_truth_unavailable"]
        native_submit_path = f"/mypage/direct_message_ajax/{talkroom_id}"
        diagnostic = after.get("send_diagnostic")
        if isinstance(diagnostic, dict):
            textarea_length = diagnostic.get("textarea_length")
            visible_error_count = diagnostic.get("visible_error_count")
            if type(textarea_length) is int and textarea_length > 0:
                errors.append("composer_not_cleared_after_click")
            if type(visible_error_count) is int and visible_error_count > 0:
                errors.append("page_reported_send_error")
        network = after.get("send_network")
        if isinstance(network, list):
            rows = [row for row in network if isinstance(row, dict)]
            if not rows:
                errors.append("send_request_not_observed")
            elif any(row.get("outcome") == "failed" for row in rows):
                errors.append("send_request_failed")
            elif any(
                type(row.get("status")) is int and int(row["status"]) >= 400
                for row in rows
            ):
                errors.append("send_request_http_error")
            elif any(
                row.get("outcome") == "finished"
                and type(row.get("status")) is int
                and 200 <= int(row["status"]) < 400
                for row in rows
            ):
                errors.append("send_request_finished_without_ground_truth")
            elif any(
                row.get("method") == "POST"
                and row.get("path") == native_submit_path
                and row.get("outcome") == "pending"
                for row in rows
            ):
                errors.append("direct_message_post_stalled")
            elif not any(
                row.get("method") == "POST"
                and row.get("path") == native_submit_path
                for row in rows
            ):
                errors.append("direct_message_post_not_observed")
            else:
                errors.append("send_request_outcome_unknown")
        browser_error_code = str(after.get("browser_error_code") or "")
        if browser_error_code in BROWSER_ERROR_CODES:
            errors.append(browser_error_code)
        return {
            "status": "reconcile_pending",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": outgoing_hash,
            "seller_sent_at": None,
            "last_sender": str(after.get("last_sender") or ""),
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": errors,
        }
    origin_at = _timestamp(intent["origin_at"])
    before_hashes = [str(value) for value in before.get("seller_message_hashes", [])]
    hashes = [str(value) for value in after.get("seller_message_hashes", [])]
    seller_sent_at = _new_outgoing_sent_at(before, after, outgoing_hash)
    sent_at = _timestamp(seller_sent_at) if seller_sent_at else None
    try:
        before_url = _canonical_url(before.get("url"))
        after_url = _canonical_url(after.get("url"))
    except ValueError:
        before_url = ""
        after_url = ""
    identity_matches = (
        str(before.get("talkroom_id")) == talkroom_id
        and str(after.get("talkroom_id")) == talkroom_id
        and before_url == thread_url
        and after_url == thread_url
    )
    if not identity_matches:
        return {
            "status": "evidence_invalid",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": outgoing_hash,
            "seller_sent_at": seller_sent_at,
            "last_sender": str(after.get("last_sender") or ""),
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": ["thread_identity_mismatch"],
        }
    follow_up_origin_at = after.get("latest_buyer_sent_at")
    follow_up_required = (
        sent_at is not None
        and after.get("last_sender") == "buyer"
        and bool(follow_up_origin_at)
        and _timestamp(follow_up_origin_at) > sent_at
    )
    if hashes.count(outgoing_hash) > 1:
        return {
            "status": "duplicate_detected",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": outgoing_hash,
            "seller_sent_at": seller_sent_at,
            "last_sender": str(after.get("last_sender") or ""),
            "follow_up_required": follow_up_required,
            "follow_up_origin_at": str(follow_up_origin_at) if follow_up_required else None,
            "blind_retry_allowed": False,
            "errors": ["duplicate_outgoing_message"],
        }
    verified = (
        bool(before.get("fingerprint"))
        and before.get("fingerprint") != after.get("fingerprint")
        and int(after.get("seller_count") or 0) == int(before.get("seller_count") or 0) + 1
        and hashes.count(outgoing_hash) == before_hashes.count(outgoing_hash) + 1
        and sent_at is not None
        and sent_at >= origin_at
    )
    if not verified:
        return {
            "status": "reconcile_pending",
            "verified": False,
            "event_key": str(intent.get("event_key") or ""),
            "talkroom_id": talkroom_id,
            "thread_url": thread_url,
            "outgoing_hash": outgoing_hash,
            "seller_sent_at": seller_sent_at,
            "last_sender": str(after.get("last_sender") or ""),
            "follow_up_required": False,
            "follow_up_origin_at": None,
            "blind_retry_allowed": False,
            "errors": ["reply_ground_truth_not_confirmed"],
        }
    return {
        "status": "replied",
        "verified": True,
        "event_key": str(intent.get("event_key") or ""),
        "talkroom_id": talkroom_id,
        "thread_url": thread_url,
        "outgoing_hash": outgoing_hash,
        "seller_sent_at": seller_sent_at,
        "last_sender": str(after.get("last_sender") or ""),
        "follow_up_required": follow_up_required,
        "follow_up_origin_at": str(follow_up_origin_at) if follow_up_required else None,
        "blind_retry_allowed": False,
        "errors": [],
    }


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--intent", required=True, type=Path)
    verify.add_argument("--before", required=True, type=Path)
    verify.add_argument("--after", required=True, type=Path)
    verify.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_reply(
        json.loads(args.intent.read_text(encoding="utf-8")),
        json.loads(args.before.read_text(encoding="utf-8")),
        json.loads(args.after.read_text(encoding="utf-8")),
    )
    _atomic_json(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "verified": result["verified"],
        "errors": result["errors"],
        "output": str(args.output),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if result["verified"] else 2 if result["status"] == "reconcile_pending" else 3


if __name__ == "__main__":
    raise SystemExit(main())
