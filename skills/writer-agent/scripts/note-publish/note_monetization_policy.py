#!/usr/bin/env python3
"""Return the fixed desired monetization state for a new note article."""

from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("desired-state",))
    parser.add_argument("--free", action="store_true")
    args = parser.parse_args()
    if args.free:
        parser.error("free publication is outside the Writer money contract")
    print(
        json.dumps(
            {
                "access_model": "one_time_purchase",
                "currency": "JPY",
                "paywall_required": True,
                "price_minor": 500,
                "publisher_args": ["--price", "500"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
