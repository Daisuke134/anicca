#!/usr/bin/env python3
"""Validate and idempotently append one standard unit-economics event."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from unit_economics_events import append_event, make_event  # noqa: E402


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("~/.local/state/anicca/telemetry/unit-economics-events.jsonl").expanduser(),
    )
    parser.add_argument("--kind", required=True, choices=("revenue", "cost"))
    parser.add_argument("--loop", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-record-id", required=True)
    parser.add_argument("--occurred-at", required=True)
    parser.add_argument("--amount-minor", required=True, type=int)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--invoice-id")
    parser.add_argument("--allocation-basis")
    args = parser.parse_args()
    try:
        event = make_event(
            kind=args.kind,
            loop=args.loop,
            source=args.source,
            source_record_id=args.source_record_id,
            occurred_at=args.occurred_at,
            amount_minor=args.amount_minor,
            currency=args.currency,
            evidence=args.evidence,
            invoice_id=args.invoice_id,
            allocation_basis=args.allocation_basis,
        )
        appended = append_event(args.ledger, event)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "rejected", "error": str(error)}, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "appended" if appended else "duplicate",
        "id": event["id"],
        "type": event["type"],
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
