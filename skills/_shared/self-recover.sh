#!/usr/bin/env bash
# self-recover.sh — REQ-F1 dispatcher (NO HUMAN, v7)
# Routes (slot, reason, evidence) → Group J handlers in lib/group_j.py.
# NEVER posts to Telegram/Slack/etc. NEVER creates gh issues with escalation labels.
# Exhaustion → MOTHER queue (= another AI instance).
#
# Usage: self-recover.sh <slot> <reason> <evidence>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SLOT="${1:-}"
REASON="${2:-unknown}"
EVIDENCE="${3:-}"
LOG="${HOME}/.openclaw/logs/${SLOT}-self-recover.log"
mkdir -p "$(dirname "$LOG")"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - <<PYEOF 2>&1 | tee -a "$LOG"
import sys
sys.path.insert(0, "${SHARED_DIR}")
from pathlib import Path
from lib.group_j import dispatch_self_recover

result = dispatch_self_recover(
    slot="${SLOT}",
    reason="${REASON}",
    evidence="""${EVIDENCE}""",
    mother_queue_path=Path.home() / "anicca" / "state" / "mother-recovery-queue.jsonl",
    log_path=Path.home() / "loops" / "self-recover-log.jsonl",
)
print(f"self-recover: slot={result.handler or '-'} status={result.status}")
PYEOF
