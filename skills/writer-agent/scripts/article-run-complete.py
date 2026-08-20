#!/usr/bin/env python3
"""Validate completion evidence for one immutable article run."""

import argparse
import json
from pathlib import Path

from article_completion import REQUIRED_LIVE, validate_live_set


def load_rows(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--armed", required=True, choices=("0", "1"))
    args = parser.parse_args()

    rows = [row for row in load_rows(Path(args.ledger)) if row.get("run_id") == args.run_id]
    if args.armed == "0":
        return 0 if rows else 1

    valid, _, _ = validate_live_set(rows, args.run_id, REQUIRED_LIVE)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
