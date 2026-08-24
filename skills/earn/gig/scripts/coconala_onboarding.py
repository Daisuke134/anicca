#!/usr/bin/env python3
"""Create and read the secret-free resumable Coconala onboarding receipt."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from money_loop_onboarding import _write_private


STATES = (
    "preflight", "authenticated", "email_verified", "sms_verified",
    "seller_information", "identity_approved", "bank_registered",
    "launchd_readback", "storefront_listing_readback",
)
ACCOUNT_GATES = STATES[:7]


def _validate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 2 or value.get("platform") != "coconala":
        raise ValueError("invalid_coconala_onboarding_receipt")
    states = value.get("states")
    if not isinstance(states, dict) or set(states) != set(STATES):
        raise ValueError("invalid_coconala_onboarding_states")
    for state in states.values():
        if not isinstance(state, dict) or set(state) != {"status", "evidence_sha256"}:
            raise ValueError("invalid_coconala_onboarding_state")
        if state["status"] == "pending" and state["evidence_sha256"] is not None:
            raise ValueError("invalid_coconala_onboarding_pending_evidence")
        if state["status"] == "complete" and re.fullmatch(r"[0-9a-f]{64}", str(state["evidence_sha256"] or "")) is None:
            raise ValueError("invalid_coconala_onboarding_complete_evidence")
        if state["status"] not in {"pending", "complete"}:
            raise ValueError("invalid_coconala_onboarding_state")
    return value


def receipt(home: Path) -> dict[str, Any]:
    path = home / ".config" / "anicca" / "gig" / "coconala-onboarding.json"
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(current, dict) and current.get("version") == 1 and isinstance(current.get("states"), dict):
            current = {
                "version": 2, "platform": "coconala",
                "states": {state: {"status": "pending", "evidence_sha256": None} for state in STATES},
            }
            _write_private(path, current)
        return _validate(current)
    value = {
        "version": 2,
        "platform": "coconala",
        "states": {state: {"status": "pending", "evidence_sha256": None} for state in STATES},
    }
    _write_private(path, value)
    return value


def record(home: Path, state: str, evidence_sha256: str) -> dict[str, Any]:
    if state not in STATES or re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None:
        raise ValueError("invalid_coconala_onboarding_evidence")
    value = receipt(home)
    value["states"][state] = {"status": "complete", "evidence_sha256": evidence_sha256}
    _write_private(home / ".config" / "anicca" / "gig" / "coconala-onboarding.json", value)
    return _validate(value)


def ready(home: Path) -> tuple[dict[str, Any], int]:
    value = receipt(home)
    missing = [state for state in ACCOUNT_GATES if value["states"][state]["status"] != "complete"]
    return {"status": "ready" if not missing else "blocked", "missing": missing}, 0 if not missing else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "status", "record", "ready"))
    parser.add_argument("--state", choices=STATES)
    parser.add_argument("--evidence-sha256")
    args = parser.parse_args()
    exit_code = 0
    if args.command == "record":
        if not args.state or not args.evidence_sha256:
            parser.error("record requires --state and --evidence-sha256")
        value = record(Path.home(), args.state, args.evidence_sha256)
    elif args.command == "ready":
        value, exit_code = ready(Path.home())
    else:
        value = receipt(Path.home())
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
