#!/usr/bin/env python3
"""Validate and render truthful Capafy outcome envelopes.

This module is deliberately pure: it reads one JSON object, validates or
renders it, and never performs network, Telegram, or runtime-state I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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


def load_json_stdin() -> dict:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("outcome must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in {"validate", "render", "delivery-key"}:
        print("usage: capafy_outcome.py validate|render|delivery-key", file=sys.stderr)
        return 2
    try:
        data = load_json_stdin()
        if args[0] == "validate":
            errors = validate_outcome(data)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 2
            print(json.dumps({"valid": True}))
        elif args[0] == "render":
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
