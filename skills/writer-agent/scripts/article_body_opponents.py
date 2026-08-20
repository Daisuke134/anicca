#!/usr/bin/env python3
"""Build a full-body, same-scope opponent receipt for body learning."""

from __future__ import annotations

import hashlib
from typing import Any


SCOPE_FIELDS = (
    "product_id",
    "channel",
    "lang",
    "editorial_form",
    "reader_scope",
)


class BodyOpponentError(ValueError):
    """Body comparison input cannot support an honest learning decision."""


def _full_body(row: dict[str, Any], *, label: str) -> str:
    text = row.get("text")
    if not isinstance(text, str) or not text.strip():
        raise BodyOpponentError(f"{label} requires a full body, not a title-only row")
    return text


def _scope(row: dict[str, Any], *, label: str) -> dict[str, str]:
    scope: dict[str, str] = {}
    for field in SCOPE_FIELDS:
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BodyOpponentError(f"{label} requires non-empty {field}")
        scope[field] = value.strip()
    return scope


def _project_article(row: dict[str, Any]) -> dict[str, Any]:
    text = row["text"]
    return {
        "artifact_id": row["artifact_id"],
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def build_body_comparison(
    *,
    self_article: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Choose the best scorable winner inside the self article's exact scope.

    Cross-scope fallback is deliberately forbidden. If the exact reference
    class is empty, the honest result is ``unknown`` and the learner changes
    nothing.
    """

    if self_article.get("role") != "self":
        raise BodyOpponentError("self article role must be self")
    if not isinstance(self_article.get("artifact_id"), str):
        raise BodyOpponentError("self article requires artifact_id")
    _full_body(self_article, label="self article")
    scope = _scope(self_article, label="self article")

    eligible: list[dict[str, Any]] = []
    for row in candidates:
        if not isinstance(row, dict) or row.get("role") != "winner":
            continue
        if row.get("artifact_id") == self_article["artifact_id"]:
            continue
        try:
            text = _full_body(row, label="opponent")
            candidate_scope = _scope(row, label="opponent")
        except BodyOpponentError:
            continue
        reward = row.get("reward")
        if (
            candidate_scope != scope
            or not isinstance(reward, dict)
            or reward.get("status") != "scorable"
            or not isinstance(reward.get("value"), (int, float))
        ):
            continue
        projected = dict(row)
        projected["text"] = text
        eligible.append(projected)

    base = {"scope": scope}
    if not eligible:
        return {
            **base,
            "status": "unknown",
            "reason": "no_same_scope_full_body_winner",
        }

    eligible.sort(
        key=lambda row: (
            -float(row["reward"]["value"]),
            str(row["artifact_id"]),
        )
    )
    opponent = eligible[0]
    return {
        **base,
        "status": "scorable",
        "reason": "same_scope_full_body_winner",
        "self": _project_article(self_article),
        "opponent": _project_article(opponent),
        "opponent_reward": dict(opponent["reward"]),
    }


def validate_body_comparison(receipt: dict[str, Any] | None) -> None:
    """Reject title-only, cross-scope, or otherwise incomplete receipts."""

    if not isinstance(receipt, dict) or receipt.get("status") != "scorable":
        raise ValueError("article-body change requires a scorable comparison receipt")
    scope = receipt.get("scope")
    if (
        not isinstance(scope, dict)
        or set(scope) != set(SCOPE_FIELDS)
        or any(not isinstance(scope.get(field), str) or not scope[field] for field in SCOPE_FIELDS)
    ):
        raise ValueError("article-body comparison receipt has incomplete scope")
    for role in ("self", "opponent"):
        row = receipt.get(role)
        if not isinstance(row, dict):
            raise ValueError(f"article-body comparison receipt lacks {role} full body")
        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"article-body comparison requires {role} full body")
        expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if row.get("text_sha256") != expected_hash:
            raise ValueError(f"article-body comparison {role} body hash mismatch")
