#!/usr/bin/env bash
# anicca-wallet/scripts/balance_watch.sh
# Cron entrypoint. Runs balance.sh, appends ONE JSONL line, prints the same line.
# Idempotent per-tick. Must complete in < 10 s.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${STATE_DIR:-/Users/anicca/.hermes/state}"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/wallet-balance.jsonl"

LINE=$("$SKILL_DIR/scripts/balance.sh")
printf '%s\n' "$LINE" >> "$LOG"
printf '%s\n' "$LINE"
