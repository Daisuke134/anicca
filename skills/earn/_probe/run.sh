#!/usr/bin/env bash
# VCSDD integration probe — writes a real earn-ledger line keyed "wake"=WAKE_ID (earn-detect matches l.wake)
# so the loop's classify can read it. Proves a per-method earn/<sub> slot gets EARN_LEDGER + classifies.
set -euo pipefail
LEDGER="${EARN_LEDGER:-${ANICCA_HOME:-$HOME/.anicca}/skills/earn/state/earn-ledger.jsonl}"
mkdir -p "$(dirname "$LEDGER")"
printf '{"wake":"%s","source":"_probe","strategy":"%s","earn_usdc":0.01,"cost_usdc":0}\n' "${WAKE_ID:-noid}" "${EARN_STRATEGY:-_probe}" >> "$LEDGER"
echo "earn/_probe ran: wrote earn-ledger line wake=${WAKE_ID:-noid} earn_usdc=0.01 (EARN_LEDGER=$LEDGER)"
