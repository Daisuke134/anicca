#!/bin/bash
# anicca-payout-wallet entrypoint — send USDC to the user's wallet on Base.
# Usage:
#   bash run.sh                       # 10% of wallet to broker.payout_destination
#   bash run.sh --amount 5.00         # send $5.00 USDC
#   bash run.sh --to 0xABC... --amount 5
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-payout-wallet"
LOG="$SKILL/state/run.log"
mkdir -p "$SKILL/state"
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
echo "=== payout-wallet run $(date '+%Y-%m-%d %H:%M:%S %Z') $*" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 60 /opt/homebrew/bin/python3 \
  "$SKILL/scripts/payout.py" "$@" >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
