#!/usr/bin/env python3
"""The artifact a paid-buyer message is rendered from — spec §0.1.6 (P1a-1).

The paid-buyer lane never composes a message as its first act. Every pass over a paid
talkroom begins by materializing an artifact, and the outbound sentence is interpolated
from that artifact's fields. "8/6 に納品します" is rendered from `due_date`; if `due_date`
is absent the sentence cannot be constructed at all. A promise is a projection of an
artifact, not a claim about one.

What this is designed against, concretely: through 24 consecutive hourly passes on
2026-08-04 the loop sent 「確認いたします」 and 「本日中に完了予定をご連絡します」 with no
artifact behind either sentence, while a paying customer waited. Prompt wording did not
stop it, so the constraint moves into the data.

The seductive wrong version, named during adversarial ideation before any code was
written (§0.1.6): let a three-line status snapshot count as the artifact, which unlocks
the lane immediately. It also legalizes content-free deliverables — the artifact check
passes while the buyer still gets nothing, which is the original bug with a ledger row
attesting that everything is fine. The substance predicate below is the answer: an
artifact must name which buyer-visible fact it changes, so "I wrote a note" is not enough.
"""

from __future__ import annotations

from typing import Any

# One action, one artifact class. The binding is the authorization: you cannot request an
# extension while holding a question worksheet, because the thing that justifies the action
# is the artifact itself.
ARTIFACT_CLASS_FOR_ACTION: dict[str, str] = {
    "ask_buyer": "question_worksheet",
    "request_extension": "revised_schedule",
    "cancel_request": "cancellation_rationale",
    "end_subscription": "final_accounting",
}

ARTIFACT_CLASSES: frozenset[str] = frozenset(ARTIFACT_CLASS_FOR_ACTION.values())

# The only facts that count as change. Deliberately the four things a buyer can observe
# from their side of the talkroom — internal counters, retries and state transitions are
# excluded on purpose, because an artifact that only moves our own numbers is the
# content-free deliverable this module exists to refuse.
BUYER_VISIBLE_FIELDS: frozenset[str] = frozenset(
    {"scope", "date", "deliverable_state", "price"}
)

# Fields every artifact carries regardless of class.
_COMMON_REQUIRED: tuple[str, ...] = ("artifact_class", "talkroom_id", "title", "delta")

# Per class, the fields without which the outbound sentence cannot be rendered.
_CLASS_REQUIRED: dict[str, tuple[str, ...]] = {
    "question_worksheet": ("questions",),
    "revised_schedule": ("due_date",),
    "cancellation_rationale": ("reason", "refund_jpy"),
    "final_accounting": ("period", "total_jpy"),
}

# Fields that must be a non-empty sequence rather than merely present. A worksheet with
# `questions: []` is not a worksheet; it is a status note wearing one's name.
_NON_EMPTY_SEQUENCES: frozenset[str] = frozenset({"questions", "delta"})


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def validate(artifact: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (ok, errors). Errors name the offending field so callers can act on them.

    Every error string contains the field name. The typed-refusal path upstream matches on
    those names, so a rejection can be reported to the buyer's blocker ID rather than
    disappearing as a silent skip.
    """
    errors: list[str] = []

    cls = artifact.get("artifact_class")
    if cls not in ARTIFACT_CLASSES:
        errors.append(
            f"artifact_class must be one of {sorted(ARTIFACT_CLASSES)}, got {cls!r}"
        )

    for field in _COMMON_REQUIRED:
        if _is_blank(artifact.get(field)):
            errors.append(f"{field} is required and must not be empty")

    # The substance predicate. An artifact that changes nothing the buyer can see is not
    # evidence of work, and allowing it would turn a silence failure into a noise failure.
    delta = artifact.get("delta")
    if isinstance(delta, list):
        for i, entry in enumerate(delta):
            if not isinstance(entry, dict):
                errors.append(f"delta[{i}] must be an object naming a changed field")
                continue
            field = entry.get("field")
            if field not in BUYER_VISIBLE_FIELDS:
                errors.append(
                    f"delta[{i}].field must be one of {sorted(BUYER_VISIBLE_FIELDS)}, "
                    f"got {field!r} — a change the buyer cannot see is not a change"
                )
    elif delta is not None:
        errors.append("delta must be a list")

    for field in _CLASS_REQUIRED.get(cls or "", ()):
        value = artifact.get(field)
        if field in _NON_EMPTY_SEQUENCES:
            if not isinstance(value, list) or len(value) == 0:
                errors.append(f"{field} is required and must not be empty for {cls}")
        elif _is_blank(value):
            errors.append(f"{field} is required for {cls}")

    return (not errors), errors


def validate_for_action(action: str, artifact: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the artifact and that it is the one this action is allowed to carry."""
    errors: list[str] = []

    expected = ARTIFACT_CLASS_FOR_ACTION.get(action)
    if expected is None:
        errors.append(
            f"action must be one of {sorted(ARTIFACT_CLASS_FOR_ACTION)}, got {action!r}"
        )
    elif artifact.get("artifact_class") != expected:
        errors.append(
            f"artifact_class for {action} must be {expected!r}, "
            f"got {artifact.get('artifact_class')!r}"
        )

    ok, field_errors = validate(artifact)
    errors.extend(field_errors)
    return (not errors), errors
