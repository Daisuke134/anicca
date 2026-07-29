#!/usr/bin/env python3
"""Project evidence-backed Coconala settlements into the shared economics ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "lib"))

from unit_economics_events import append_event, make_event  # noqa: E402


SETTLED = {"SETTLED", "settled", "検収", "検収完了", "支払", "支払完了"}


def _source_record_id(row: dict[str, Any]) -> str:
    bounded = {
        "request_id": row["requestId"],
        "status": row["status"],
        "evidence": row["evidence"],
    }
    return hashlib.sha256(
        json.dumps(bounded, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sync_gig_revenue(earnings_path: str | Path, ledger_path: str | Path) -> dict[str, int]:
    result = {"scanned": 0, "eligible": 0, "appended": 0, "duplicates": 0, "rejected": 0}
    source = Path(earnings_path).expanduser().resolve()
    if not source.exists():
        return result
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            result["scanned"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                result["rejected"] += 1
                continue
            if not isinstance(row, dict):
                result["rejected"] += 1
                continue
            if (
                row.get("status") not in SETTLED
                or not isinstance(row.get("requestId"), str)
                or not row["requestId"].strip()
                or not isinstance(row.get("jpy"), int)
                or isinstance(row.get("jpy"), bool)
                or row["jpy"] <= 0
                or not isinstance(row.get("evidence"), str)
                or not row["evidence"].strip()
                or row.get("ts") is None
            ):
                result["rejected"] += 1
                continue
            result["eligible"] += 1
            try:
                event = make_event(
                    kind="revenue",
                    loop="gig",
                    source="anicca://gig/coconala",
                    source_record_id=_source_record_id(row),
                    occurred_at=row["ts"],
                    amount_minor=row["jpy"],
                    currency="JPY",
                    evidence=row["evidence"],
                )
                if append_event(ledger_path, event):
                    result["appended"] += 1
                else:
                    result["duplicates"] += 1
            except (OSError, ValueError):
                result["rejected"] += 1
    return result


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--earnings", type=Path, default=Path("~/gig/earnings.jsonl").expanduser())
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("~/.local/state/anicca/telemetry/unit-economics-events.jsonl").expanduser(),
    )
    args = parser.parse_args()
    result = sync_gig_revenue(args.earnings, args.ledger)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
