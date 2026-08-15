#!/usr/bin/env python3
"""Build B2 same-pass continuation state from canonical submit proof.

The model result is useful for preserving search progress, but it is not the
authority for whether an application happened.  Only applications independently
verified in the canonical ledger may be carried into another model invocation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def request_id(value: dict[str, Any]) -> str:
    return str(value.get("requestId") or value.get("request_id") or "").strip()


def verified_ids(ledger: Path, pass_id: str) -> set[str]:
    found: set[str] = set()
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return found
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or "action" in row:
            continue
        identity = request_id(row)
        if (
            identity
            and str(row.get("pass_id") or "") == pass_id
            and row.get("status") == "applied"
            and row.get("submit_verified") is True
            and row.get("applied_page_verified") is True
        ):
            found.add(identity)
    return found


def build(summary_path: Path, ledger: Path, pass_id: str) -> dict[str, Any]:
    summary = read_object(summary_path)
    result_path = Path(str(summary["result_path"]))
    result = read_object(result_path)
    proved = verified_ids(ledger, pass_id)
    applications = result.get("applications")
    if not isinstance(applications, list):
        applications = []
    carried = [
        row
        for row in applications
        if isinstance(row, dict) and request_id(row) in proved
    ]
    current_b2 = result.get("current_b2")
    if not isinstance(current_b2, dict):
        current_b2 = {}
    return {
        "applications": carried,
        "current_b2": current_b2,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--runner-summary", type=Path, required=True)
    value.add_argument("--ledger", type=Path, required=True)
    value.add_argument("--pass-id", required=True)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        payload = build(args.runner_summary, args.ledger, args.pass_id)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"b2_continuation_state_invalid:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
