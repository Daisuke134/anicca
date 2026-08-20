#!/usr/bin/env python3
"""Turn rule-conflict scan findings into durable, fail-closed gate tickets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _path_without_line(location: str | None) -> str | None:
    if not location:
        return None
    head, separator, tail = location.rpartition(":")
    return head if separator and tail.isdigit() else location


def _canonical_owner(finding: dict[str, Any]) -> str:
    explicit = finding.get("canonical_owner")
    if isinstance(explicit, str) and explicit:
        return explicit
    candidates = [
        _path_without_line(finding.get("side1")),
        _path_without_line(finding.get("side2")),
    ]
    for candidate in candidates:
        if candidate and candidate.startswith("reference/"):
            return candidate
    return next(candidate for candidate in candidates if candidate)


def _ticket(finding: dict[str, Any]) -> dict[str, Any]:
    severity = (
        "critical" if finding.get("severity") == "critical" else "review"
    )
    stable = {
        "class": finding.get("class"),
        "side1": finding.get("side1"),
        "side2": finding.get("side2"),
        "subject": finding.get("subject"),
    }
    ticket_id = hashlib.sha256(
        json.dumps(stable, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "ticket_id": ticket_id,
        "class": finding.get("class"),
        "severity": severity,
        "canonical_owner": _canonical_owner(finding),
        **{key: value for key, value in stable.items() if key != "class"},
    }


def evaluate_scan(scan_result: dict[str, Any]) -> dict[str, Any]:
    """Build a gate receipt; an unreadable scan blocks both consumers."""

    error = scan_result.get("error")
    if error:
        tickets = [
            {
                "ticket_id": hashlib.sha256(str(error).encode()).hexdigest()[
                    :16
                ],
                "class": "scanner_error",
                "severity": "critical",
                "canonical_owner": "rule_conflicts.py",
                "side1": None,
                "side2": None,
                "subject": str(error),
            }
        ]
    else:
        tickets = [_ticket(row) for row in scan_result.get("findings", [])]

    critical_count = sum(
        ticket["severity"] == "critical" for ticket in tickets
    )
    allowed = critical_count == 0
    return {
        "status": "clear" if allowed else "blocked",
        "sources_scanned": scan_result.get("sources_scanned", []),
        "ticket_count": len(tickets),
        "critical_count": critical_count,
        "generation_allowed": allowed,
        "learning_change_allowed": allowed,
        "tickets": tickets,
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".rule-gate.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scan_result = json.loads(args.scan_json.read_text(encoding="utf-8"))
    gate = evaluate_scan(scan_result)
    _atomic_write(args.out, gate)
    print(json.dumps(gate, ensure_ascii=False))
    return 0 if gate["status"] == "clear" else 2


if __name__ == "__main__":
    raise SystemExit(main())
