#!/usr/bin/env python3
"""Deterministic queue planning for uncontracted Coconala replies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    from connector_outbox import (
        ConnectorOutbox,
        InvalidTransition,
        OutboxError,
        coconala_message_event_key,
        validate_coconala_event_key,
    )
except ModuleNotFoundError:  # imported directly by the unit-test loader
    _outbox_spec = importlib.util.spec_from_file_location(
        "connector_outbox", Path(__file__).with_name("connector_outbox.py")
    )
    if _outbox_spec is None or _outbox_spec.loader is None:
        raise
    _outbox_module = importlib.util.module_from_spec(_outbox_spec)
    _outbox_spec.loader.exec_module(_outbox_module)
    ConnectorOutbox = _outbox_module.ConnectorOutbox
    InvalidTransition = _outbox_module.InvalidTransition
    OutboxError = _outbox_module.OutboxError
    coconala_message_event_key = _outbox_module.coconala_message_event_key
    validate_coconala_event_key = _outbox_module.validate_coconala_event_key


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _talkroom_url(value: Any, talkroom_id: str) -> str:
    parsed = urlsplit(str(value or ""))
    valid_paths = {
        f"/talkrooms/{talkroom_id}",
        f"/mypage/direct_message/{talkroom_id}",
    }
    if parsed.hostname not in {"coconala.com", "www.coconala.com"} or parsed.path not in valid_paths:
        raise ValueError("invalid talkroom URL")
    return f"https://coconala.com{parsed.path}"


def _event_key(row: dict[str, Any], talkroom_id: str, origin_at: datetime) -> str | None:
    if row.get("message_id"):
        return coconala_message_event_key(talkroom_id, str(row["message_id"]))
    ordinal = row.get("stable_ordinal")
    digest = str(row.get("message_sha256") or "")
    if isinstance(ordinal, int) and ordinal >= 0 and re.fullmatch(r"[0-9a-f]{64}", digest):
        candidate = (
            f"coconala:fallback:v1:{talkroom_id}:{int(origin_at.timestamp())}:"
            f"{ordinal}:sha256_v1:{digest}"
        )
        return validate_coconala_event_key(candidate, talkroom_id)
    return None


def enqueue_queue(
    queue: dict[str, Any], *, database: Path, manifest: Path, now: int | None = None
) -> dict[str, Any]:
    """Durably deduplicate every covered event onto one active thread action.

    C1b: this is also the pass's revive point.  ``blocked`` used to leave that
    state only when a NEW event arrived here, so a silent buyer killed the thread
    forever.  After the (event-driven) enqueue the outbox is asked to revive every
    blocked action whose backoff has elapsed, which is the ONLY time-driven path
    out of ``blocked``.

    The revive writes ``revived_at`` and never touches ``updated_at``, so it
    cannot invalidate an observation that any process captured earlier -- that is
    what makes it safe to run concurrently with the 5-minute detector, which holds
    a different lock.  Enqueue-first is kept as the shipped order, but it is
    defence in depth, not the guard: an ordering inside one call could never have
    protected another process's in-flight snapshot.
    """
    if queue.get("status") == "collector_unhealthy":
        raise ValueError("collector queue is unhealthy")
    if queue.get("status") not in {"ready", "queue_empty"}:
        raise ValueError("invalid queue status")
    outbox = ConnectorOutbox(database, manifest)
    actions: dict[int, dict[str, Any]] = {}
    semantic_reauthorized: list[int] = []
    for item in queue.get("items", []):
        if not isinstance(item, dict):
            raise ValueError("invalid queue item")
        thread_id = str(item.get("talkroom_id") or "")
        thread_url = str(item.get("talkroom_url") or "")
        observed_at = int(_timestamp(item.get("detected_at")).timestamp())
        event_keys = item.get("covered_event_keys")
        if not isinstance(event_keys, list) or not event_keys:
            raise ValueError("missing covered event keys")
        for event_key in event_keys:
            try:
                action = outbox.enqueue(
                    event_key=str(event_key), thread_id=thread_id,
                    thread_url=thread_url, observed_at=observed_at,
                )
            except OutboxError as error:
                if str(error) != "estimate_event_conflict":
                    raise
                estimate = next(
                    (
                        candidate for candidate in outbox.estimate_pending_actions()
                        if candidate.get("thread_id") == thread_id
                    ),
                    None,
                )
                owner = f"buyer-after-estimate-{thread_id}"
                claimed = (
                    outbox.claim(owner=owner, now=observed_at, lease_seconds=30,
                                 action_id=int(estimate["action_id"]))
                    if estimate is not None else None
                )
                if claimed is None:
                    raise
                outbox.close_nothing_to_say(
                    int(claimed["action_id"]), owner=owner,
                    fencing_token=int(claimed["fencing_token"]),
                    reason="buyer_message_after_estimate", now=observed_at,
                )
                action = outbox.enqueue(
                    event_key=str(event_key), thread_id=thread_id,
                    thread_url=thread_url, observed_at=observed_at,
                )
            semantic_body = item.get("semantic_reply_body")
            semantic_context = str(item.get("semantic_context_sha256") or "")
            if (
                queue.get("semantic_ssot") is True
                and action.get("dlq_at") is not None
                and type(semantic_body) is str
                and 0 < len(semantic_body.strip()) <= 1000
                and re.fullmatch(r"[0-9a-f]{64}", semantic_context)
            ):
                try:
                    action = outbox.requeue_closed_action(
                        int(action["action_id"]), now=observed_at,
                        require_no_intent=True,
                    )
                except InvalidTransition:
                    pass
                else:
                    semantic_reauthorized.append(int(action["action_id"]))
            actions[int(action["action_id"])] = action
    # The revive is BEST EFFORT and is never allowed to fail the enqueue. Durable
    # event ingest is this step's job; reviving is an optimisation on top of it.
    # A known way this can raise: the revive is the FIRST manifest read on a
    # queue_empty pass, where nothing read it before, so a corrupt manifest would
    # newly kill this step. Anything escaping here reaches gig_pass.sh's
    # record_failure -> isolate_lane and takes down the whole reply lane, which is
    # the exact outcome C1b exists to prevent. The error is surfaced, never
    # swallowed. (Note: the concurrent-detector hazard is NOT handled here -- it is
    # handled at the source, by the revive not writing updated_at.)
    revive: dict[str, Any] = {"revived": [], "dead_lettered": [], "status": "unknown"}
    revive_error: str | None = None
    try:
        revive = outbox.revive_blocked_actions(
            now=int(time.time()) if now is None else int(now)
        )
    except Exception as error:  # noqa: BLE001 - best-effort by contract
        revive_error = repr(error)
    return {
        "status": "enqueued" if actions else "queue_empty",
        "actions": list(actions.values()),
        "semantic_reauthorized": semantic_reauthorized,
        "revived": list(revive["revived"]),
        "dead_lettered": list(revive["dead_lettered"]),
        "revive_status": "failed" if revive_error else str(revive.get("status") or "unknown"),
        "revive_error": revive_error,
        # Set when state committed but its audit line could not be written: the
        # counts above are real, only the jsonl trail is missing.
        "revive_audit_error": revive.get("audit_error"),
    }


def build_queue(snapshot: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Build a privacy-bounded P1 reply queue from an authenticated snapshot."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    detected_at = _timestamp(snapshot["captured_at"])
    paid_talkroom_ids = {
        str(order.get("talkroom_id"))
        for order in snapshot.get("orders", [])
        if isinstance(order, dict) and order.get("talkroom_id") is not None
    }
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in snapshot.get("inquiries", []):
        if not isinstance(row, dict):
            continue
        seller_debt_reply = row.get("semantic_seller_debt_reply") is True
        if row.get("reply_required") is not True or (
            row.get("last_message_side") != "buyer" and not seller_debt_reply
        ):
            continue
        talkroom_id = str(row["talkroom_id"])
        if talkroom_id in paid_talkroom_ids or row.get("contracted") is True:
            continue
        origin_value = row.get("buyer_sent_at") or (
            row.get("seller_sent_at") if seller_debt_reply else None
        )
        if not origin_value:
            errors.append(f"inquiry:{talkroom_id}:missing_buyer_sent_at")
            continue
        origin_at = _timestamp(origin_value)
        event_key = _event_key(row, talkroom_id, origin_at)
        if event_key is None:
            errors.append(f"inquiry:{talkroom_id}:missing_event_identity")
            continue
        warning_at = origin_at + timedelta(minutes=15)
        breach_at = origin_at + timedelta(minutes=30)
        reply_due_at = detected_at + timedelta(minutes=10)
        sla_status = "breached" if current >= breach_at else "warning" if current >= warning_at else "on_time"
        item = {
            "platform": "coconala",
            "priority": "P1",
            "event_type": "buyer_message",
            "event_key": event_key,
            "coordination_key": f"coconala:{talkroom_id}",
            "covered_event_keys": [event_key],
            "talkroom_id": talkroom_id,
            "talkroom_url": _talkroom_url(row.get("talkroom_url"), talkroom_id),
            "origin_at": _iso(origin_at),
            "detected_at": _iso(detected_at),
            "reply_due_at": _iso(reply_due_at),
            "warning_at": _iso(warning_at),
            "breach_at": _iso(breach_at),
            "sla_status": sla_status,
            "next_action": str(row.get("next_action") or "reply"),
        }
        if isinstance(row.get("semantic_receipt"), dict):
            body = row.get("semantic_reply_body")
            context_sha256 = str(row.get("semantic_context_sha256") or "")
            if type(body) is not str or not body.strip() or not re.fullmatch(
                r"[0-9a-f]{64}", context_sha256,
            ):
                errors.append(f"inquiry:{talkroom_id}:invalid_semantic_reply")
                continue
            item.update({
                "semantic_reply_body": body.strip(),
                "semantic_context_sha256": context_sha256,
                "semantic_receipt_version": row["semantic_receipt"].get("version"),
            })
            if seller_debt_reply:
                item["semantic_seller_debt_reply"] = True
        items.append(item)
    if errors:
        return {"status": "collector_unhealthy", "errors": errors, "items": []}
    by_thread: dict[str, dict[str, Any]] = {}
    for item in sorted(items, key=lambda value: (value["origin_at"], value["event_key"])):
        existing = by_thread.get(item["coordination_key"])
        if existing is None:
            by_thread[item["coordination_key"]] = item
            continue
        event_key = item["event_key"]
        if event_key not in existing["covered_event_keys"]:
            existing["covered_event_keys"].append(event_key)
    queued = sorted(by_thread.values(), key=lambda value: (value["origin_at"], value["event_key"]))
    result = {
        "status": "ready" if queued else "queue_empty",
        "errors": [], "items": queued,
    }
    if snapshot.get("semantic_ssot") is True:
        result["semantic_ssot"] = True
    return result


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
    build = subparsers.add_parser("build")
    build.add_argument("--snapshot", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--now")
    enqueue = subparsers.add_parser("enqueue")
    enqueue.add_argument("--queue", required=True, type=Path)
    enqueue.add_argument("--database", required=True, type=Path)
    enqueue.add_argument("--manifest", required=True, type=Path)
    enqueue.add_argument("--now", type=int)
    args = parser.parse_args()
    if args.command == "enqueue":
        queue = json.loads(args.queue.read_text(encoding="utf-8"))
        result = enqueue_queue(
            queue, database=args.database, manifest=args.manifest, now=args.now
        )
        print(json.dumps({
            "status": result["status"],
            "actions": len(result["actions"]),
            "semantic_reauthorized": len(result["semantic_reauthorized"]),
            "revived": len(result["revived"]),
            "dead_lettered": len(result["dead_lettered"]),
            "revive_status": result["revive_status"],
            "revive_error": result["revive_error"],
            "revive_audit_error": result["revive_audit_error"],
            "database": str(args.database),
        }, ensure_ascii=False, separators=(",", ":")))
        return 0
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    now = _timestamp(args.now) if args.now else None
    result = build_queue(snapshot, now=now)
    _atomic_json(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "items": len(result["items"]),
        "errors": result["errors"],
        "output": str(args.output),
    }, ensure_ascii=False, separators=(",", ":")))
    return 2 if result["status"] == "collector_unhealthy" else 0


if __name__ == "__main__":
    raise SystemExit(main())
