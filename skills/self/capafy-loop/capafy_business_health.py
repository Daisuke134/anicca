#!/usr/bin/env python3
"""Evaluate Capafy health from business outcomes, never scheduler presence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


STATE = Path(os.environ.get("CAPAFY_OUTCOME_STATE_DIR", "~/.openclaw/state")).expanduser()
OUTCOME_MAX_HOURS = float(os.environ.get("CAPAFY_BUSINESS_OUTCOME_MAX_HOURS", "30"))
REPAIR_SLA_MINUTES = float(os.environ.get("CAPAFY_REPAIR_SLA_MINUTES", "5"))


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_minutes(value: object) -> float:
    parsed = parse_time(value)
    if parsed is None:
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 60)


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return code


def main() -> int:
    incidents = []
    incident_dir = STATE / "capafy-incidents"
    if incident_dir.exists():
        incidents = [load(path) for path in incident_dir.glob("*.json")]
        incidents = [item for item in incidents if item and item.get("phase") != "verified"]
        incidents.sort(key=lambda item: item.get("updated_at", ""))

    if incidents:
        contained: list[dict] = []
        now = datetime.now(timezone.utc)
        for incident in incidents:
            phase = incident.get("phase")
            age = age_minutes(incident.get("updated_at"))
            base = {
                "incident_id": incident.get("incident_id"),
                "phase": phase,
                "age_minutes": round(age, 2),
            }
            if phase in {"detected", "repair_started", "repaired"}:
                if age > REPAIR_SLA_MINUTES:
                    return emit(
                        {"status": "unhealthy", "reason": "repair_sla_expired", **base}, 1
                    )
                contained.append({"status": "repair_grace", **base})
                continue
            if phase == "unresolved":
                retry_at = parse_time(incident.get("next_retry_at"))
                if retry_at is None:
                    return emit(
                        {"status": "unhealthy", "reason": "unresolved_without_retry", **base},
                        1,
                    )
                if retry_at <= now:
                    return emit({"status": "unhealthy", "reason": "retry_due", **base}, 1)
                contained.append(
                    {"status": "contained", **base, "next_retry_at": incident["next_retry_at"]}
                )
                continue
            return emit({"status": "unhealthy", "reason": "unknown_incident_phase", **base}, 1)
        if contained:
            return emit(contained[-1], 0)

    allowed = {
        "builder_submitted",
        "builder_noop",
        "marketing_published",
        "marketing_dry",
        "account_state",
    }
    terminals = []
    for name in ("capafy-builder-terminal.json", "capafy-marketing-terminal.json"):
        record = load(STATE / name)
        kind = (record.get("outcome") or {}).get("kind")
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
    return emit({"status": "unhealthy", "reason": "no_recent_business_outcome"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
