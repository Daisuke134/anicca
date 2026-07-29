#!/usr/bin/env python3
"""Fenced lifecycle controller for one Coconala reply side effect."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from connector_outbox import (
        ConnectorOutbox,
        ConsistencyWindowOpen,
        SERVER_REJECTION_CODES,
    )
except ModuleNotFoundError:  # imported directly by unit-test loaders
    _outbox_module = _load_local("connector_outbox")
    ConnectorOutbox = _outbox_module.ConnectorOutbox
    ConsistencyWindowOpen = _outbox_module.ConsistencyWindowOpen
    SERVER_REJECTION_CODES = _outbox_module.SERVER_REJECTION_CODES

try:
    from reply_evidence import verify_reply
except ModuleNotFoundError:  # imported directly by unit-test loaders
    verify_reply = _load_local("reply_evidence").verify_reply


POST_CLICK_LEASE_SECONDS = 420


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


class ReplyActionController:
    """Connect immutable intent and evidence APIs without persisting raw text."""

    def __init__(self, database: Path, manifest: Path):
        self.outbox = ConnectorOutbox(database, manifest)

    def claim(
        self, *, owner: str, now: int, lease_seconds: int, action_id: int | None = None
    ) -> dict[str, Any] | None:
        return self.outbox.claim(
            owner=owner,
            now=now,
            lease_seconds=lease_seconds,
            action_id=action_id,
        )

    def pending_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self.outbox.pending_action_for_thread(thread_id)

    def pending_actions(self) -> list[dict[str, Any]]:
        return self.outbox.pending_actions()

    def reconciliation_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self.outbox.reconciliation_action_for_thread(thread_id)

    def reconciliation_actions(self) -> list[dict[str, Any]]:
        return self.outbox.reconciliation_actions()

    def reconcile_observation(
        self,
        *,
        action: dict[str, Any],
        observation: dict[str, Any],
        observed_at: int,
    ) -> dict[str, Any]:
        """Resolve delivery-unknown from a bounded authoritative thread read."""
        if (
            str(observation.get("talkroom_id") or "") != str(action["thread_id"])
            or str(observation.get("url") or "") != str(action["thread_url"])
        ):
            raise ValueError("reconciliation observation identifies another thread")
        messages = observation.get("seller_messages")
        if not isinstance(messages, list):
            raise ValueError("reconciliation observation lacks seller messages")
        outgoing_hash = str(action["outgoing_hash"])
        matches: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("invalid seller message observation")
            if str(message.get("body_sha256") or "") == outgoing_hash:
                matches.append(message)
        if len(matches) > 1:
            return {
                "status": "duplicate_detected",
                "errors": ["duplicate_outgoing_message"],
            }
        seller_sent_at = None
        if matches:
            seller_sent_at = int(_timestamp(matches[0].get("sent_at")).timestamp())
        try:
            stored = self.outbox.reconcile(
                int(action["action_id"]),
                thread_url=str(observation["url"]),
                outgoing_hash=outgoing_hash,
                seller_sent_at=seller_sent_at,
                last_sender=str(observation.get("last_sender") or "system"),
                observed_at=observed_at,
                authoritative_absent=not matches,
            )
        except ConsistencyWindowOpen:
            return {
                "status": "reconcile_pending",
                "errors": ["consistency_window_open"],
            }
        status = str(stored["state"])
        if status == "replied":
            return {
                "status": "replied",
                "action_id": int(action["action_id"]),
                "revision": int(stored["revision"]),
                "seller_sent_at": str(matches[0]["sent_at"]),
                "origin_at": datetime.fromtimestamp(
                    int(action["intent_origin_at"]), timezone.utc
                ).isoformat(),
                "errors": [],
            }
        if status == "pending":
            result = {"status": "requeued", "errors": []}
            if stored.get("new_event_reactivated") is True:
                result["defer"] = True
            return result
        if status == "blocked":
            rejection_code = str(action.get("rejection_code") or "")
            errors = (
                [rejection_code]
                if rejection_code in SERVER_REJECTION_CODES
                else ["server_rejection"]
            )
            return {"status": "blocked", "errors": errors}
        if status == "reconcile_pending":
            return {"status": "reconcile_pending", "errors": ["ground_truth_unavailable"]}
        raise RuntimeError(f"unexpected reconciled action state: {status}")

    @staticmethod
    def _require_action_binding(action: dict[str, Any], queue_item: dict[str, Any]) -> None:
        if (
            str(action.get("thread_id") or "") != str(queue_item.get("talkroom_id") or "")
            or str(action.get("thread_url") or "") != str(queue_item.get("talkroom_url") or "")
        ):
            raise ValueError("queue item does not identify claimed action")

    def prepare(
        self,
        *,
        action: dict[str, Any],
        queue_item: dict[str, Any],
        outgoing_body: str,
        now: int,
    ) -> dict[str, Any]:
        self._require_action_binding(action, queue_item)
        stored = self.outbox.prepare_intent(
            int(action["action_id"]),
            owner=str(action["owner"]),
            fencing_token=int(action["fencing_token"]),
            outgoing_body=outgoing_body,
            now=now,
            origin_at=int(_timestamp(queue_item["origin_at"]).timestamp()),
        )
        return {
            "action_id": int(action["action_id"]),
            "revision": int(stored["revision"]),
            "owner": str(action["owner"]),
            "fencing_token": int(action["fencing_token"]),
            "event_key": str(queue_item.get("event_key") or ""),
            "talkroom_id": str(action["thread_id"]),
            "talkroom_url": str(action["thread_url"]),
            "origin_at": _timestamp(queue_item["origin_at"]).isoformat(),
            "outgoing_hash": str(stored["outgoing_hash"]),
        }

    def authorize_click(
        self,
        *,
        intent: dict[str, Any],
        now: int,
        lease_seconds: int = POST_CLICK_LEASE_SECONDS,
    ) -> dict[str, Any]:
        return self.outbox.mark_click_started(
            int(intent["action_id"]),
            int(intent["revision"]),
            owner=str(intent["owner"]),
            fencing_token=int(intent["fencing_token"]),
            now=now,
            lease_seconds=lease_seconds,
        )

    def pre_click_failure(self, *, intent: dict[str, Any], now: int) -> dict[str, Any]:
        return self.outbox.record_pre_click_failure(
            int(intent["action_id"]),
            owner=str(intent["owner"]),
            fencing_token=int(intent["fencing_token"]),
            now=now,
        )

    def finalize(
        self,
        *,
        intent: dict[str, Any],
        before: dict[str, Any],
        after: dict[str, Any],
        observed_at: int,
    ) -> dict[str, Any]:
        result = verify_reply(intent, before, after)
        result["action_id"] = int(intent["action_id"])
        result["revision"] = int(intent["revision"])
        result["origin_at"] = str(intent["origin_at"])
        if result["verified"] is True:
            seller_sent_at = int(_timestamp(result["seller_sent_at"]).timestamp())
            action = self.outbox.reconcile(
                int(intent["action_id"]),
                thread_url=str(result["thread_url"]),
                outgoing_hash=str(result["outgoing_hash"]),
                seller_sent_at=seller_sent_at,
                last_sender=str(result["last_sender"] or "system"),
                observed_at=observed_at,
                authoritative_absent=False,
            )
            if action["state"] != "replied":
                raise RuntimeError("verified reply did not reach replied state")
            return result
        rejection_codes = [
            str(error)
            for error in result.get("errors", [])
            if str(error) in SERVER_REJECTION_CODES
        ]
        self.outbox.record_delivery_unknown(
            int(intent["action_id"]),
            owner=str(intent["owner"]),
            fencing_token=int(intent["fencing_token"]),
            now=observed_at,
            rejection_code=rejection_codes[0] if len(rejection_codes) == 1 else None,
        )
        return result
