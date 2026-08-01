#!/usr/bin/env python3
"""Validate and render truthful Capafy outcome envelopes.

This module is deliberately pure: it reads one JSON object, validates or
renders it, and never performs network, Telegram, or runtime-state I/O.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PLACEHOLDER = re.compile(r"\{[^{}]+\}")
MONEY_FIELDS = (
    "gross_usd",
    "pending_usd",
    "realized_usd",
    "mrr_usd",
    "cost_usd",
    "contribution_usd",
)
INCIDENT_PHASES = {
    "detected": {"repair_started", "unresolved"},
    "repair_started": {"repaired", "unresolved"},
    "repaired": {"verified", "unresolved"},
    "unresolved": {"repair_started"},
    "verified": set(),
}


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _is_https_url(value: Any, *, host_suffix: str | None = None) -> bool:
    if not isinstance(value, str) or PLACEHOLDER.search(value):
        return False
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    if host_suffix is None:
        return True
    host = (parsed.hostname or "").lower()
    return host == host_suffix or host.endswith(f".{host_suffix}")


def validate_outcome(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    if any(PLACEHOLDER.search(value) for value in _strings(data)):
        errors.append("literal placeholder tokens are not deliverable")

    kind = data.get("kind")
    if kind in {"builder_submitted", "repair_closure"}:
        if not _is_https_url(data.get("listing_url"), host_suffix="capafy.ai"):
            errors.append("listing_url must be a real https://capafy.ai URL")
        if not data.get("agent_id"):
            errors.append("agent_id is required")
        if data.get("remote_status") not in {1, 4}:
            errors.append("remote_status must be a verified submitted or public state")
        if data.get("skills_confirmed") is not True:
            errors.append("skills_confirmed must be true")
        if data.get("config_confirmed") is not True:
            errors.append("config_confirmed must be true")
        for field in MONEY_FIELDS:
            if field not in data:
                errors.append(f"{field} is required and must remain separate")
            else:
                try:
                    Decimal(str(data[field]))
                except (InvalidOperation, TypeError, ValueError):
                    errors.append(f"{field} must be numeric")
    elif kind == "marketing_published":
        for field in ("reel_url", "listing_url", "campaign_url"):
            if not _is_https_url(data.get(field)):
                errors.append(f"{field} must be a real HTTPS URL")
        if not data.get("caption"):
            errors.append("caption is required")
    elif kind == "account_state":
        if not data.get("handle"):
            errors.append("handle is required")
        public_url = data.get("public_post_url")
        if public_url is not None and not _is_https_url(public_url):
            errors.append("public_post_url must be a real HTTPS URL")
    else:
        errors.append(f"unsupported kind: {kind!r}")
    return errors


def _money(value: Any) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):.2f}"


def _money_lines(data: dict) -> list[str]:
    return [
        f"Lifetime gross: {_money(data['gross_usd'])}",
        f"Pending seller balance: {_money(data['pending_usd'])}",
        f"Realized bank payout: {_money(data['realized_usd'])}",
        f"MRR: {_money(data['mrr_usd'])}",
        f"Model/tool cost: {_money(data['cost_usd'])}",
        f"Contribution after recorded cost: {_money(data['contribution_usd'])}",
    ]


def _verified_state(data: dict) -> str:
    return (
        f"Verified remote state: status {data['remote_status']}; "
        "skill/config confirmed"
    )


def render_outcome(data: dict) -> str:
    errors = validate_outcome(data)
    if errors:
        raise ValueError("; ".join(errors))

    kind = data["kind"]
    if kind == "account_state":
        schedule = (
            "The scheduler is loaded."
            if data.get("scheduler_loaded")
            else "The scheduler is not loaded."
        )
        session = (
            "The posting session is established."
            if data.get("session_established")
            else "The posting session is not established."
        )
        post = (
            f"Verified public post: {data['public_post_url']}"
            if data.get("public_post_url")
            else "No public post is verified."
        )
        return "\n".join(
            [
                f"Capafy Instagram account @{data['handle']}",
                f"Calendar age: day {data.get('calendar_warmup_day', 0)}.",
                schedule,
                session,
                post,
            ]
        )

    if kind == "repair_closure":
        lines = [
            "Capafy incident resolved — no action needed",
            data.get("detected_summary", "A Capafy operation failed."),
            data.get("repair_summary", "The repair owner restored the operation."),
            f"Recovered skill: {data['title']} ({data['agent_id']})",
            _verified_state(data),
            f"Evidence: {data['listing_url']}",
            *_money_lines(data),
            f"Next: {data['next_action']}",
        ]
        return "\n".join(lines)

    if kind == "builder_submitted":
        return "\n".join(
            [
                "Capafy Builder — New skill submitted and verified",
                f"Skill: {data['title']} ({data['agent_id']})",
                _verified_state(data),
                f"Open the real Capafy page: {data['listing_url']}",
                *_money_lines(data),
                f"Next: {data['next_action']}",
            ]
        )

    return "\n".join(
        [
            "Capafy Marketer — Reel published and verified",
            f"Skill: {data['title']}",
            f"Watch the Reel: {data['reel_url']}",
            f"Open the skill: {data['listing_url']}",
            f"Campaign link: {data['campaign_url']}",
            f"Caption: {data['caption']}",
        ]
    )


def delivery_key(data: dict) -> str:
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _state_root() -> Path:
    configured = os.environ.get("CAPAFY_OUTCOME_STATE_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".openclaw/state"


def _incident_dir() -> Path:
    return _state_root() / "capafy-incidents"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _read_incidents() -> list[dict]:
    records = []
    for path in _incident_dir().glob("*.json") if _incident_dir().exists() else []:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def start_incident(
    *, owner: str, summary: str, fingerprint: str, repair_result_path: str | None
) -> dict:
    for record in sorted(
        _read_incidents(), key=lambda item: item.get("detected_at", ""), reverse=True
    ):
        if (
            record.get("owner") == owner
            and record.get("fingerprint") == fingerprint
            and record.get("phase") != "verified"
        ):
            return record

    now = _now()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    incident_id = f"capafy-{owner}-{timestamp}-{secrets.token_hex(4)}"
    record = {
        "schema_version": 1,
        "incident_id": incident_id,
        "owner": owner,
        "phase": "detected",
        "detected_at": now,
        "updated_at": now,
        "summary": summary,
        "fingerprint": fingerprint,
        "repair_result_path": repair_result_path,
        "attempts": 0,
        "next_retry_at": None,
        "terminal_message_key": None,
    }
    _atomic_json_write(_incident_dir() / f"{incident_id}.json", record)
    return record


def transition_incident(update: dict) -> dict:
    incident_id = update.get("incident_id")
    phase = update.get("phase")
    if not isinstance(incident_id, str) or not incident_id:
        raise ValueError("incident_id is required")
    if phase not in INCIDENT_PHASES:
        raise ValueError(f"unsupported incident phase: {phase!r}")
    path = _incident_dir() / f"{incident_id}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"incident not found: {incident_id}") from exc
    current = record.get("phase")
    if phase != current and phase not in INCIDENT_PHASES.get(current, set()):
        raise ValueError(f"incident phase cannot move backwards: {current} -> {phase}")
    if current == "unresolved" and phase == "repair_started":
        record["attempts"] = int(record.get("attempts", 0)) + 1
    for field in (
        "phase",
        "summary",
        "repair_summary",
        "verification",
        "outcome",
        "next_retry_at",
        "terminal_message_key",
        "telegram_message_id",
    ):
        if field in update:
            record[field] = update[field]
    record["updated_at"] = _now()
    _atomic_json_write(path, record)
    return record


def get_active_incident(owner: str) -> dict:
    matches = [
        record
        for record in _read_incidents()
        if record.get("owner") == owner and record.get("phase") != "verified"
    ]
    if not matches:
        raise ValueError(f"no active incident for owner: {owner}")
    return max(matches, key=lambda item: item.get("updated_at", ""))


def load_json_stdin() -> dict:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("outcome must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: capafy_outcome.py <command>", file=sys.stderr)
        return 2
    try:
        command = args[0]
        if command == "start-incident":
            def option(name: str, *, required: bool = True) -> str | None:
                try:
                    return args[args.index(name) + 1]
                except (ValueError, IndexError):
                    if required:
                        raise ValueError(f"{name} is required")
                    return None

            record = start_incident(
                owner=option("--owner") or "",
                summary=option("--summary") or "",
                fingerprint=option("--fingerprint") or "",
                repair_result_path=option("--repair-result-path", required=False),
            )
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
            return 0
        if command == "get-active-incident":
            try:
                owner = args[args.index("--owner") + 1]
            except (ValueError, IndexError) as exc:
                raise ValueError("--owner is required") from exc
            print(json.dumps(get_active_incident(owner), ensure_ascii=False, sort_keys=True))
            return 0
        if command == "transition-incident":
            print(
                json.dumps(
                    transition_incident(load_json_stdin()),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        if len(args) != 1 or command not in {"validate", "render", "delivery-key"}:
            raise ValueError(f"unsupported command: {command}")
        data = load_json_stdin()
        if command == "validate":
            errors = validate_outcome(data)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 2
            print(json.dumps({"valid": True}))
        elif command == "render":
            print(render_outcome(data))
        else:
            errors = validate_outcome(data)
            if errors:
                raise ValueError("; ".join(errors))
            print(delivery_key(data))
    except (json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
