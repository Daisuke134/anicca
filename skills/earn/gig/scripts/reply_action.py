#!/usr/bin/env python3
"""Fenced lifecycle controller for one Coconala reply side effect."""

from __future__ import annotations

import importlib.util
import re
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
        ExecutorStillActive,
        SERVER_REJECTION_CODES,
    )
except ModuleNotFoundError:  # imported directly by unit-test loaders
    _outbox_module = _load_local("connector_outbox")
    ConnectorOutbox = _outbox_module.ConnectorOutbox
    ConsistencyWindowOpen = _outbox_module.ConsistencyWindowOpen
    ExecutorStillActive = _outbox_module.ExecutorStillActive
    SERVER_REJECTION_CODES = _outbox_module.SERVER_REJECTION_CODES

try:
    from reply_evidence import verify_reply
except ModuleNotFoundError:  # imported directly by unit-test loaders
    verify_reply = _load_local("reply_evidence").verify_reply


POST_CLICK_LEASE_SECONDS = 420

# A21: after this many reconcile passes that cannot prove delivery either way,
# the message is quarantined in the dead-letter queue instead of blind-looping
# (Azure dead-letter pattern; the DLQ entry is the "I need help" evidence).
DLQ_AFTER_UNRESOLVED_ATTEMPTS = 5

# E6b: after this many CONSECUTIVE identical exceptions on the same thread, the
# entry is quarantined instead of retried on the next 300s tick. Consecutive, not
# lifetime -- 412 in a row is a message that cannot succeed, three scattered over
# a week is a lane coping with a flaky site. Same bound as the reconcile budget
# above so the lane has one answer to "how many tries is enough".
DLQ_AFTER_CONSECUTIVE_FAILURES = 5


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def failure_class(error: BaseException) -> str:
    """Name the KIND of failure, stably enough to compare two runs.

    The raw message is too specific to key a streak on: the composer's budget
    error embeds live token counts, so `RuntimeError: ... daily_consumed_tokens:
    1047806` never equals itself twice and would never reach a bound. The bare
    exception type is too coarse: `missing_message_input` and a budget refusal
    are both RuntimeError and would merge into one streak. Collapsing digits and
    keeping a bounded head of the first line sits between the two.
    """
    head = str(error).strip().splitlines()
    text = head[0] if head else ""
    return f"{type(error).__name__}:{re.sub(r'[0-9]+', 'N', text)[:150]}"


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
        last_sender = str(observation.get("last_sender") or "system")
        if matches:
            seller_sent_at = None
            sent_raw = matches[0].get("sent_at")
            if sent_raw:
                seller_sent_at = int(_timestamp(sent_raw).timestamp())
            stored = None
            if len(matches) == 1:
                stored = self.outbox.reconcile(
                    int(action["action_id"]),
                    thread_url=str(observation["url"]),
                    outgoing_hash=outgoing_hash,
                    seller_sent_at=seller_sent_at,
                    last_sender=last_sender,
                    observed_at=observed_at,
                    authoritative_absent=False,
                )
            if stored is not None and str(stored["state"]) == "replied":
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
            # The exact outgoing content is visible in the thread, either more
            # than once (we already double-posted) or outside the strict click
            # window (an earlier pass delivered it).  The idempotency key is
            # delivered: close instead of retrying or swallowing (Stripe
            # idempotent requests).  Detection AFTER a duplicate is not safety;
            # the closure prevents the third copy.
            closed = self.outbox.close_already_delivered(
                int(action["action_id"]),
                outgoing_hash=outgoing_hash,
                seller_sent_at=seller_sent_at,
                last_sender=last_sender,
                observed_at=observed_at,
            )
            if str(closed["state"]) != "replied":
                raise RuntimeError("already-delivered closure did not reach replied state")
            return {
                "status": "already_delivered",
                "action_id": int(action["action_id"]),
                "revision": int(closed["revision"]),
                "seller_sent_at": str(matches[0].get("sent_at") or ""),
                "origin_at": datetime.fromtimestamp(
                    int(action["intent_origin_at"]), timezone.utc
                ).isoformat(),
                "errors": (
                    ["duplicate_outgoing_message"]
                    if len(matches) > 1
                    else ["stale_presence_outside_click_window"]
                ),
            }
        try:
            stored = self.outbox.reconcile(
                int(action["action_id"]),
                thread_url=str(observation["url"]),
                outgoing_hash=outgoing_hash,
                seller_sent_at=None,
                last_sender=last_sender,
                observed_at=observed_at,
                authoritative_absent=True,
            )
        except ConsistencyWindowOpen:
            return {
                "status": "reconcile_pending",
                "errors": ["consistency_window_open"],
            }
        except ExecutorStillActive:
            return self._unresolved(
                action, observed_at, ["executor_quiescence_unproven"]
            )
        status = str(stored["state"])
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
        if stored.get("revision_budget_exhausted") is True:
            # C1b anti-burn: the outbox already quarantined this action because it
            # spent its whole revision budget without one verified delivery. The
            # lane reports a terminal dlq instead of counting another unresolved
            # pass against a message it will never send again.
            return {"status": "dlq", "errors": ["revision_budget_exhausted"]}
        if status == "reconcile_pending":
            return self._unresolved(action, observed_at, ["ground_truth_unavailable"])
        raise RuntimeError(f"unexpected reconciled action state: {status}")

    def _unresolved(
        self, action: dict[str, Any], observed_at: int, errors: list[str]
    ) -> dict[str, Any]:
        """Count an unresolvable pass; dead-letter after the bounded attempt limit."""
        attempts = self.outbox.note_reconcile_unresolved(
            int(action["action_id"]), now=observed_at
        )
        if attempts >= DLQ_AFTER_UNRESOLVED_ATTEMPTS:
            self.outbox.move_to_dlq(
                int(action["action_id"]), reason=str(errors[0]), now=observed_at
            )
            return {"status": "dlq", "errors": list(errors)}
        return {"status": "reconcile_pending", "errors": list(errors)}

    def close_if_already_delivered(
        self,
        *,
        intent: dict[str, Any],
        before: dict[str, Any],
        observed_at: int,
    ) -> dict[str, Any] | None:
        """Refuse to send a body hash already delivered to this thread.

        Pre-send idempotency guard (Stripe idempotent requests): the live
        thread snapshot AND the outbox delivery history are both checked
        before any fill/click.  Returns the terminal closure, or ``None``
        when sending is safe.
        """
        outgoing_hash = str(intent["outgoing_hash"])
        matches: list[dict[str, Any]] = []
        messages = before.get("seller_messages")
        if isinstance(messages, list):
            for message in messages:
                if (
                    isinstance(message, dict)
                    and str(message.get("body_sha256") or "") == outgoing_hash
                ):
                    matches.append(message)
        hashes = {str(value) for value in (before.get("seller_message_hashes") or [])}
        delivered = bool(matches) or outgoing_hash in hashes
        if not delivered and not self.outbox.thread_delivered_hash(
            str(intent["talkroom_id"]), outgoing_hash
        ):
            return None
        seller_sent_at = None
        if matches and matches[0].get("sent_at"):
            seller_sent_at = int(_timestamp(matches[0]["sent_at"]).timestamp())
        last_sender = before.get("last_sender")
        if last_sender not in ("buyer", "seller", "system"):
            last_sender = "system"
        stored = self.outbox.close_already_delivered(
            int(intent["action_id"]),
            outgoing_hash=outgoing_hash,
            seller_sent_at=seller_sent_at,
            last_sender=str(last_sender),
            observed_at=observed_at,
            owner=str(intent["owner"]),
            fencing_token=int(intent["fencing_token"]),
        )
        if str(stored["state"]) != "replied":
            raise RuntimeError("already-delivered guard did not close the action")
        return {
            "status": "already_delivered",
            "verified": False,
            "action_id": int(intent["action_id"]),
            "revision": int(stored["revision"]),
            "talkroom_id": str(intent["talkroom_id"]),
            "blind_retry_allowed": False,
            "errors": [],
        }

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

    def close_nothing_to_say(
        self, *, action: dict[str, Any], reason: str, now: int
    ) -> dict[str, Any]:
        """Terminate a claimed action that has nothing to answer (not a reply)."""
        stored = self.outbox.close_nothing_to_say(
            int(action["action_id"]),
            owner=str(action["owner"]),
            fencing_token=int(action["fencing_token"]),
            reason=reason,
            now=now,
        )
        if stored["dlq_at"] is None:
            raise RuntimeError("nothing-to-say closure did not leave the queue")
        if str(stored["state"]) == "replied":
            raise RuntimeError("nothing-to-say closure must not claim a reply")
        return {
            "status": "nothing_to_say",
            "verified": False,
            "action_id": int(action["action_id"]),
            "revision": int(stored["revision"]),
            "talkroom_id": str(action["thread_id"]),
            "reason": reason,
            "blind_retry_allowed": False,
            "errors": [],
        }

    def note_failure(
        self,
        *,
        thread_id: str,
        error: BaseException,
        now: int,
        dead_letter_after: int = DLQ_AFTER_CONSECUTIVE_FAILURES,
    ) -> dict[str, Any]:
        """Count one consecutive same-class failure; quarantine at the bound."""
        return self.outbox.record_thread_failure(
            thread_id=thread_id,
            error_class=failure_class(error),
            now=now,
            dead_letter_after=dead_letter_after,
        )

    def clear_failure_streak(self, thread_id: str) -> bool:
        """A pass that did not raise proves the streak is not consecutive."""
        return self.outbox.clear_thread_failure_streak(thread_id)

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
                # Coconala renders sent_at with minute resolution, so a message
                # sent within the click minute rounds BELOW click_started_at and
                # the strict presence window refuses it. The three-point
                # read-back already proved delivery; close on the idempotency
                # key instead of crashing the lane (live incident 2026-08-01
                # 08:01 thread 93000006, the systematic source of the blind
                # reconcile_pending backlog).
                action = self.outbox.close_already_delivered(
                    int(intent["action_id"]),
                    outgoing_hash=str(result["outgoing_hash"]),
                    seller_sent_at=seller_sent_at,
                    last_sender=str(result["last_sender"] or "system"),
                    observed_at=observed_at,
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
