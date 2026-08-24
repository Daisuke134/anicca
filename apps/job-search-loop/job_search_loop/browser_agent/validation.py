from __future__ import annotations

from .contracts import ObservationV1, ValidationFeedbackV1, VisibleControlV1


def validation_feedback(
    before: ObservationV1 | None,
    after: ObservationV1,
) -> ValidationFeedbackV1 | None:
    """Return rendered, value-free validation for the next model decision."""
    messages = tuple(dict.fromkeys(text.strip() for text in after.validation_text if text.strip()))
    if not messages:
        return None

    before_messages = () if before is None else before.validation_text
    folded_messages = tuple(message.casefold() for message in messages)
    related: list[VisibleControlV1] = []
    for control in after.controls:
        label = control.label.strip()
        if label and any(
            label.casefold() in message or message in label.casefold()
            for message in folded_messages
        ):
            related.append(control)

    return ValidationFeedbackV1(
        schema_version=1,
        observation_sha256=after.content_sha256,
        messages=messages,
        related_controls=tuple(related),
        changed=tuple(before_messages) != messages,
    )
