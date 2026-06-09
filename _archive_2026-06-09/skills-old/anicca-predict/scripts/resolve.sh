#!/usr/bin/env bash
# resolve.sh — resolve all expired open predictions (spec 18 §3 PREDICTION; P14 #337 Wave 1).
#
# For each open row whose deadline has passed: run a claim-specific evidence script
# (~/.hermes/state/predict-evidence/<prediction_id>.sh, stdout must be exactly "won"/"lost") if
# present, else mark "unresolved". Append a MOCK pot row (Wave 1: NO real transfer). Rewrites
# predictions.jsonl atomically with the updated rows.
#
# Cron entry point (every 6h). Wave 2 replaces the mock pot with wallet_lib.send_usdc().
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/_lib.sh"

NOW="$(pr_now)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ -s "$PREDICTIONS" ] || { printf '%s\n' "$("$JQ" -nc --arg ts "$TS" '{ts:$ts, resolved:0, note:"no predictions"}')" >> "$TRACE"; echo "resolve: no predictions"; exit 0; }

TMP="$(pr_mktemp resolve)"
n_resolved=0

while IFS= read -r row; do
  [ -z "$row" ] && continue
  status="$(printf '%s' "$row" | "$JQ" -r '.status')"
  deadline="$(printf '%s' "$row" | "$JQ" -r '.deadline_ts')"
  pid="$(printf '%s' "$row" | "$JQ" -r '.prediction_id')"
  stake="$(printf '%s' "$row" | "$JQ" -r '.stake_usdc')"

  # Only act on still-open rows whose deadline has passed.
  if [ "$status" != "open" ] || [ "$deadline" -gt "$NOW" ] 2>/dev/null; then
    printf '%s\n' "$row" >> "$TMP"
    continue
  fi

  new_status="unresolved"
  evid="$EVIDENCE_DIR/$pid.sh"
  if [ -x "$evid" ]; then
    out="$(timeout 60 "$evid" 2>/dev/null | tr -d '[:space:]' || true)"
    case "$out" in
      won)  new_status="won" ;;
      lost) new_status="lost" ;;
      *)    new_status="unresolved" ;;
    esac
  fi

  # MOCK pot distribution (Wave 1 — NO transfer). Wave 2 → wallet_lib.send_usdc().
  "$JQ" -nc --arg ts "$TS" --arg p "$pid" --arg s "$new_status" --arg stake "$stake" \
    '{ts:$ts, prediction_id:$p, status:$s, stake_usdc:$stake, payout:"mock", note:"wave1-no-transfer"}' \
    >> "$POT"

  printf '%s\n' "$row" | "$JQ" -c --arg s "$new_status" --argjson rt "$NOW" \
    '.status=$s | .resolved_ts=$rt' >> "$TMP"
  n_resolved=$((n_resolved+1))
done < "$PREDICTIONS"

mv "$TMP" "$PREDICTIONS"

printf '%s\n' "$("$JQ" -nc --arg ts "$TS" --argjson resolved "$n_resolved" '{ts:$ts, resolved:$resolved}')" >> "$TRACE"
echo "resolve: $n_resolved expired prediction(s) resolved (Wave 1 mock pot)"
