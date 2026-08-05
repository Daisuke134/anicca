from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .ledger import Ledger
from .portfolio import PORTFOLIO_LIMITS
from .summary import write_summary


def record_quota_deficit(
    ledger: Ledger,
    *,
    day: str,
    reason: str,
) -> dict[str, object] | None:
    portfolio_confirmed = ledger.confirmed_daily_portfolio(day)
    confirmed_count = ledger.confirmed_daily_count(day)
    if confirmed_count >= sum(PORTFOLIO_LIMITS.values()):
        return None
    portfolio_deficit = {
        bucket: max(0, limit - portfolio_confirmed[bucket])
        for bucket, limit in PORTFOLIO_LIMITS.items()
    }
    return ledger.record_quota_deficit(
        japan_day=day,
        confirmed_count=confirmed_count,
        portfolio_confirmed=portfolio_confirmed,
        portfolio_deficit=portfolio_deficit,
        reason=reason,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("record",))
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--day", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args(argv)
    ledger = Ledger(parsed.ledger)
    try:
        event = record_quota_deficit(ledger, day=parsed.day, reason=parsed.reason)
    finally:
        ledger.close()
    receipt = event or {"status": "quota_met", "japan_day": parsed.day}
    write_summary(parsed.output, receipt)
    os.chmod(parsed.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
