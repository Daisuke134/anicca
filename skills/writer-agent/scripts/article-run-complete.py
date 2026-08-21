#!/usr/bin/env python3
"""Validate completion evidence for one immutable article run."""

import argparse
import json
import sys
from pathlib import Path

from article_completion import (
    ACTIVE_REQUIRED_LIVE,
    LEGACY_REQUIRED_LIVE,
    validate_live_set,
)
from publication_contract_resolver import (
    PublicationContractError,
    resolve_publication_contract,
)


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
    parser.add_argument("--publication-state", required=True)
    args = parser.parse_args()

    rows = [row for row in load_rows(Path(args.ledger)) if row.get("run_id") == args.run_id]
    if args.armed == "0":
        return 0 if rows else 1

    try:
        contract = resolve_publication_contract(
            Path(args.publication_state), Path(args.ledger), args.run_id
        )
    except PublicationContractError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    required = LEGACY_REQUIRED_LIVE if contract == "legacy-exact8" else ACTIVE_REQUIRED_LIVE
    valid, _, _ = validate_live_set(rows, args.run_id, required)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
