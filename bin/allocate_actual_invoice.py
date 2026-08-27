#!/usr/bin/env python3
"""Bind an actual invoice to exact provider-reported usage events by tokens."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from invoice_allocator import allocate_invoice, append_invoice_allocations  # noqa: E402


def _strict_jsonl(source: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with source.expanduser().open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"usage_ledger_invalid_json:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"usage_ledger_non_object:{line_number}")
            rows.append(row)
    return rows


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--invoice", required=True, type=Path)
    parser.add_argument(
        "--usage-ledger",
        type=Path,
        default=Path("~/.local/state/anicca/telemetry/agent-usage.jsonl").expanduser(),
    )
    parser.add_argument(
        "--economics-ledger",
        type=Path,
        default=Path("~/.local/state/anicca/telemetry/unit-economics-events.jsonl").expanduser(),
    )
    args = parser.parse_args()
    try:
        invoice = json.loads(args.invoice.expanduser().read_text(encoding="utf-8"))
        usage_rows = _strict_jsonl(args.usage_ledger)
        events = allocate_invoice(usage_rows, invoice)
        outcome = append_invoice_allocations(args.economics_ledger, events)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "rejected", "error": str(error)}, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps({
        "allocated_minor": sum(event["data"]["amount_minor"] for event in events),
        "appended": outcome["appended"],
        "duplicates": outcome["duplicates"],
        "loops": len(events),
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
