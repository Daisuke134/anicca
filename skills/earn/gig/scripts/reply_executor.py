#!/usr/bin/env python3
"""Provider-neutral ordering for one claimed Coconala reply action."""

from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


REPLY_LEASE_SECONDS = 1200


def _load_local(name: str):
    import importlib.util

    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record_transcript(
    *, talkroom_id: str, context: Any, outgoing_body: str, sent_at: int
) -> None:
    """Keep the exchange that produced this reply, so a later pass can label it.

    Best effort by construction: the recorder returns False rather than raising, and this
    ignores the result. Losing a transcript costs a future lesson; losing a reply costs a
    real buyer, and 2026-08-06 measured 24 of 30 inbox threads already sitting silent.
    """
    module = _load_local("reply_transcript")
    path = os.environ.get("GIG_REPLY_TRANSCRIPTS")
    if not path:
        # Running this suite once wrote 94 fixture rows -- talkroom_id "43",
        # outgoing_body "reply-2" -- into the real ledger that P3-3 will mine to learn
        # which wording converts. Teaching data poisoned by fixtures is worse than none:
        # it looks real. A test must not have to remember an env var, so the default
        # production path is simply unreachable while pytest is loaded.
        if "pytest" in sys.modules:
            return
        path = os.path.expanduser("~/gig/reply-transcripts.jsonl")
    module.append_transcript(
        path,
        module.transcript_row(
            talkroom_id=talkroom_id,
            context=context,
            outgoing_body=outgoing_body,
            outgoing_hash=hashlib.sha256(outgoing_body.encode("utf-8")).hexdigest(),
            sent_at=sent_at,
            status="composed",
        ),
    )


def dom_compatible_outgoing_body(value: str) -> str:
    if type(value) is not str:
        raise TypeError("composed reply must be a string")
    return value.replace("\r\n", "\n").replace("\r", "\n")


class ReplyBrowser(Protocol):
    def read_before(self) -> tuple[dict[str, Any], dict[str, Any]]: ...

    def fill(self, body: str) -> None: ...

    def click(self) -> None: ...

    def read_after(self) -> dict[str, Any]: ...

    def failure_evidence(self, error: Exception) -> dict[str, Any]: ...


def refuse_fenced_talkroom(
    *,
    queue_item: dict[str, Any],
    action: dict[str, Any],
    paid_talkroom_ids: Any,
) -> None:
    """Refuse to speak in a room that belongs to another lane. TODO 3c.

    Two lanes shared talkroom 90000002 on 2026-08-07. PAID_WORK held the requirements, the
    BLOCKED record and every gate built that day; this lane held the words on the screen,
    and it was this lane that told a paying buyer to go and read a 1879-byte document and
    reported 「こちらでさせていただきました」 over no work at all. Prompt prohibitions were
    tried three times the same day and moved the wording, not the behaviour, so the refusal
    lives here instead: the one place a reply cannot get past without going through.

    FAIL CLOSED, and here is which direction that is at THIS call site.
    ``paid_talkroom_ids`` is None when the fence registry could not be read -- the fourth
    answer paid_work_evidence.blocked_evidence_verdict added, "I could not look", which is
    not "there is nothing there". paid_work_evidence.validate_paid_work treats it as not
    deliverable, gig_pass.sh's paid_work_fresh_blocked treats it as still blocked, and
    delivery_cadence.delivery_decision treats it as do-not-deliver; all three refuse to act.
    So does this one: not knowing whether a room is paid is refused exactly like knowing it
    is. Silence from this lane costs one pass. A message with no project context, sent into
    a room where someone has already paid, costs the order.

    An unidentifiable thread is the same answer for the same reason: a send whose
    destination cannot be named cannot be checked against the fence at all.
    """
    talkroom_id = str(
        queue_item.get("talkroom_id") or action.get("thread_id") or ""
    ).strip()
    if not talkroom_id:
        raise ValueError("paid_talkroom_write_refused:unidentifiable_thread")
    if paid_talkroom_ids is None:
        raise ValueError(
            f"paid_talkroom_write_refused:membership_undeterminable:{talkroom_id}"
        )
    if talkroom_id in {str(value) for value in paid_talkroom_ids}:
        raise ValueError(f"paid_talkroom_write_refused:{talkroom_id}")


def execute_reply(
    *,
    controller: Any,
    queue_item: dict[str, Any],
    owner: str,
    clock: Callable[[], int],
    compose: Callable[[dict[str, Any]], str],
    browser: ReplyBrowser,
    paid_talkroom_ids: Any,
    lease_seconds: int = REPLY_LEASE_SECONDS,
    action_id: int | None = None,
) -> dict[str, Any]:
    """Execute compose/read/send/verify with click authority held by the controller.

    ``paid_talkroom_ids`` has no default on purpose. Every caller must say which rooms
    belong to another lane, because the one call site that forgot is the one that would
    send. A frozenset() is a real answer ("none are fenced"); None means the registry could
    not be read and nothing is sent.
    """
    action = controller.claim(
        owner=owner,
        now=clock(),
        lease_seconds=lease_seconds,
        action_id=action_id,
    )
    if action is None:
        return {
            "status": "queue_empty",
            "verified": False,
            "blind_retry_allowed": False,
            "errors": [],
        }
    intent: dict[str, Any] | None = None
    click_authorized = False
    try:
        # Before the tab is read, before a model call is spent, before an intent exists.
        # check_style below is the last free point to refuse a BODY; this is the first
        # point at which the ROOM is known, and a room that is not ours is not made ours
        # by writing a better sentence into it.
        refuse_fenced_talkroom(
            queue_item=queue_item,
            action=action,
            paid_talkroom_ids=paid_talkroom_ids,
        )
        context, before = browser.read_before()
        # Ask the composer whether a reply is owed BEFORE spending a model call.
        # "We spoke last" is a terminal finding, not a failure: closing here is
        # what stops the entry from being re-queued and re-attempted every five
        # minutes. The closure never touches seller_sent_at / the delivered-hash
        # store, so the thread is not marked replied-to and the next buyer
        # message enqueues a fresh action.
        reason = getattr(compose, "nothing_to_say_reason", None)
        if callable(reason):
            nothing_to_say = reason(context)
            if nothing_to_say:
                return controller.close_nothing_to_say(
                    action=action,
                    reason=str(nothing_to_say),
                    now=clock(),
                )
        outgoing_body = dom_compatible_outgoing_body(compose(context))
        prepared_at = clock()
        # Reuse prepared_at rather than reading the clock again: callers inject clock as a
        # finite sequence of ticks, so an extra read would starve the send path of the
        # timestamp it needs. prepared_at is also the honest value here -- it is the moment
        # this body came into existence, which is what status="composed" claims.
        _record_transcript(
            talkroom_id=str(queue_item.get("talkroom_id") or action.get("thread_id") or ""),
            context=context,
            outgoing_body=outgoing_body,
            sent_at=prepared_at,
        )
        # Saying the same thing twice is how kiki_1115 ended: a full proposal at 11:46, a
        # near-identical one at 13:01, and a buyer who had written only 「宜しくお願い致し
        # ます。」 in between. The hash guard below cannot see it -- the bodies differ
        # (measured 0.741) -- so the near-duplicate check runs first, before any state is
        # prepared. Refusing costs one pass; repeating costs the conversation.
        near_duplicate = _load_local("near_duplicate_reply")
        if near_duplicate.is_near_duplicate(
            outgoing_body, before.get("seller_messages")
        ):
            return {
                "status": "near_duplicate_suppressed",
                "verified": False,
                "blind_retry_allowed": False,
                "errors": ["outgoing body repeats our last message in this thread"],
            }
        intent = controller.prepare(
            action=action,
            queue_item=queue_item,
            outgoing_body=outgoing_body,
            now=prepared_at,
        )
        # A21 pre-send idempotency guard: never send a body hash that the live
        # thread or the outbox delivery history already shows (Stripe idempotent
        # requests). Refusing BEFORE fill/click is the only point where a
        # duplicate costs nothing.
        already_delivered = controller.close_if_already_delivered(
            intent=intent,
            before=before,
            observed_at=prepared_at,
        )
        if already_delivered is not None:
            return already_delivered
        # Last point before the words exist in the buyer's browser. The near-duplicate
        # check above asks "have I said this already"; this asks "is this even addressed to
        # a customer". Order 91000002 received 「パッケージSHA-256: f0ce...」 because nothing
        # stood here.
        style_violations = _load_local("buyer_voice").check_style(outgoing_body)
        if style_violations:
            raise ValueError(f"buyer_style_violation:{style_violations[0]}")
        verify_freshness = getattr(browser, "verify_semantic_freshness", None)
        if callable(verify_freshness):
            verify_freshness()
        browser.fill(outgoing_body)
        if callable(verify_freshness):
            verify_freshness()
        outgoing_body = ""
        controller.authorize_click(intent=intent, now=clock())
        click_authorized = True
        try:
            browser.click()
            after = browser.read_after()
        except Exception as error:
            evidence = getattr(browser, "failure_evidence", None)
            after = evidence(error) if callable(evidence) else {"status": "read_failed"}
        return controller.finalize(
            intent=intent,
            before=before,
            after=after,
            observed_at=clock(),
        )
    except Exception:
        if not click_authorized:
            controller.pre_click_failure(intent=intent or action, now=clock())
        raise
