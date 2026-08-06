from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


SUBMIT_OPERATIONS = frozenset(
    {"ApiSubmitSingleApplicationFormAction", "ApiSubmitMultipleFormsAction"}
)
RECAPTCHA_REJECTION = (
    "There was an error verifying that you are not a robot. Please try again."
)


def is_submit_mutation(operation_name: Any) -> bool:
    return isinstance(operation_name, str) and operation_name in SUBMIT_OPERATIONS


def submit_operation_from_payload(payload: Any) -> str | None:
    candidates = payload if isinstance(payload, list) else [payload]
    operations = [
        candidate.get("operationName")
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and is_submit_mutation(candidate.get("operationName"))
    ]
    return operations[0] if len(operations) == 1 else None


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


def classify_post_click_observation(
    *,
    submit_operation: str | None,
    recaptcha_started: bool,
    visible_error_texts: list[str],
    unselected_required_answers: list[str],
    timed_out: bool,
) -> dict[str, Any]:
    if submit_operation is not None and not is_submit_mutation(submit_operation):
        raise ValueError("submit_operation is not an official Ashby submit operation")
    if not isinstance(recaptcha_started, bool) or not isinstance(timed_out, bool):
        raise ValueError("observation flags must be booleans")
    if any(not isinstance(value, str) or not value.strip() for value in visible_error_texts):
        raise ValueError("visible errors must be non-empty strings")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in unselected_required_answers
    ):
        raise ValueError("required answer identifiers must be non-empty strings")

    exact_recaptcha_rejection = RECAPTCHA_REJECTION in visible_error_texts
    if submit_operation is not None:
        classification = "request_started"
    elif exact_recaptcha_rejection:
        classification = "recaptcha_rejected"
    elif visible_error_texts or unselected_required_answers:
        classification = "validation_rejected"
    elif recaptcha_started and timed_out:
        classification = "recaptcha_pending"
    elif timed_out:
        classification = "silent_timeout"
    else:
        classification = "no_terminal_signal"

    return {
        "version": 1,
        "classification": classification,
        "submit_operation": submit_operation,
        "recaptcha_started": recaptcha_started,
        "timed_out": timed_out,
        "visible_error_sha256": sorted(_sha256(value) for value in visible_error_texts),
        "unselected_required_answer_sha256": sorted(
            _sha256(value) for value in unselected_required_answers
        ),
        "retryable": classification == "recaptcha_rejected",
    }


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
    status_casefold = status.casefold()
    semantic_success_status = (
        status_casefold.startswith("success ")
        and "your application" in status_casefold
        and "successfully submitted" in status_casefold
    )
    status_matches = bool(
        status
        and (
            status == expected
            or status == f"Success {expected}"
            or semantic_success_status
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
