#!/usr/bin/env python3
"""Claim the one permitted Capafy offline skill build for a local calendar day."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path


def claim(path: Path, day: str, execution_id: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        try:
            current = json.load(stream)
        except (json.JSONDecodeError, OSError):
            current = {}
        if current.get("calendar_day") == day:
            return False
        stream.seek(0)
        stream.truncate()
        json.dump({"calendar_day": day, "execution_id": execution_id}, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", choices=["claim"])
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--execution-id", required=True)
    args = parser.parse_args()
    if claim(args.state, args.day, args.execution_id):
        print("BUILD_OFFLINE")
        return 0
    print("ALREADY_CLAIMED")
    return 10


if __name__ == "__main__":
    raise SystemExit(main())
