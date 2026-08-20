#!/usr/bin/env python3
"""Validate a flexible topic route without coupling source to writing form."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TOPIC_SOURCES = {
    "customer-pain",
    "search-demand",
    "product-proof",
    "measured-failure",
    "market-winner",
    "experiment",
    "build-log",
    "timely-event",
    "explicit-queue",
}
EVIDENCE_METHODS = {
    "browse",
    "interview-data",
    "run-tool",
    "existing-proof",
}
EDITORIAL_FORMS = {
    "explainer",
    "how-to",
    "case-study",
    "comparison",
    "field-note",
    "opinion",
    "report",
}
PRODUCT_LINKS = {"audience", "pain", "proof", "offer"}


class TopicRouteError(ValueError):
    """A topic cannot be routed without reader value and evidence."""


def load_recent_editorial_forms(
    runs_root: Path,
    current_run_id: str,
    limit: int = 2,
) -> tuple[str, ...]:
    """Read recent immutable route receipts, excluding the current run."""

    if limit < 1:
        return ()
    if not runs_root.exists():
        return ()

    receipts: list[tuple[int, str, str]] = []
    for route_file in runs_root.glob("*/gates/topic-route.json"):
        if route_file.parent.parent.name == current_run_id:
            continue
        try:
            route = json.loads(route_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TopicRouteError(
                f"invalid prior topic route receipt: {route_file}"
            ) from exc
        editorial_form = (
            route.get("editorial_form") if isinstance(route, dict) else None
        )
        if editorial_form not in EDITORIAL_FORMS:
            raise TopicRouteError(
                f"invalid editorial_form in prior route receipt: {route_file}"
            )
        receipts.append(
            (route_file.stat().st_mtime_ns, str(route_file), editorial_form)
        )

    receipts.sort()
    return tuple(row[2] for row in receipts[-limit:])


def _required_text(container: dict[str, Any], field: str, label: str) -> str:
    value = container.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TopicRouteError(f"{label}.{field} must be non-empty")
    return value.strip()


def route_topic(
    topic: dict[str, Any],
    recent_forms: tuple[str, ...] = (),
    forbidden_topic_id: str | None = None,
    forbidden_editorial_form: str | None = None,
    required_feedback_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a validated route; never infer form from source or evidence.

    The card explicitly declares all three axes. That permits the same source
    to produce different editorial forms and the same form to consume
    different source types without a hidden ``queue -> run-tool -> report``
    fallback.
    """

    if not isinstance(topic, dict):
        raise TopicRouteError("topic must be an object")
    topic_id = _required_text(topic, "topic_id", "topic")
    if forbidden_topic_id and topic_id == forbidden_topic_id:
        raise TopicRouteError(f"blocked topic_id cannot be reused: {topic_id}")
    topic_source = _required_text(topic, "topic_source", "topic")
    if topic_source not in TOPIC_SOURCES:
        raise TopicRouteError(f"unsupported topic_source: {topic_source}")

    reader = topic.get("reader")
    if not isinstance(reader, dict):
        raise TopicRouteError("reader must be an object")
    reader_out = {
        field: _required_text(reader, field, "reader")
        for field in ("audience", "job", "outcome")
    }

    evidence_plan = topic.get("evidence_plan")
    if not isinstance(evidence_plan, list) or not evidence_plan:
        raise TopicRouteError("evidence_plan must contain at least one item")
    evidence_methods: list[str] = []
    evidence_refs: list[str] = []
    addressed_feedback: set[str] = set()
    required_feedback = set(required_feedback_ids)
    for index, row in enumerate(evidence_plan):
        if not isinstance(row, dict):
            raise TopicRouteError(f"evidence_plan[{index}] must be an object")
        method = _required_text(row, "method", f"evidence_plan[{index}]")
        if method not in EVIDENCE_METHODS:
            raise TopicRouteError(f"unsupported evidence method: {method}")
        evidence_methods.append(method)
        evidence_refs.append(_required_text(row, "ref", f"evidence_plan[{index}]"))
        addresses = row.get("addresses_feedback", [])
        if not isinstance(addresses, list) or any(
            not isinstance(value, str) or not value.strip()
            for value in addresses
        ):
            raise TopicRouteError(
                f"evidence_plan[{index}].addresses_feedback must be a string list"
            )
        normalized = {value.strip() for value in addresses}
        unknown = normalized - required_feedback
        if unknown:
            raise TopicRouteError(
                "evidence_plan addresses unknown quality feedback: "
                + ",".join(sorted(unknown))
            )
        addressed_feedback.update(normalized)
    missing_feedback = required_feedback - addressed_feedback
    if missing_feedback:
        raise TopicRouteError(
            "quality feedback not covered by evidence_plan: "
            + ",".join(sorted(missing_feedback))
        )

    editorial_form = _required_text(topic, "editorial_form", "topic")
    if editorial_form not in EDITORIAL_FORMS:
        raise TopicRouteError(f"unsupported editorial_form: {editorial_form}")
    if forbidden_editorial_form and editorial_form == forbidden_editorial_form:
        raise TopicRouteError(
            f"blocked editorial_form cannot be reused: {editorial_form}"
        )
    if (
        len(recent_forms) >= 2
        and recent_forms[-2] == editorial_form
        and recent_forms[-1] == editorial_form
    ):
        raise TopicRouteError(
            f"third consecutive editorial_form is not allowed: {editorial_form}"
        )

    product_link = topic.get("product_link")
    if not isinstance(product_link, dict):
        raise TopicRouteError("product_link must be an object")
    product_link_out = {
        key: value.strip()
        for key, value in product_link.items()
        if key in PRODUCT_LINKS and isinstance(value, str) and value.strip()
    }
    if not product_link_out:
        raise TopicRouteError(
            "product_link requires at least one of audience, pain, proof, offer"
        )

    routed = {
        "topic_id": topic_id,
        "topic_source": topic_source,
        "reader": reader_out,
        "evidence_methods": evidence_methods,
        "evidence_refs": evidence_refs,
        "editorial_form": editorial_form,
        "product_link": product_link_out,
    }
    if required_feedback_ids:
        routed["quality_feedback_ids"] = list(required_feedback_ids)
    return routed


def _replacement_feedback_ids(replacement: dict[str, Any]) -> tuple[str, ...]:
    feedback = replacement.get("quality_failure_feedback")
    if not isinstance(feedback, dict) or feedback.get("version") != 1:
        raise TopicRouteError("quality replacement feedback is missing or invalid")
    expected_hash = feedback.get("feedback_sha256")
    unsigned = dict(feedback)
    unsigned.pop("feedback_sha256", None)
    actual_hash = hashlib.sha256(
        json.dumps(
            unsigned,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if expected_hash != actual_hash:
        raise TopicRouteError("quality replacement feedback hash mismatch")
    items = feedback.get("items")
    if not isinstance(items, list) or not items:
        raise TopicRouteError("quality replacement feedback items are missing")
    ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TopicRouteError(f"quality feedback item {index} is invalid")
        feedback_id = _required_text(item, "id", f"quality_feedback[{index}]")
        if feedback_id in ids:
            raise TopicRouteError(f"duplicate quality feedback id: {feedback_id}")
        ids.append(feedback_id)
    return tuple(ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--input", required=True, type=Path)
    validate.add_argument("--out", required=True, type=Path)
    validate.add_argument("--runs-root", required=True, type=Path)
    validate.add_argument("--current-run-id", required=True)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    replacement_path = (
        args.runs_root
        / args.current_run_id
        / "gates"
        / "quality-replacement.json"
    )
    forbidden_topic_id = None
    forbidden_editorial_form = None
    required_feedback_ids: tuple[str, ...] = ()
    if replacement_path.exists():
        if replacement_path.is_symlink() or not replacement_path.is_file():
            raise TopicRouteError("quality replacement receipt is not a regular file")
        replacement = json.loads(replacement_path.read_text(encoding="utf-8"))
        if (
            not isinstance(replacement, dict)
            or replacement.get("replacement_run_id") != args.current_run_id
        ):
            raise TopicRouteError("quality replacement receipt identity mismatch")
        forbidden_topic_id = _required_text(
            replacement,
            "forbidden_topic_id",
            "quality_replacement",
        )
        forbidden_editorial_form = _required_text(
            replacement,
            "forbidden_editorial_form",
            "quality_replacement",
        )
        required_feedback_ids = _replacement_feedback_ids(replacement)
    recent_forms = load_recent_editorial_forms(
        args.runs_root,
        current_run_id=args.current_run_id,
    )
    routed = route_topic(
        source,
        recent_forms=recent_forms,
        forbidden_topic_id=forbidden_topic_id,
        forbidden_editorial_form=forbidden_editorial_form,
        required_feedback_ids=required_feedback_ids,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(routed, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
