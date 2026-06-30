#!/usr/bin/env python3
"""cross-learn-share-dispatch.py — Python side of cross-learn-share.sh."""
import json
import os
import sys
import time
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib._common import append_jsonl  # noqa: E402


def main() -> int:
    slot = os.environ.get("ANICCA_SLOT", "")
    req_id = os.environ.get("ANICCA_REQ_ID", "")
    outcome = os.environ.get("ANICCA_OUTCOME", "")
    shared_file = Path.home() / "loops" / slot / "shared-lessons.jsonl"

    # Dedup check (REQ-D2 claim-check)
    if shared_file.exists():
        for line in shared_file.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("requestId") == req_id and row.get("outcome") == outcome:
                    print("cross-learn-share: dedup hit, skip")
                    return 0

    # Tentative row BEFORE gh (claim-check pattern)
    append_jsonl(shared_file, {
        "ts": int(time.time()),
        "requestId": req_id, "outcome": outcome,
        "issue_url": None, "status": "pending",
    })
    print(f"cross-learn-share: tentative row written for {req_id}/{outcome}")
    # TODO sprint-2: subprocess gh issue create + atomic-rewrite to status:shared.
    return 0


if __name__ == "__main__":
    sys.exit(main())
