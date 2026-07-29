#!/usr/bin/env python3
"""Deterministic queue planning for uncontracted Coconala replies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    from connector_outbox import (
        ConnectorOutbox,
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
    queue: dict[str, Any], *, database: Path, manifest: Path
) -> dict[str, Any]:
    """Durably deduplicate every covered event onto one active thread action."""
    if queue.get("status") == "collector_unhealthy":
        raise ValueError("collector queue is unhealthy")
    if queue.get("status") not in {"ready", "queue_empty"}:
        raise ValueError("invalid queue status")
    outbox = ConnectorOutbox(database, manifest)
    actions: dict[int, dict[str, Any]] = {}
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
            action = outbox.enqueue(
                event_key=str(event_key),
                thread_id=thread_id,
                thread_url=thread_url,
                observed_at=observed_at,
            )
            actions[int(action["action_id"])] = action
    return {
        "status": "enqueued" if actions else "queue_empty",
        "actions": list(actions.values()),
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
        if row.get("reply_required") is not True or row.get("last_message_side") != "buyer":
            continue
        talkroom_id = str(row["talkroom_id"])
        if talkroom_id in paid_talkroom_ids or row.get("contracted") is True:
            continue
        if not row.get("buyer_sent_at"):
            errors.append(f"inquiry:{talkroom_id}:missing_buyer_sent_at")
            continue
        origin_at = _timestamp(row["buyer_sent_at"])
        event_key = _event_key(row, talkroom_id, origin_at)
        if event_key is None:
            errors.append(f"inquiry:{talkroom_id}:missing_event_identity")
            continue
        warning_at = origin_at + timedelta(minutes=15)
        breach_at = origin_at + timedelta(minutes=30)
        reply_due_at = detected_at + timedelta(minutes=10)
        sla_status = "breached" if current >= breach_at else "warning" if current >= warning_at else "on_time"
        items.append({
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
            "next_action": "reply",
        })
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
    return {"status": "ready" if queued else "queue_empty", "errors": [], "items": queued}


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
    args = parser.parse_args()
    if args.command == "enqueue":
        queue = json.loads(args.queue.read_text(encoding="utf-8"))
        result = enqueue_queue(queue, database=args.database, manifest=args.manifest)
        print(json.dumps({
            "status": result["status"],
            "actions": len(result["actions"]),
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
