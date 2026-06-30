#!/usr/bin/env python3
"""self-recover-dispatch.py — Python side of self-recover.sh.

SECURITY: reads inputs from os.environ, never from string interpolation.
"""
import os
import sys
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib.group_j import dispatch_self_recover  # noqa: E402


def main() -> int:
    result = dispatch_self_recover(
        slot=os.environ.get("ANICCA_SLOT", ""),
        reason=os.environ.get("ANICCA_REASON", "unknown"),
        evidence=os.environ.get("ANICCA_EVIDENCE", ""),
        mother_queue_path=Path.home() / "anicca" / "state" / "mother-recovery-queue.jsonl",
        log_path=Path.home() / "loops" / "self-recover-log.jsonl",
    )
    print(f"self-recover: handler={result.handler or '-'} status={result.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
