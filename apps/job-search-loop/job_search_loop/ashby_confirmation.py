from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


SUBMIT_MUTATIONS = frozenset(
    {"submitApplicationFormAction", "submitMultipleFormsAction"}
)


def is_submit_mutation(operation_name: Any) -> bool:
    return isinstance(operation_name, str) and operation_name in SUBMIT_MUTATIONS


def _typename(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    typename = value.get("__typename")
    return typename if isinstance(typename, str) and typename else None


def _sha256(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def classify_confirmation(
    payload: Any,
    *,
    expected_success_text: str,
    status_text: str | None,
    alert_text: str | None,
) -> dict[str, Any]:
    if not isinstance(expected_success_text, str) or not expected_success_text.strip():
        raise ValueError("expected_success_text is required")
    data = payload.get("data") if isinstance(payload, Mapping) else None
    data = data if isinstance(data, Mapping) else {}
    operation = "none"
    action: Mapping[str, Any] = {}
    if isinstance(data.get("submitApplicationFormAction"), Mapping):
        operation = "single"
        action = data["submitApplicationFormAction"]
    elif isinstance(data.get("submitMultipleFormsAction"), Mapping):
        operation = "multiple"
        action = data["submitMultipleFormsAction"]

    application_result = _typename(action.get("applicationFormResult"))
    survey_values = action.get("surveyFormResults")
    survey_results = (
        [_typename(value) for value in survey_values]
        if isinstance(survey_values, list)
        else []
    )
    graphql_success = application_result == "FormSubmitSuccess" and all(
        value == "FormSubmitSuccess" for value in survey_results
    )
    expected = _normalized(expected_success_text)
    status = _normalized(status_text)
    status_matches = bool(
        status
        and (
            status == expected
            or status == f"Success {expected}"
        )
    )
    alert_present = bool(_normalized(alert_text))
    return {
        "version": 1,
        "operation": operation,
        "application_result": application_result,
        "survey_results": survey_results,
        "graphql_success": graphql_success,
        "status_matches": status_matches,
        "alert_present": alert_present,
        "expected_success_sha256": _sha256(expected_success_text),
        "status_text_sha256": _sha256(status_text),
        "alert_text_sha256": _sha256(alert_text),
        "authoritative_success": bool(
            graphql_success and status_matches and not alert_present
        ),
    }
