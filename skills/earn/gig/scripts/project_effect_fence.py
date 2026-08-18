#!/usr/bin/env python3
"""Project/capability-scoped external-effect fences for the Gig runtime."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IDENTITY_FIELDS = ("request_id", "talkroom_id", "contract_id")

# One capability name, used by every producer and every consumer of this registry.
# b1_conversation_gate already asks for exactly this string; nothing new is invented here.
CONVERSATION_WRITE = "conversation_write"
COCONALA = "coconala"
PAID_CONVERSATION_REASON = (
    "paid order fulfilment is owned by the PAID_WORK lane; other lanes observe "
    "this room and do not speak in it"
)


class FenceError(ValueError):
    """A fence registry cannot be trusted."""


def _timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise FenceError("invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise FenceError("timestamp_requires_timezone")
    return parsed.astimezone(timezone.utc)


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(registry, dict) or registry.get("version") != 1:
        raise FenceError("invalid_registry_version")
    fences = registry.get("fences")
    if not isinstance(fences, list):
        raise FenceError("invalid_fences")
    seen: set[str] = set()
    for fence in fences:
        if not isinstance(fence, dict):
            raise FenceError("invalid_fence")
        fence_id = str(fence.get("id") or "")
        if not fence_id or fence_id in seen:
            raise FenceError("invalid_or_duplicate_fence_id")
        seen.add(fence_id)
        if fence.get("state") not in {"open", "released"}:
            raise FenceError("invalid_fence_state")
        identities = fence.get("identities")
        if not isinstance(identities, dict) or not any(
            str(identities.get(field) or "") for field in IDENTITY_FIELDS
        ):
            raise FenceError("missing_fence_identity")
        if any(field not in IDENTITY_FIELDS for field in identities):
            raise FenceError("unsupported_fence_identity")
        capabilities = fence.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities or not all(
            isinstance(value, str) and value for value in capabilities
        ):
            raise FenceError("invalid_fence_capabilities")
        if not str(fence.get("reason") or ""):
            raise FenceError("missing_fence_reason")
        _timestamp(fence.get("opened_at"))
        release = fence.get("release")
        if not isinstance(release, dict) or release.get("kind") not in {"event", "at"}:
            raise FenceError("invalid_fence_release")
        if release["kind"] == "event" and not str(release.get("event") or ""):
            raise FenceError("missing_release_event")
        if release["kind"] == "at":
            _timestamp(release.get("at"))
    return fences


def _matches(item: dict[str, Any], fence: dict[str, Any]) -> bool:
    identities = fence["identities"]
    return any(
        str(identities.get(field) or "")
        and str(item.get(field) or "") == str(identities[field])
        for field in IDENTITY_FIELDS
    )


def active_fences_for_item(
    item: dict[str, Any],
    registry: dict[str, Any],
    *,
    capability: str,
    platform: str,
    now: datetime,
) -> list[dict[str, Any]]:
    current = now.astimezone(timezone.utc)
    active: list[dict[str, Any]] = []
    for fence in validate_registry(registry):
        if fence["state"] != "open":
            continue
        if str(fence.get("platform") or platform) != platform:
            continue
        if capability not in fence["capabilities"] and "*" not in fence["capabilities"]:
            continue
        release = fence["release"]
        if release["kind"] == "at" and current >= _timestamp(release["at"]):
            continue
        if _matches(item, fence):
            active.append(fence)
    return active


def partition_items(
    items: list[dict[str, Any]],
    registry: dict[str, Any],
    *,
    capability: str,
    platform: str,
    now: datetime,
) -> dict[str, Any]:
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise FenceError("invalid_queue_items")
    available: list[dict[str, Any]] = []
    fenced: list[dict[str, Any]] = []
    for item in items:
        matches = active_fences_for_item(
            item, registry, capability=capability, platform=platform, now=now
        )
        if not matches:
            available.append(item)
            continue
        identity = next(
            (str(item.get(field)) for field in ("talkroom_id", "request_id", "contract_id") if item.get(field)),
            "unknown",
        )
        fenced.append({
            "item_identity": identity,
            "fence_ids": [str(fence["id"]) for fence in matches],
            "reasons": [str(fence["reason"]) for fence in matches],
        })
    return {
        "selected": available[0] if available else None,
        "available": available,
        "fenced": fenced,
    }


# --- TODO 3c: one mouth per room -------------------------------------------------------
#
# On 2026-08-07 two lanes were talking into talkroom 90000002 (order 91000002). PAID_WORK
# carried the requirements, the BLOCKED record and four gates built that day; the B1 reply
# lane carried the text on the screen and nothing else, and it was B1 that told a paying
# buyer to go and read delivery-v2.md and wrote 「こちらでさせていただきました」 over zero
# work. B1 was not misbehaving -- it was never told the room was somebody else's.
#
# Membership is LOOKED UP, never inferred. The only sources are the paid orders the pass
# already collected and the delivery queue built from them: no title matching, no keyword
# on the message body. A room is fenced because an order says so, or it is not fenced.


# The delivery queue is NOT uniformly paid. delivery_queue.build appends
# quote_needing_proposal rows straight from snapshot["quotes"] (delivery_queue.py:301-309),
# and those are pre-purchase conversations -- the exact work B1 exists to do. An earlier
# version of this module unioned every queue item, which would have fenced a quote room and
# silenced a proposal. Named as a deny-list rather than an allow-list so an unrecognised
# class fails towards refusing to write, never towards writing.
NON_PAID_QUEUE_CLASSES = frozenset({
    "quote_needing_proposal",
    "nurture",
    "listing_apply_learn",
})


def _identity_ids(rows: Any, label: str, *, paid_classes_only: bool = False) -> set[str]:
    """Talkroom ids out of one already-collected source, or FenceError."""
    if rows is None:
        return set()
    if not isinstance(rows, list):
        raise FenceError(f"invalid_{label}")
    found: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise FenceError(f"invalid_{label}_row")
        if paid_classes_only and str(row.get("queue_class") or "") in NON_PAID_QUEUE_CLASSES:
            continue
        value = str(row.get("talkroom_id") or "").strip()
        if value:
            found.add(value)
    return found


def paid_order_talkroom_ids(snapshot: dict[str, Any]) -> set[str]:
    """The rooms the collector itself already opened, from snapshot["orders"] alone.

    Deliberately narrower than paid_talkroom_ids, and it is the narrowness that makes it
    safe to remove these rooms from a lane's target list: coconala_queue_snapshot loops
    `for order in orders` and writes live-dom/talkroom-<id>.json plus a screenshot for every
    one of them (coconala_queue_snapshot.py:1411-1447), before any lane runs and with no
    model involved. This set and that loop read the same list, so a room in this set is a
    room the pass has already observed. Widen this and that guarantee stops holding.
    """
    if not isinstance(snapshot, dict):
        raise FenceError("invalid_snapshot")
    orders = snapshot.get("orders")
    if not isinstance(orders, list):
        raise FenceError("invalid_snapshot_orders")
    return _identity_ids(orders, "snapshot_orders")


def paid_talkroom_ids(
    snapshot: dict[str, Any], queue: dict[str, Any] | None = None
) -> set[str]:
    """Every talkroom id that a paid order or a PAID delivery-queue row names.

    Wider than paid_order_talkroom_ids on purpose: this one only decides whether to refuse
    a write, and refusing one too many costs a message we can send next pass.

    Raises rather than returning a short set: a half-read source would silently unfence a
    paying customer's room, which is the exact failure this exists to stop.
    """
    found = paid_order_talkroom_ids(snapshot)
    if queue is not None:
        if not isinstance(queue, dict):
            raise FenceError("invalid_queue")
        found |= _identity_ids(queue.get("items"), "queue_items", paid_classes_only=True)
    return found


def paid_conversation_registry(
    snapshot: dict[str, Any],
    queue: dict[str, Any] | None = None,
    *,
    opened_at: datetime,
    platform: str = COCONALA,
) -> dict[str, Any]:
    """A v1 registry that closes conversation_write on every paid room.

    No new vocabulary: the rows below are ordinary fences, validated by validate_registry
    and read by the active_fences_for_item that b1_conversation_gate already calls.

    Release is an event, never a clock. A paid room stops being fenced when the order stops
    appearing in the snapshot -- next pass simply builds no fence for it. A timed release
    would reopen the room while the order was still live.
    """
    stamp = _timestamp(opened_at.isoformat() if isinstance(opened_at, datetime) else opened_at)
    registry = {
        "version": 1,
        "fences": [
            {
                "id": f"paid-conversation-write:{platform}:{talkroom_id}",
                "state": "open",
                "platform": platform,
                "identities": {"talkroom_id": talkroom_id},
                "capabilities": [CONVERSATION_WRITE],
                "reason": PAID_CONVERSATION_REASON,
                "opened_at": stamp.isoformat(),
                "release": {"kind": "event", "event": f"paid_order_closed:{talkroom_id}"},
            }
            for talkroom_id in sorted(paid_talkroom_ids(snapshot, queue))
        ],
    }
    validate_registry(registry)
    return registry


def write_fenced_talkroom_ids(
    registry: dict[str, Any] | None,
    *,
    platform: str = COCONALA,
    now: datetime | None = None,
) -> frozenset[str] | None:
    """The rooms this registry forbids writing into, or None when it could not be read.

    None is the fourth answer, in the shape paid_work_evidence.blocked_evidence_verdict
    uses: "I could not look" is not "there is nothing there", and each caller has to pick
    its own safe direction rather than inherit a default that happens to be convenient.
    """
    if registry is None:
        return None
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        fences = validate_registry(registry)
    except FenceError:
        return None
    fenced: set[str] = set()
    for fence in fences:
        item = {"talkroom_id": str(fence["identities"].get("talkroom_id") or "")}
        if not item["talkroom_id"]:
            continue
        if active_fences_for_item(
            item,
            registry,
            capability=CONVERSATION_WRITE,
            platform=platform,
            now=current,
        ):
            fenced.add(item["talkroom_id"])
    return frozenset(fenced)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
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
    select = subparsers.add_parser("select")
    select.add_argument("--queue", required=True, type=Path)
    select.add_argument("--fences", required=True, type=Path)
    select.add_argument("--capability", required=True)
    select.add_argument("--platform", required=True)
    select.add_argument("--now", required=True)
    select.add_argument("--output", required=True, type=Path)
    build_paid = subparsers.add_parser("build-paid")
    build_paid.add_argument("--snapshot", required=True, type=Path)
    build_paid.add_argument("--queue", type=Path)
    build_paid.add_argument("--platform", default=COCONALA)
    build_paid.add_argument("--now", required=True)
    build_paid.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "build-paid":
        try:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            queue = (
                json.loads(args.queue.read_text(encoding="utf-8"))
                if args.queue is not None and args.queue.is_file()
                else None
            )
            registry = paid_conversation_registry(
                snapshot,
                queue,
                opened_at=_timestamp(args.now),
                platform=args.platform,
            )
            _atomic_json(args.output, registry)
            print(json.dumps({
                "ok": True,
                "fenced": len(registry["fences"]),
                "output": str(args.output),
            }, separators=(",", ":")))
            return 0
        except (OSError, json.JSONDecodeError, FenceError) as exc:
            print(
                json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")),
                file=sys.stderr,
            )
            return 2
    try:
        queue = json.loads(args.queue.read_text(encoding="utf-8"))
        registry = json.loads(args.fences.read_text(encoding="utf-8"))
        result = partition_items(
            queue.get("items"),
            registry,
            capability=args.capability,
            platform=args.platform,
            now=_timestamp(args.now),
        )
        _atomic_json(args.output, result)
        print(json.dumps({
            "ok": True,
            "selected": result["selected"],
            "available": len(result["available"]),
            "fenced": result["fenced"],
            "output": str(args.output),
        }, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (OSError, json.JSONDecodeError, FenceError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
