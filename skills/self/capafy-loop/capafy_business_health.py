#!/usr/bin/env python3
"""Evaluate Capafy health from business outcomes, never scheduler presence."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path


STATE = Path(os.environ.get("CAPAFY_OUTCOME_STATE_DIR", "~/.openclaw/state")).expanduser()


def positive_threshold(name: str, default: str) -> float | None:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value > 0 else None


OUTCOME_MAX_HOURS = positive_threshold("CAPAFY_BUSINESS_OUTCOME_MAX_HOURS", "30")
REPAIR_SLA_MINUTES = positive_threshold("CAPAFY_REPAIR_SLA_MINUTES", "5")
RECONCILIATION_LEDGER = Path(
    os.environ.get("CAPAFY_RECONCILIATION_LEDGER", "~/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl")
).expanduser()
RECONCILIATION_MAX_HOURS = positive_threshold("CAPAFY_RECONCILIATION_MAX_HOURS", "48")
REPORT_DELIVERY_STATE = Path(
    os.environ.get("CAPAFY_REPORT_DELIVERY_STATE", str(STATE / "capafy-goal-monitor-delivery.json"))
).expanduser()
HOURLY_REPORT_MAX_MINUTES = positive_threshold("CAPAFY_HOURLY_REPORT_MAX_MINUTES", "90")
DAILY_CLOSE_MAX_HOURS = positive_threshold("CAPAFY_DAILY_CLOSE_MAX_HOURS", "26")
REPAIRS = {
    "builder": ("builder", "ai.anicca.capafy-loop-daily"),
    "capafy-builder": ("builder", "ai.anicca.capafy-loop-daily"),
    "marketer": ("marketer", "ai.anicca.capafy-ig-marketing-daily"),
    "capafy-marketer": ("marketer", "ai.anicca.capafy-ig-marketing-daily"),
    "company": ("company", "ai.anicca.capafy-goal-monitor"),
    "capafy-company": ("company", "ai.anicca.capafy-goal-monitor"),
    "company-hourly": ("company", "ai.anicca.capafy-goal-monitor-hourly"),
    "company-daily-close": ("company", "ai.anicca.capafy-goal-monitor-daily-close"),
}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
PROJECTION_ID = re.compile(r"sha256:[0-9a-f]{64}")


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def parse_time(value: object, *, rfc3339: bool = False) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    if rfc3339 and not RFC3339.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def observed_time(value: object, *, rfc3339: bool = False) -> datetime | None:
    parsed = parse_time(value, rfc3339=rfc3339)
    if parsed is None or parsed > datetime.now(timezone.utc):
        return None
    return parsed


def age_minutes(value: object) -> float:
    parsed = observed_time(value)
    if parsed is None:
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 60)


def file_age_minutes(path: Path) -> float:
    try:
        if not path.is_file():
            return float("inf")
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except (OSError, OverflowError, ValueError):
        return float("inf")
    if modified > datetime.now(timezone.utc):
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - modified).total_seconds() / 60)


def valid_period(key: str, prefix: str, pattern: str) -> bool:
    period = key.removeprefix(prefix)
    if not re.fullmatch(pattern, period):
        return False
    try:
        datetime.strptime(period, "%Y-%m-%dT%H" if prefix == "hourly:" else "%Y-%m-%d")
    except ValueError:
        return False
    return True


def delivery_age_minutes(prefix: str) -> float:
    state = load(REPORT_DELIVERY_STATE)
    rows = state.get("deliveries")
    required = {"delivery_key", "projection_id", "telegram_message_id", "delivered_at"}
    if state.get("schema_version") != 2 or not isinstance(rows, list):
        return float("inf")
    delivered = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != required or not isinstance(row.get("delivery_key"), str):
            return float("inf")
        if row["delivery_key"].startswith(prefix):
            pattern = r"\d{4}-\d{2}-\d{2}T\d{2}" if prefix == "hourly:" else r"\d{4}-\d{2}-\d{2}"
            timestamp = observed_time(row["delivered_at"], rfc3339=True)
            if (
                not valid_period(row["delivery_key"], prefix, pattern)
                or not isinstance(row["projection_id"], str)
                or not PROJECTION_ID.fullmatch(row["projection_id"])
                or not isinstance(row["telegram_message_id"], str)
                or not re.fullmatch(r"[0-9]+", row["telegram_message_id"])
                or timestamp is None
            ):
                return float("inf")
            delivered.append(timestamp)
    if not delivered:
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - max(delivered)).total_seconds() / 60)


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


def unhealthy(reason: str, owner: str, **payload: object) -> int:
    repair_owner, repair_label = REPAIRS[owner]
    return emit(
        {"status": "unhealthy", "reason": reason, **payload, "repair_owner": repair_owner, "repair_action": "kickstart", "repair_label": repair_label},
        1,
    )


def integrity(reason: str, **payload: object) -> int:
    return emit(
        {"status": "unhealthy", "reason": reason, **payload, "repair_owner": "integrity", "repair_action": "self_fix"},
        1,
    )


def main() -> int:
    if any(value is None for value in (
        OUTCOME_MAX_HOURS,
        REPAIR_SLA_MINUTES,
        RECONCILIATION_MAX_HOURS,
        HOURLY_REPORT_MAX_MINUTES,
        DAILY_CLOSE_MAX_HOURS,
    )):
        return integrity("invalid_health_configuration")
    if file_age_minutes(RECONCILIATION_LEDGER) > RECONCILIATION_MAX_HOURS * 60:
        return unhealthy("stale_reconciliation", "builder")
    if delivery_age_minutes("hourly:") > HOURLY_REPORT_MAX_MINUTES:
        return unhealthy("owner_report_missing", "company-hourly")
    if delivery_age_minutes("daily_close:") > DAILY_CLOSE_MAX_HOURS * 60:
        return unhealthy("owner_report_missing", "company-daily-close")

    marketing_terminal = load(STATE / "capafy-marketing-terminal.json")
    marketing_recorded_at = observed_time(marketing_terminal.get("recorded_at"))
    marketing_outcome = marketing_terminal.get("outcome")
    marketing_kind = marketing_outcome.get("kind") if isinstance(marketing_outcome, dict) else None
    superseding_marketing_outcome = marketing_kind in {
        "account_created",
        "marketing_published",
        "marketing_dry",
    }
    incidents = []
    incident_dir = STATE / "capafy-incidents"
    if incident_dir.exists():
        incidents = [load(path) for path in incident_dir.glob("*.json")]
        incidents = [item for item in incidents if item and item.get("phase") != "verified"]
        if superseding_marketing_outcome and marketing_recorded_at is not None:
            incidents = [
                item
                for item in incidents
                if not (
                    str(item.get("incident_id", "")).startswith("capafy-marketer-")
                    and (incident_time := parse_time(item.get("updated_at"))) is not None
                    and marketing_recorded_at > incident_time
                )
            ]
        incidents.sort(key=lambda item: str(item.get("updated_at", "")))

    if incidents:
        contained: list[dict] = []
        now = datetime.now(timezone.utc)
        for incident in incidents:
            phase = incident.get("phase")
            age = age_minutes(incident.get("updated_at"))
            owner = incident.get("owner")
            base = {
                "incident_id": incident.get("incident_id"),
                "phase": phase,
                "age_minutes": round(age, 2) if math.isfinite(age) else None,
            }
            if not isinstance(owner, str) or owner not in REPAIRS:
                return integrity("unknown_incident_owner", **base)
            if phase in {"detected", "repair_started", "repaired"}:
                if age > REPAIR_SLA_MINUTES:
                    return unhealthy("repair_sla_expired", owner, **base)
                contained.append({"status": "repair_grace", **base})
                continue
            if phase == "unresolved":
                retry_at = parse_time(incident.get("next_retry_at"))
                if retry_at is None:
                    return unhealthy("unresolved_without_retry", owner, **base)
                if retry_at <= now:
                    return unhealthy("retry_due", owner, **base)
                contained.append(
                    {"status": "contained", **base, "next_retry_at": incident["next_retry_at"]}
                )
                continue
            return unhealthy("unknown_incident_phase", owner, **base)
        if contained:
            return emit(contained[-1], 0)

    allowed = {
        "builder_submitted",
        "builder_noop",
        "account_created",
        "marketing_published",
        "marketing_dry",
        "account_state",
    }
    terminals = []
    for name in ("capafy-builder-terminal.json", "capafy-marketing-terminal.json"):
        record = load(STATE / name)
        outcome = record.get("outcome")
        kind = outcome.get("kind") if isinstance(outcome, dict) else None
        age = age_minutes(record.get("recorded_at"))
        if kind in allowed:
            terminals.append((age, kind, name))
    if terminals:
        age, kind, source = min(terminals)
        if age <= OUTCOME_MAX_HOURS * 60:
            return emit(
                {"status": "healthy", "outcome_kind": kind, "source": source, "age_minutes": round(age, 2)},
                0,
            )
    return unhealthy("no_recent_business_outcome", "builder")


if __name__ == "__main__":
    raise SystemExit(main())
