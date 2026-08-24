#!/usr/bin/env python3
"""Create and read the secret-free resumable Coconala onboarding receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from money_loop_onboarding import _write_private


STATES = (
    "preflight", "authenticated", "email_verified", "sms_verified",
    "seller_information", "identity_approved", "bank_registered",
    "launchd_readback", "storefront_listing_readback",
)


def _validate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1 or value.get("platform") != "coconala":
        raise ValueError("invalid_coconala_onboarding_receipt")
    states = value.get("states")
    if not isinstance(states, dict) or set(states) != set(STATES):
        raise ValueError("invalid_coconala_onboarding_states")
    if any(state not in {"pending", "complete"} for state in states.values()):
        raise ValueError("invalid_coconala_onboarding_state")
    return value


def receipt(home: Path) -> dict[str, Any]:
    path = home / ".config" / "anicca" / "gig" / "coconala-onboarding.json"
    if path.exists():
        return _validate(json.loads(path.read_text(encoding="utf-8")))
    value = {
        "version": 1,
        "platform": "coconala",
        "states": {state: "pending" for state in STATES},
    }
    _write_private(path, value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "status"))
    args = parser.parse_args()
    value = receipt(Path.home())
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
