#!/usr/bin/env bash
# predict.sh — open a MiroFish-style outcome wager (spec 18 §3 PREDICTION; P14 #337 Wave 1).
#
#   predict.sh <claim_text> <stake_usdc_str>
#
# Validates the claim is TESTABLE (explicit metric + deadline), computes a deadline, and records
# an `open` row in ~/.hermes/state/predictions.jsonl. Wave 1: stake is RECORDED only — NO on-chain
# transfer (gated on #324-wave2 + wallet ≥$5).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/_lib.sh"

usage() { echo "usage: predict.sh <claim_text> <stake_usdc_str>" >&2; exit 64; }
[ "$#" -eq 2 ] || usage
CLAIM="$1"; STAKE="$2"

if ! pr_testable "$CLAIM"; then
  echo "predict: claim is not testable (needs an explicit metric AND a deadline): $CLAIM" >&2
  exit 64
fi

NOW="$(pr_now)"
TS="$(date -u -r "$NOW" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
HORIZON="$(pr_horizon_secs "$CLAIM")"
DEADLINE=$(( NOW + HORIZON ))
PID="$(pr_id "$CLAIM$TS")"

"$JQ" -nc \
  --arg id "$PID" --arg ts "$TS" --arg claim "$CLAIM" --arg stake "$STAKE" \
  --argjson deadline "$DEADLINE" \
  '{prediction_id:$id, ts:$ts, claim:$claim, stake_usdc:$stake, deadline_ts:$deadline, status:"open"}' \
  >> "$PREDICTIONS"

echo "predict: opened $PID — \"$CLAIM\" stake=$STAKE deadline_ts=$DEADLINE (Wave 1 dry-run, no chain)"
