#!/usr/bin/env python3
"""The only way text reaches a paid buyer — spec §0.1.6 (P1a-2).

`compose_reply` takes an artifact and returns the message. It does not take a message.
There is no parameter through which a model-written sentence can reach the buyer, so the
question "did the agent promise something it cannot back up" stops being a matter of
prompt discipline and becomes a matter of what the function signature permits.

The sentence this closes, verbatim from the talkroom: 「本日中に完了予定をご連絡します」,
sent four times across 2026-08-03/04 with no schedule behind it, the fourth after three
misses. Here the delivery date is read out of `revised_schedule.due_date`; with the field
absent the template cannot be filled and the call raises instead of sending.

A rejected alternative, from the adversarial pass in §0.1.6: scan outbound text for
commitment grammar (dates, 「します」, deliverable nouns) and block it unless an artifact
hash resolves. That filter is adversarial to itself — false positives block legitimate
replies and push the lane back into the silence we are trying to end. Rendering from
fields removes the free text that would have needed filtering.

Buyer-facing rules, enforced by tests rather than by convention: no talkroom or artifact
identifiers, no hashes, no file paths, no English jargon, and no delivery date in a class
that carries none. A worksheet asks questions; it does not also promise a completion time.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_ARTIFACT_MODULE_PATH = Path(__file__).resolve().parent / "paid_conversation_artifact.py"


def _artifact_module():
    spec = importlib.util.spec_from_file_location(
        "paid_conversation_artifact", _ARTIFACT_MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PromiseWithoutArtifact(Exception):
    """Raised when a message would have to assert something the artifact does not carry.

    Raising rather than returning an empty string is deliberate: an empty return would be
    silently sendable as "no reply this pass", which is the original failure. The caller
    must convert this into a typed refusal with a blocker ID.
    """


def _japanese_date(iso: str) -> str:
    """`2026-08-06` -> `8月6日`. Buyers do not read ISO dates, and a slash would be a path."""
    try:
        _, month, day = iso.split("-")
    except (ValueError, AttributeError) as exc:
        raise PromiseWithoutArtifact(f"due_date is not a date: {iso!r}") from exc
    return f"{int(month)}月{int(day)}日"


def _worksheet(artifact: dict[str, Any]) -> str:
    lines = [f"{artifact['title']}について、以下の点をご確認いただけますでしょうか。", ""]
    for i, question in enumerate(artifact["questions"], 1):
        lines.append(f"{i}. {question}")
    lines += ["", "ご回答をいただき次第、続きを進めてまいります。"]
    return "\n".join(lines)


def _schedule(artifact: dict[str, Any]) -> str:
    when = _japanese_date(artifact["due_date"])
    return "\n".join(
        [
            f"{artifact['title']}についてご連絡いたします。",
            "",
            f"完成予定を{when}とさせていただきたく存じます。",
            "ご都合が合わない場合は、お知らせいただけますでしょうか。",
        ]
    )


def _cancellation(artifact: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"{artifact['title']}についてご連絡いたします。",
            "",
            f"理由: {artifact['reason']}",
            f"ご返金額: {int(artifact['refund_jpy']):,}円",
            "",
            "ご期待に沿えず申し訳ございません。",
        ]
    )


def _final_accounting(artifact: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"{artifact['title']}についてご連絡いたします。",
            "",
            f"対象期間: {artifact['period']}",
            f"ご請求額: {int(artifact['total_jpy']):,}円",
            "",
            "これまでのお取引に感謝申し上げます。",
        ]
    )


_TEMPLATES = {
    "question_worksheet": _worksheet,
    "revised_schedule": _schedule,
    "cancellation_rationale": _cancellation,
    "final_accounting": _final_accounting,
}


def compose_reply(artifact: dict[str, Any]) -> str:
    """Render the buyer-facing message for this artifact, or refuse to produce one.

    The single parameter is the whole point. A second parameter carrying text would be the
    hole this module exists to close, and a test asserts the signature stays this narrow.
    """
    ok, errors = _artifact_module().validate(artifact)
    if not ok:
        raise PromiseWithoutArtifact("; ".join(errors))

    template = _TEMPLATES.get(artifact["artifact_class"])
    if template is None:
        raise PromiseWithoutArtifact(
            f"no buyer-facing template for {artifact['artifact_class']!r}"
        )
    return template(artifact)
