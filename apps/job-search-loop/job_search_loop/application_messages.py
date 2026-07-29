from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_TEMPLATE_PATH = (
    Path(__file__).parents[1] / "templates" / "application-messages.v1.json"
)
REQUIRED_FIELDS = {
    "version",
    "role_family",
    "company",
    "role",
    "body",
    "fact_ids",
    "job_source_span",
}
PROHIBITED_OWNERSHIP = (
    "led the entire",
    "single-handed",
    "sales quota",
    "people management",
    "revenue owner",
)


class MessageError(ValueError):
    pass


def _clean(value: str, *, name: str, maximum: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    if not cleaned:
        raise MessageError(f"{name} is required")
    if len(cleaned) > maximum:
        raise MessageError(f"{name} exceeds {maximum} characters")
    return cleaned


def _templates(path: Path = DEFAULT_TEMPLATE_PATH) -> dict[str, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1 or not isinstance(value.get("templates"), dict):
        raise MessageError("application message template version is invalid")
    return value["templates"]


def build_application_message(
    profile: dict[str, Any],
    *,
    role_family: str,
    company: str,
    role: str,
    grounded_role_reason: str,
    job_source_span: str,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
) -> dict[str, Any]:
    templates = _templates(template_path)
    if role_family not in templates:
        raise MessageError(f"unsupported role family: {role_family}")
    company = _clean(company, name="company", maximum=160)
    role = _clean(role, name="role", maximum=200)
    reason = _clean(
        grounded_role_reason,
        name="grounded role reason",
        maximum=500,
    )
    source_span = _clean(
        job_source_span,
        name="job source span",
        maximum=1_000,
    )
    facts = {
        str(fact["id"]): str(fact["claim"])
        for fact in profile.get("facts", [])
        if fact.get("id") and fact.get("claim")
    }
    template = templates[role_family]
    fact_ids = [str(value) for value in template["fact_ids"]]
    missing = [fact_id for fact_id in fact_ids if fact_id not in facts]
    if missing:
        raise MessageError(f"missing approved fact IDs: {', '.join(missing)}")
    claims = [facts[fact_id] for fact_id in fact_ids]
    body = "\n\n".join(
        (
            f"Dear {company} Hiring Team,",
            f"I am applying for {role} because {reason}.",
            " ".join(claims[:2]),
            f"{template['bridge']} {' '.join(claims[2:])}",
            str(template["closing"]),
        )
    )
    result = {
        "version": 1,
        "role_family": role_family,
        "company": company,
        "role": role,
        "body": body,
        "fact_ids": fact_ids,
        "job_source_span": source_span,
    }
    validate_application_message(result, profile, template_path=template_path)
    return result


def validate_application_message(
    value: dict[str, Any],
    profile: dict[str, Any],
    *,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
) -> None:
    if set(value) != REQUIRED_FIELDS:
        raise MessageError("message fields do not match the strict contract")
    templates = _templates(template_path)
    role_family = str(value.get("role_family") or "")
    if role_family not in templates:
        raise MessageError(f"unsupported role family: {role_family}")
    if value.get("version") != 1:
        raise MessageError("message version must be 1")
    for field, maximum in (
        ("company", 160),
        ("role", 200),
        ("body", 2_500),
        ("job_source_span", 1_000),
    ):
        _clean(str(value.get(field) or ""), name=field, maximum=maximum)
    expected_fact_ids = [str(row) for row in templates[role_family]["fact_ids"]]
    fact_ids = value.get("fact_ids")
    if not isinstance(fact_ids, list) or fact_ids != expected_fact_ids:
        raise MessageError("fact IDs do not match the role template")
    approved = {
        str(fact["id"]): str(fact["claim"])
        for fact in profile.get("facts", [])
        if fact.get("id") and fact.get("claim")
    }
    if not set(fact_ids) <= set(approved):
        raise MessageError("message references an unapproved fact")
    body = str(value["body"])
    for fact_id in fact_ids:
        if approved[fact_id] not in body:
            raise MessageError(f"approved claim missing from body: {fact_id}")
    lowered = body.casefold()
    if any(phrase in lowered for phrase in PROHIBITED_OWNERSHIP):
        raise MessageError("message contains unsupported ownership language")
