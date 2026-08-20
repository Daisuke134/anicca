#!/usr/bin/env python3
"""Append one structured quality advisory without ever emitting a PASS verdict."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--lang", required=True, choices=("ja", "en"))
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--raw-file", required=True)
    args = parser.parse_args()

    raw = Path(args.raw_file).read_text(encoding="utf-8", errors="replace")
    record = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": "quality_advisory",
        "verdict": "ADVISORY",
        "gate": args.gate,
        "lang": args.lang,
        "attempt": args.attempt,
        "exit_code": args.exit_code,
        "raw_output": raw,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
