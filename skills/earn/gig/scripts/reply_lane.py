#!/usr/bin/env python3
"""Autonomous multi-thread orchestration for the Coconala reply queue."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AwaitingBuyer(ValueError):
    """The last word in this thread is already ours.

    Raised by reply_composer before any model call or browser action. It is not a failure of
    the lane, of the browser or of the buyer -- there is simply nothing to say until they
    answer -- and counting it as one made every pass look broken while it behaved correctly.
    """


# reply_composer is loaded dynamically by every caller, so it cannot import this class
# without a cycle. Matching its exact refusal text is the bridge; production must get the
# same slot-refund the typed exception gets, or the fix only exists in tests.
AWAITING_BUYER_TEXT = "reply composition requires buyer-last conversation"

# Measured 2026-08-06 03:00 on thread 93000002: the page loaded, we were logged in
# (title="メッセージ詳細 | マイページ | ココナラ"), and it contained no textarea, no text input
# and no contenteditable -- only /users_blocks/add and /users_blocks/remove. A closed or
# blocked conversation has no reply box, and no number of retries will grow one. Retrying it
# spent the pass's single send every time, so the buyers who could be answered never were.
MISSING_COMPOSER_TEXT = "missing_message_input"


def _has_no_reply_box(error: BaseException) -> bool:
    return MISSING_COMPOSER_TEXT in str(error)


PAID_TALKROOM_REFUSAL_TEXT = "paid_talkroom_write_refused"


def _is_paid_talkroom_refusal(error: BaseException) -> bool:
    return PAID_TALKROOM_REFUSAL_TEXT in str(error)


class _FollowupContext:
    """A reply browser that also tells the composer what the queue knew.

    Delegates everything; only ``read_before`` differs, merging the thread's follow-up
    history into the context the composer receives. The browser's own keys win, so a
    field the page actually observed is never overwritten by the queue's older idea of it.
    """

    def __init__(self, browser: Any, item: dict[str, Any]):
        self._browser = browser
        self._item = item

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)

    # Explicit, because __getattr__ cannot serve these: Python looks up dunder methods on
    # the type, never the instance. The lane opens the browser with a `with` block, so the
    # first real question to a paying buyer died here with
    # TypeError: '_FollowupContext' object does not support the context manager protocol.
    def __enter__(self):
        self._browser.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._browser.__exit__(*exc_info)

    def read_before(self):
        context, before = self._browser.read_before()
        if isinstance(context, dict):
            merged = {
                "followups_sent": self._item.get("followups_sent"),
                "silent_days": self._item.get("silent_days"),
                # The build agent's diagnosis, for a blocked paid order. Absent on a
                # follow-up, where it reads as None and is never looked at.
                "blocked_state": self._item.get("blocked_state"),
            }
            merged.update(context)
            context = merged
        return context, before


class _SemanticContext:
    """Bind one cached semantic receipt to the fresh browser observation."""

    def __init__(self, browser: Any, item: dict[str, Any]):
        self._browser, self._item = browser, item
        self._browser.semantic_context_sha256 = item.get("semantic_context_sha256")
        if item.get("semantic_seller_debt_reply") is True:
            self._browser.semantic_expected_last_sender = "seller"
        self._browser.required_official_context = "none"

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)

    def __enter__(self):
        self._browser.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._browser.__exit__(*exc_info)

    def read_before(self):
        context, before = self._browser.read_before()
        if isinstance(context, dict):
            context = dict(context)
            context["semantic_reply_body"] = self._item.get("semantic_reply_body")
            if self._item.get("semantic_seller_debt_reply") is True:
                context["semantic_seller_debt_reply"] = True
        return context, before


class SemanticReceiptComposer:
    """Return the one body already authorized by the semantic judgement."""

    uses_model = False

    @staticmethod
    def nothing_to_say_reason(context: dict[str, Any]) -> str | None:
        rows = context.get("conversation") if isinstance(context, dict) else None
        if isinstance(rows, list) and rows:
            latest = rows[-1]
            if isinstance(latest, dict) and (latest.get("role") or latest.get("side")) == "seller":
                if context.get("semantic_seller_debt_reply") is True:
                    return None
                return "seller_last"
        return None

    def __call__(self, context: dict[str, Any]) -> str:
        body = context.get("semantic_reply_body") if isinstance(context, dict) else None
        if type(body) is not str or not body.strip() or len(body.strip()) > 1000:
            raise ValueError("semantic_reply_body_invalid")
        return body.strip()


def _followup_refusal(error: BaseException):
    """The error, if it is a follow-up refusal rather than a fault.

    Identified by shape rather than by class: followup_composer is loaded dynamically, so
    importing its exception here would be a cycle, and an ``isinstance`` against a
    separately-loaded module object would silently never match.
    """
    if type(error).__name__ != "FollowupRefused":
        return None
    if not isinstance(getattr(error, "reason", None), str):
        return None
    return error


def _as_awaiting_buyer(compose):
    def composed(context):
        try:
            return compose(context)
        except AwaitingBuyer:
            raise
        except ValueError as error:
            if AWAITING_BUYER_TEXT in str(error):
                raise AwaitingBuyer(str(error)) from error
            raise

    nothing_to_say_reason = getattr(compose, "nothing_to_say_reason", None)
    if callable(nothing_to_say_reason):
        # Preserve the executor hook across the ValueError adapter. Without it,
        # seller-last threads lose their terminal closure and are sent again.
        composed.nothing_to_say_reason = nothing_to_say_reason
    composed.uses_model = getattr(compose, "uses_model", True)
    return composed


def _load_local(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from reply_executor import execute_reply
except ModuleNotFoundError:  # imported directly by unit-test loaders
    execute_reply = _load_local("reply_executor").execute_reply

try:
    from project_effect_fence import write_fenced_talkroom_ids
except ModuleNotFoundError:  # imported directly by unit-test loaders
    write_fenced_talkroom_ids = _load_local("project_effect_fence").write_fenced_talkroom_ids

# EV1 instrumentation. Catches everything: a broken trajectory.py must not stop a reply.
try:
    from trajectory import record as record_trajectory
except Exception:  # noqa: BLE001 - instrumentation may never break its host
    try:
        record_trajectory = _load_local("trajectory").record
    except Exception:  # noqa: BLE001
        def record_trajectory(**_kwargs: Any) -> None:  # type: ignore[misc]
            return None


def fenced_ids_from_file(path: Any) -> frozenset[str] | None:
    """The fenced rooms named by a registry file, or None when it cannot be read.

    None is deliberate and travels all the way to execute_reply, which refuses on it. A
    missing or corrupt registry means this pass cannot tell a paid room from an enquiry,
    and TODO 3c's whole point is that the lane does not guess in that situation.
    """
    if path is None:
        return None
    try:
        registry = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(registry, dict):
        return None
    return write_fenced_talkroom_ids(registry)


def _verified_event(
    *, action: dict[str, Any], item: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Project a verified result to bounded, Telegram-safe metadata."""
    event = {
        "action_id": int(result.get("action_id") or action["action_id"]),
        "revision": int(result.get("revision") or action["revision"]),
        "talkroom_id": str(item["talkroom_id"]),
        "origin_at": str(result.get("origin_at") or item["origin_at"]),
        "seller_sent_at": str(result["seller_sent_at"]),
        "status": "replied",
    }
    if event["action_id"] <= 0 or event["revision"] <= 0:
        raise ValueError("verified reply event lacks positive action revision")
    return event


def process_queue(
    *,
    controller: Any,
    queue: dict[str, Any],
    compose: Any,
    browser_factory: Any,
    owner_prefix: str,
    clock: Any,
    paid_talkroom_ids: Any,
    max_model_calls: int | None = None,
    target_action_id: int | None = None,
) -> dict[str, Any]:
    """Process every current pending thread; repeated projections become no-ops."""
    if queue.get("status") == "collector_unhealthy":
        raise ValueError("collector queue is unhealthy")
    compose = _as_awaiting_buyer(compose)
    if queue.get("status") not in {"ready", "queue_empty"}:
        raise ValueError("invalid reply queue status")
    summary = {
        "status": "completed",
        "replied": 0,
        "already_delivered": 0,
        "reconciled": 0,
        "requeued": 0,
        "reconcile_pending": 0,
        "pending_verify": 0,
        "dlq": 0,
        "nothing_to_say": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
        "deferred": 0,
        "awaiting_buyer": 0,
        "unrepliable": 0,
        "near_duplicate": 0,
        "model_calls": 0,
        "errors": [],
        "events": [],
        "dlq_events": [],
    }
    items = list(queue.get("items", []))
    queued_threads = {
        str(item.get("talkroom_id") or "")
        for item in items
        if isinstance(item, dict)
    }
    reconciliations = {
        str(action["thread_id"]): action
        for action in controller.reconciliation_actions()
        if target_action_id is None or int(action["action_id"]) == target_action_id
    }
    for thread_id, action in reconciliations.items():
        if thread_id in queued_threads:
            continue
        event_key = str(action.get("event_key") or "")
        items.append({
            "event_key": event_key,
            "covered_event_keys": [event_key] if event_key else [],
            "talkroom_id": thread_id,
            "talkroom_url": str(action["thread_url"]),
            "origin_at": datetime.fromtimestamp(
                int(action["intent_origin_at"]), timezone.utc
            ).isoformat(),
        })
        queued_threads.add(thread_id)
    # Bug (measured 2026-09-04): this used to require "status == queue_empty and not
    # items" before folding in the durable backlog. A busy shop's fresh scan almost
    # always finds at least one item, so that condition was true on ~0 passes and 97
    # threads sat in connector_actions state=pending for up to 30 days, re-queued but
    # never selected. queued_threads already dedupes against whatever the fresh scan
    # found, so folding the backlog in on every non-targeted pass is safe -- only the
    # targeted single-thread path (semantic_ssot is True) must stay excluded, since it
    # exists to process exactly one thread, not the whole backlog.
    if queue.get("semantic_ssot") is not True:
        for action in controller.pending_actions():
            thread_id = str(action["thread_id"])
            if thread_id in queued_threads:
                continue
            event_key = str(action.get("event_key") or "")
            event_observed_at = action.get("event_observed_at")
            if not event_key or type(event_observed_at) is not int:
                raise ValueError("durable pending action lacks event identity")
            items.append({
                "event_key": event_key,
                "covered_event_keys": [event_key],
                "talkroom_id": thread_id,
                "talkroom_url": str(action["thread_url"]),
                "origin_at": datetime.fromtimestamp(
                    event_observed_at, timezone.utc
                ).isoformat(),
            })
            queued_threads.add(thread_id)
    def process_one(item: dict[str, Any], thread_id: str) -> bool | None:
        reconciliation = reconciliations.get(thread_id)
        if reconciliation is not None:
            with browser_factory(reconciliation, item) as browser:
                transient, observation = browser.read_before()
            if isinstance(transient, dict):
                transient.clear()
            reconciled = controller.reconcile_observation(
                action=reconciliation,
                observation=observation,
                observed_at=clock(),
            )
            reconciliation_status = str(reconciled.get("status") or "")
            if reconciliation_status == "replied":
                summary["replied"] += 1
                summary["reconciled"] += 1
                summary["events"].append(_verified_event(
                    action=reconciliation, item=item, result=reconciled,
                ))
            elif reconciliation_status == "requeued":
                summary["requeued"] += 1
                if reconciled.get("defer") is True:
                    return
            elif reconciliation_status == "already_delivered":
                # Terminal closure: the content is already in the thread, so the
                # intent is satisfied without a resend (Stripe idempotency).
                summary["already_delivered"] += 1
                summary["reconciled"] += 1
            elif reconciliation_status == "blocked":
                summary["blocked"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "blocked",
                    "errors": list(reconciled.get("errors") or []),
                })
                return
            elif reconciliation_status == "dlq":
                # Terminal quarantine: delivery could not be proven either way
                # after bounded attempts; never blind-retried (dead-letter queue).
                summary["dlq"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "dlq",
                    "errors": list(reconciled.get("errors") or []),
                })
                return
            elif reconciliation_status == "reconcile_pending":
                summary["reconcile_pending"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": reconciliation_status,
                    "errors": list(reconciled.get("errors") or []),
                })
                return
            else:
                raise RuntimeError(
                    f"reply reconciliation ended in unexpected status: {reconciliation_status}"
                )
        action = controller.pending_action_for_thread(thread_id)
        if action is None:
            if reconciliation is None:
                event_key = item.get("event_key")
                try:
                    lifecycle = controller.outbox.action_lifecycle_for_event(
                        event_key, thread_id
                    )
                except ValueError:
                    lifecycle = None
                    exact_error = "exact_event_invalid"
                except Exception as error:
                    # This catch is scoped to the lookup only. Dynamic CLI/test
                    # loaders can give InvalidTransition distinct class identities,
                    # so match that exact type name; re-raise everything else.
                    if type(error).__name__ == "InvalidTransition":
                        lifecycle = None
                        exact_error = "exact_event_identity_mismatch"
                    elif isinstance(error, sqlite3.Error):
                        lifecycle = None
                        exact_error = (
                            "exact_lifecycle_lookup_failed:"
                            + type(error).__name__
                        )
                    else:
                        raise
                else:
                    exact_error = "exact_event_not_found" if lifecycle is None else None
                if lifecycle is None:
                    summary["failed"] += 1
                    summary["errors"].append({
                        "talkroom_id": thread_id,
                        "status": "failed",
                        "errors": [exact_error or "exact_event_not_found"],
                    })
                    return False
                if lifecycle["state"] == "replied" or lifecycle["closure"] == "already_delivered":
                    summary["already_delivered"] += 1
                    return
                if lifecycle["closure"] == "nothing_to_say":
                    summary["nothing_to_say"] += 1
                    return
                if lifecycle["state"] == "blocked" and lifecycle["dlq_at"] is None:
                    summary["blocked"] += 1
                    summary["errors"].append({
                        "talkroom_id": thread_id,
                        "status": "blocked",
                        "errors": [lifecycle["rejection_code"] or "server_rejection"],
                    })
                    return
                if lifecycle["closure"] == "dlq" or lifecycle["dlq_at"] is not None:
                    reason = lifecycle["reason"] or "dlq"
                    summary["dlq"] += 1
                    summary["errors"].append({
                        "talkroom_id": thread_id,
                        "status": "dlq",
                        "errors": [reason],
                    })
                    return
                summary["failed"] += 1
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "failed",
                    "errors": [f"exact_event_unexpected_state:{lifecycle['state']}"],
                })
            return
        uses_model = getattr(compose, "uses_model", True) is not False
        if uses_model and max_model_calls is not None and summary["model_calls"] >= max_model_calls:
            summary["deferred"] += 1
            return
        if uses_model:
            summary["model_calls"] += 1
        owner = f"{owner_prefix}:{action['action_id']}"
        with browser_factory(action, item) as browser:
            result = execute_reply(
                controller=controller,
                queue_item=item,
                owner=owner,
                clock=clock,
                compose=compose,
                browser=browser,
                paid_talkroom_ids=paid_talkroom_ids,
                action_id=int(action["action_id"]),
            )
        status = str(result.get("status") or "")
        # EV1 (spec §4.1): the ownership signal for accident ③ -- on 2026-08-07 this lane
        # wrote into a paid room the delivery lane owned, and nothing recorded that two
        # lanes had touched one resource.
        #
        # ★ Placed after execute_reply returns, on purpose. ★ A room this lane correctly
        # refused (refuse_fenced_talkroom) raises inside execute_reply and never reaches
        # here, so a refusal is not recorded as a claim on the room. `error` IS recorded as
        # a claim: the incident's own reply-lane-result.json listed talkroom 90000002 under
        # errors, not events, and a reconstruction that ignored errors would have shown a
        # single owner for the room where two lanes collided.
        record_trajectory(
            stage="INQUIRY_REPLY", lane="reply", resource_key=f"talkroom:{thread_id}",
            action="write", reason=status,
            result=(
                "ok" if status in {"replied", "already_delivered"}
                else "error" if status in {"reconcile_pending", "duplicate_detected", "evidence_invalid"}
                else "skipped"
            ),
        )
        if status == "replied":
            summary["replied"] += 1
            summary["events"].append(_verified_event(
                action=action, item=item, result=result,
            ))
        elif status == "already_delivered":
            # Pre-send guard refused a duplicate body hash; terminal closure.
            summary["already_delivered"] += 1
        elif status == "nothing_to_say":
            # Terminal, and NOT a reply: we already spoke last, so the entry
            # leaves the queue with a recorded reason instead of being retried on
            # the next 300s tick. The thread is not marked replied-to; a new
            # buyer message enqueues a fresh action.
            summary["nothing_to_say"] += 1
            if uses_model:
                summary["model_calls"] = max(0, summary["model_calls"] - 1)
        elif status in {"reconcile_pending", "duplicate_detected", "evidence_invalid"}:
            # Sent (or possibly sent) but the read-back could not prove delivery:
            # pending_verify, resolved by the next detector cycle. Never resent
            # blindly in this pass.
            summary["pending_verify"] += 1
            summary["errors"].append({
                "talkroom_id": thread_id,
                "status": "pending_verify",
                "errors": list(result.get("errors") or []),
            })
        elif status == "queue_empty":
            summary["skipped"] += 1
        elif status == "near_duplicate_suppressed":
            # Nothing was sent, so the slot goes back -- the same rule that awaiting_buyer
            # and unrepliable already follow. Counting this as a failure would raise a
            # false alarm about a lane behaving correctly, and letting it keep the slot
            # would starve the buyers who are owed an actual reply.
            summary["near_duplicate"] += 1
            summary["model_calls"] = max(0, summary["model_calls"] - 1)
            summary["errors"].append({
                "talkroom_id": thread_id,
                "status": "near_duplicate_suppressed",
                "errors": list(result.get("errors") or []),
            })
        else:
            raise RuntimeError(f"reply action ended in unexpected status: {status}")

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("invalid reply queue item")
        thread_id = str(item.get("talkroom_id") or "")
        try:
            lookup_ok = process_one(item, thread_id)
        except AwaitingBuyer:
            # Their turn, not ours. reply_composer refuses a thread whose last message is
            # already ours, before any model call and before the browser opens, so nothing
            # was spent and nothing can be said. Give the slot back: on 2026-08-06 one such
            # thread consumed the pass's single send every time and deferred the seven
            # buyers who were actually owed a reply, for days.
            summary["awaiting_buyer"] += 1
            summary["model_calls"] = max(0, summary["model_calls"] - 1)
        except Exception as error:
            if _is_paid_talkroom_refusal(error):
                # TODO 3c. The room belongs to PAID_WORK, or this pass could not tell. Not a
                # lane failure and not a buyer we lost -- the correct outcome, which still
                # has to be counted, because a room that silently leaves this lane looks
                # exactly like a room the code dropped. The slot goes back so a fenced room
                # cannot starve the pre-purchase enquiries this lane exists to answer.
                summary["paid_talkroom_refused"] = (
                    summary.get("paid_talkroom_refused", 0) + 1
                )
                summary["model_calls"] = max(0, summary["model_calls"] - 1)
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "paid_talkroom_refused",
                    "errors": [str(error)[:300]],
                })
                continue
            refusal = _followup_refusal(error)
            if refusal is not None:
                # A buyer who said no, or a draft that broke a platform rule. Neither is a
                # lane failure, and both have to be visible: a thread that leaves the
                # pipeline without a reason is indistinguishable from a bug eating buyers.
                summary["followup_refused"] = summary.get("followup_refused", 0) + 1
                if not getattr(refusal, "spent_model_call", False):
                    summary["model_calls"] = max(0, summary["model_calls"] - 1)
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "reason": refusal.reason,
                    "evidence": refusal.evidence,
                })
                continue
            if _has_no_reply_box(error):
                # No composer on the page at all. Nothing was sent, so give the slot back and
                # move to the next buyer in this same pass -- the diagnosis stays in errors so
                # the closed thread is still visible rather than silently dropped.
                summary["unrepliable"] += 1
                summary["model_calls"] = max(0, summary["model_calls"] - 1)
                summary["errors"].append({
                    "talkroom_id": thread_id,
                    "status": "unrepliable",
                    "errors": [f"{type(error).__name__}: {str(error)[:300]}"],
                })
                continue
            # Bulkhead (live incident gig-pass-1785538800): one message's
            # verification crash must not kill the lane and silence every other
            # breached thread. The failure becomes a per-message closure; the
            # connector state machine has already parked the action safely
            # (pending via pre-click failure, or reconcile_pending post-click).
            summary["failed"] += 1
            entry = {
                "talkroom_id": thread_id,
                "status": "failed",
                "errors": [f"{type(error).__name__}: {str(error)[:200]}"],
            }
            # Parking it safely is not the same as being able to finish it. Count
            # the streak durably so the NEXT process (300s later, fresh memory)
            # can tell "flaky once" from "cannot ever succeed".
            #
            # Inside the bulkhead, so it gets the bulkhead's own guarantee: a
            # locked database while counting a failure must not escalate one
            # thread's failure into a lane-wide crash. Losing a tick of the count
            # only delays the bound; raising here would defeat it entirely.
            try:
                streak = controller.note_failure(
                    thread_id=thread_id, error=error, now=clock(),
                )
            except Exception as bookkeeping_error:
                entry["errors"].append(
                    f"failure_bookkeeping_unavailable: {type(bookkeeping_error).__name__}"
                )
                summary["errors"].append(entry)
                continue
            entry["consecutive"] = int(streak["consecutive"])
            entry["error_class"] = str(streak["error_class"])
            summary["errors"].append(entry)
            if streak.get("dead_lettered") is True:
                summary["dlq"] += 1
                summary["dlq_events"].append({
                    "action_id": int(streak["action_id"]),
                    "talkroom_id": thread_id,
                    "reason": str(streak["reason"]),
                    "error_class": str(streak["error_class"]),
                    "consecutive": int(streak["consecutive"]),
                    "closed_at": int(streak["first_at"]),
                })
        else:
            # Any pass that did not raise breaks the run of identical failures.
            # A failure to forget must not undo a thread that just succeeded: the
            # worst case is one stale count, which the next success clears.
            if lookup_ok is not False:
                try:
                    controller.clear_failure_streak(thread_id)
                except Exception as bookkeeping_error:
                    summary["errors"].append({
                        "talkroom_id": thread_id,
                        "status": "streak_not_cleared",
                        "errors": [type(bookkeeping_error).__name__],
                    })
    if summary["reconcile_pending"] or summary["pending_verify"] or summary["failed"]:
        summary["status"] = "reconcile_pending"
    return summary


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
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--cdp-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--owner-prefix")
    parser.add_argument("--hidden-browser", action="store_true")
    parser.add_argument(
        "--fences",
        type=Path,
        default=None,
        help="project_effect_fence registry naming the talkrooms another lane owns; "
             "without it, or when it cannot be read, this lane sends nothing (TODO 3c)",
    )
    parser.add_argument("--max-model-calls", type=int, default=1, help="0 processes the finite queue without an item cap")
    # A follow-up runs through this same lane because it is the same act -- one message
    # into one talkroom, under the same outbox fencing and the same near-duplicate guard.
    # Only what the model is asked for changes, plus a refusal gate that reads the live
    # thread for a buyer who already said no.
    parser.add_argument("--followup", action="store_true")
    # A blocked paid order asking its buyer what to build. Same act again -- one message,
    # one talkroom, the same fencing -- but the buyer has already paid, so the prompt is
    # an apology and a list of what is needed, not a sales message.
    parser.add_argument("--ask-buyer", action="store_true")
    parser.add_argument("--target-action-id", type=int)
    args = parser.parse_args()
    if args.max_model_calls < 0:
        parser.error("--max-model-calls must be at least 0")
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    action_module = _load_local("reply_action")
    controller = action_module.ReplyActionController(args.database, args.manifest)
    try:
        if (
            not queue.get("items")
            and queue.get("status") == "queue_empty"
            and not controller.reconciliation_actions()
            and not controller.pending_actions()
        ):
            result = process_queue(
                controller=controller,
                queue=queue,
                compose=lambda _: (_ for _ in ()).throw(AssertionError("model must not run")),
                browser_factory=lambda *_: (_ for _ in ()).throw(AssertionError("browser must not run")),
                owner_prefix=args.owner_prefix or "gig-reply-empty",
                clock=lambda: int(time.time()),
                # Nothing to process, so nothing to fence; this branch already refuses to
                # run a model or open a browser. Reading the registry here would let a
                # broken file turn an empty pass into a failed one.
                paid_talkroom_ids=frozenset(),
                max_model_calls=args.max_model_calls or None,
            )
        else:
            browser_module = _load_local("coconala_reply_browser")
            prompt_builder = None
            task_label = "gig-reply-compose"
            semantic_mode = queue.get("semantic_ssot") is True and not (args.followup or args.ask_buyer)
            if semantic_mode:
                composer = SemanticReceiptComposer()
            elif args.followup:
                followup_module = _load_local("followup_composer")
                prompt_builder = followup_module.followup_prompt_for
                task_label = "gig-followup-compose"
            elif args.ask_buyer:
                ask_module = _load_local("ask_buyer")
                prompt_builder = lambda context: ask_module.question_prompt(
                    state=(context or {}).get("blocked_state"),
                    conversation=(context or {}).get("messages"),
                )
                task_label = "gig-ask-buyer-compose"
            if not semantic_mode:
                composer_module = _load_local("reply_composer")
                composer = composer_module.RunnerComposer(
                    runner=args.runner,
                    schema=args.schema,
                    workdir=args.workdir,
                    prompt_builder=prompt_builder,
                    task_label=task_label,
                )
            if args.followup:
                # Guards what came back, not only what was asked for. The prompt already
                # forbids promising unpaid work and that request failed once already.
                composer = followup_module.guarded(composer)
            elif args.ask_buyer:
                # The message that created this situation was itself polite and empty, so
                # a question that asks nothing is refused rather than sent as a third one.
                inner = composer

                def composer(context: dict[str, Any]) -> str:  # noqa: F811
                    body = inner(context)
                    decision = ask_module.check_question(body)
                    if not decision.get("ok"):
                        raise ValueError(
                            "ask_buyer question rejected: "
                            + ",".join(str(v) for v in decision.get("violations") or [])
                        )
                    return str(body).strip()

            def browser_factory(action: dict[str, Any], item: dict[str, Any]):
                browser = browser_module.CoconalaCdpReplyBrowser(
                    args.cdp_helper,
                    str(item["talkroom_url"]),
                    hidden=args.hidden_browser,
                )
                if semantic_mode:
                    return _SemanticContext(browser, item)
                if not (args.followup or args.ask_buyer):
                    return browser
                # The composer is handed the browser's context, never the queue item, so
                # how long this buyer has been quiet and how many times we have already
                # written would arrive as zero on every thread -- the prompt would always
                # say "0 日 / 0 回" and the third and final message would never be written
                # as a close. The browser is the only object here that knows both.
                return _FollowupContext(browser, item)

            result = process_queue(
                controller=controller,
                queue=queue,
                compose=composer,
                browser_factory=browser_factory,
                owner_prefix=args.owner_prefix or f"gig-reply-{os.getpid()}-{uuid.uuid4().hex[:12]}",
                clock=lambda: int(time.time()),
                paid_talkroom_ids=fenced_ids_from_file(args.fences),
                max_model_calls=args.max_model_calls or None,
                target_action_id=args.target_action_id,
            )
        _atomic_json(args.output, result)
    except Exception as error:
        failure = {
            "status": "failed",
            "replied": 0,
            "already_delivered": 0,
            "reconciled": 0,
            "requeued": 0,
            "reconcile_pending": 0,
            "pending_verify": 0,
            "dlq": 0,
            "nothing_to_say": 0,
            "failed": 0,
            "blocked": 0,
            "skipped": 0,
            "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            "events": [],
            "dlq_events": [],
        }
        _atomic_json(args.output, failure)
        print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 2 if result["status"] == "reconcile_pending" else 0


if __name__ == "__main__":
    raise SystemExit(main())
