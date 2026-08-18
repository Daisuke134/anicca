"""Runtime validation for the versioned marketplace KPI record contract."""

from __future__ import annotations

import datetime as _datetime
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "kpi-record.schema.json"


class KPIValidationError(ValueError):
    """Stable validation failure without exposing untrusted record contents."""


def _is_rfc3339_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return True
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = _datetime.datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


_FORMAT_CHECKER = FormatChecker()
_FORMAT_CHECKER.checks("date-time")(_is_rfc3339_datetime)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)


def _error_code(error: Any) -> str:
    validator = getattr(error, "validator", None)
    if isinstance(validator, str) and validator:
        return validator
    return "schema"


def _format_path(path: Any) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def _parse_datetime(value: str) -> _datetime.datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = _datetime.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    return parsed


def _validate_window_order(record: Mapping[str, Any]) -> None:
    if record.get("record_kind") != "metric_snapshot":
        return
    window = record.get("window")
    if not isinstance(window, Mapping):
        return
    start = window.get("start")
    end = window.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        return
    if _parse_datetime(start) > _parse_datetime(end):
        raise KPIValidationError("metric_snapshot.window: start_after_end")


def validate_kpi_record(record: Mapping[str, Any]) -> None:
    """Validate one event or metric snapshot, raising a stable ValueError on failure."""
    errors = sorted(
        _validator().iter_errors(record),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        details = "; ".join(
            f"{_format_path(error.path)}:{_error_code(error)}" for error in errors
        )
        raise KPIValidationError(f"invalid_kpi_record:{details}")
    _validate_window_order(record)


__all__ = ["KPIValidationError", "validate_kpi_record"]
