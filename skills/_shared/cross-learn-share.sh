#!/usr/bin/env bash
# cross-learn-share.sh — REQ-D2 SHARE: publish novel lesson + claim-check dedup.
#
# Usage: cross-learn-share.sh <slot> <requestId> <outcome> <body-file>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SLOT="${1:-}"
REQ_ID="${2:-}"
OUTCOME="${3:-}"
BODY_FILE="${4:-/dev/null}"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - <<PYEOF
import json, sys, time
sys.path.insert(0, "${SHARED_DIR}")
from pathlib import Path
from lib._common import append_jsonl

shared_file = Path.home() / "loops" / "${SLOT}" / "shared-lessons.jsonl"

# Dedup check (REQ-D2 claim-check)
if shared_file.exists():
    for line in shared_file.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("requestId") == "${REQ_ID}" and row.get("outcome") == "${OUTCOME}":
                print("cross-learn-share: dedup hit, skip")
                sys.exit(0)

# Tentative row BEFORE gh (claim-check)
append_jsonl(shared_file, {
    "ts": int(time.time()),
    "requestId": "${REQ_ID}", "outcome": "${OUTCOME}",
    "issue_url": None, "status": "pending",
})
print(f"cross-learn-share: tentative row written for ${REQ_ID}/${OUTCOME}")
PYEOF

# gh issue create. Real impl wires --body-file + retry + update row to status:shared.
# TODO sprint-2: full atomic-rewrite to status:shared on gh success.
