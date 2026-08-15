#!/usr/bin/env python3
"""Ask for one follow-up, and refuse to send it when the live thread says no.

Shape borrowed from ``reply_composer.RunnerComposer`` -- same runner, same evidence
contract, same length bound -- because a follow-up differs from a first reply in exactly
one thing: what the model is asked for. Duplicating the sandbox would mean two places to
fix the next time a composer fails only in production.

Two refusals wrap the model call, and the order is the point:

Before, ``stop_signal`` reads the thread the browser just opened. A buyer who said no gets
no draft at all -- not a rejected one, none -- because the model has nothing appropriate to
write and spending a call on it invites a body that talks past a refusal.

After, ``followup_gate`` reads what came back. The model is told not to promise an unpaid
deliverable, but the reason this lane exists is that a prompt is a request and the request
was not enough the first time: kiki_1115 was promised the work free, 本日中, and stopped
answering.

A refusal raises ``FollowupRefused`` rather than returning an empty string, so the lane
records why a thread was skipped instead of typing silence into a talkroom.
"""
from __future__ import annotations

from typing import Any

import os
import sys

# Loaded dynamically by reply_lane, which uses spec_from_file_location and does not
# put this directory on the path. Importing a sibling then fails with
# ModuleNotFoundError -- measured, not guessed. Running as a script happens to work
# because sys.path[0] is already here, and depending on that is depending on how the
# caller was launched.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import followup_draft
import followup_gate
import stop_signal


class FollowupRefused(Exception):
    """This thread gets no follow-up this pass, and says why.

    ``spent_model_call`` decides whether the lane's send slot is refunded. Refusing before
    the prompt is built costs nothing and the slot must go back, or one refused thread
    starves every other buyer in the pass -- the exact failure that left seven people
    waiting for days in August. Refusing what the model returned did cost a call, and
    pretending otherwise would let a lane that produces only violations loop unbounded.
    """

    def __init__(self, reason: str, evidence: str = "", *, spent_model_call: bool = False):
        super().__init__(reason if not evidence else f"{reason}: {evidence}")
        self.reason = reason
        self.evidence = evidence
        self.spent_model_call = spent_model_call


def _conversation(context: Any) -> Any:
    if not isinstance(context, dict):
        return None
    for key in ("messages", "conversation", "thread_messages"):
        value = context.get(key)
        if value:
            return value
    return None


def followup_prompt_for(context: Any) -> str:
    """The instructions for this thread, refusing before the model is paid for.

    ``followups_sent`` and ``silent_days`` ride on the context the lane hands over; both
    default to the conservative reading (a first touch, silence unknown) rather than an
    optimistic one.
    """
    conversation = _conversation(context)
    stopped = stop_signal.stopped_by(conversation)
    if stopped:
        raise FollowupRefused("stopped:" + stopped["reason"], stopped["text"])
    data = context if isinstance(context, dict) else {}
    sent = data.get("followups_sent")
    sent = int(sent) if isinstance(sent, int) and sent >= 0 else 0
    days = data.get("silent_days")
    days = float(days) if isinstance(days, (int, float)) else 0.0
    return followup_draft.followup_prompt(
        conversation=conversation,
        followups_sent=sent,
        silent_days=days,
    )


def check_composed(context: Any, body: Any) -> str:
    """The body, or a refusal naming the rule it broke."""
    data = context if isinstance(context, dict) else {}
    decision = followup_gate.decide(
        conversation=_conversation(context),
        body=body,
        silent_days=data.get("silent_days"),
    )
    if not decision.get("ok"):
        raise FollowupRefused(
            str(decision.get("reason") or "refused"),
            str(decision.get("evidence") or ""),
            spent_model_call=True,
        )
    return str(body).strip()


def guarded(compose: Any) -> Any:
    """Wrap a composer so what it returns still has to pass the gate."""

    def composed(context: dict[str, Any]) -> str:
        return check_composed(context, compose(context))

    return composed
