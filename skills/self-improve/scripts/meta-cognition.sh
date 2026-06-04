#!/usr/bin/env bash
# meta-cognition: Anicca's self-model probe. Emits ONE JSON object to stdout
# describing the current self-state (finances, activity, health, identity).
# Read-only. Must complete in a few seconds. Idempotent.
set -uo pipefail

STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
CFO_JSON="${CFO_JSON:-/Users/operator/.openclaw/skills/cfo-core/data/anicca-cfo.json}"
JQ=/usr/bin/jq

HEARTBEAT="$STATE_DIR/heartbeat.jsonl"
EVAL_COST="$STATE_DIR/eval-cost.jsonl"
VIOLATIONS="$STATE_DIR/constitution-violations.jsonl"
WALLET="$STATE_DIR/wallet-balance.jsonl"
DAILY="$STATE_DIR/daily-report.jsonl"

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# epoch 24h ago for time-window filters
CUTOFF="$(( $(date -u +%s) - 86400 ))"

# ---- helper: epoch from an ISO8601 Z timestamp (portable on macOS) ----
iso_to_epoch() {
  # strips fractional seconds + trailing Z, parses as UTC
  local t="${1%Z}"; t="${t%%.*}"
  date -u -j -f "%Y-%m-%dT%H:%M:%S" "$t" +%s 2>/dev/null || echo 0
}

# ---- health: heartbeat ok-ratio over last 8 rows + last ts ----
hb_ok_ratio="null"; last_hb_ts=""
if [ -r "$HEARTBEAT" ]; then
  tail8="$(tail -8 "$HEARTBEAT")"
  total="$(printf '%s\n' "$tail8" | grep -c .)"
  if [ "$total" -gt 0 ]; then
    oks="$(printf '%s\n' "$tail8" | "$JQ" -r 'select(.ok==true) | 1' 2>/dev/null | grep -c .)"
    hb_ok_ratio="$(awk "BEGIN{printf \"%.3f\", $oks/$total}")"
    last_hb_ts="$(printf '%s\n' "$tail8" | tail -1 | "$JQ" -r '.ts // empty' 2>/dev/null)"
  fi
fi

# ---- health: eval failures within 24h ----
eval_fail_24h=0
if [ -r "$EVAL_COST" ]; then
  while IFS= read -r row; do
    [ -z "$row" ] && continue
    pass="$(printf '%s' "$row" | "$JQ" -r 'if has("pass") then .pass else "missing" end' 2>/dev/null)"
    [ "$pass" != "false" ] && continue
    rts="$(printf '%s' "$row" | "$JQ" -r '.ts // empty' 2>/dev/null)"
    [ -z "$rts" ] && continue
    [ "$(iso_to_epoch "$rts")" -ge "$CUTOFF" ] && eval_fail_24h=$((eval_fail_24h+1))
  done < "$EVAL_COST"
fi

# ---- health: constitution violations within 24h (decision != OK) ----
violations_24h=0
if [ -r "$VIOLATIONS" ]; then
  while IFS= read -r row; do
    [ -z "$row" ] && continue
    dec="$(printf '%s' "$row" | "$JQ" -r '.decision // empty' 2>/dev/null)"
    [ -z "$dec" ] && continue
    [ "$dec" = "OK" ] && continue
    rts="$(printf '%s' "$row" | "$JQ" -r '.ts // empty' 2>/dev/null)"
    [ -z "$rts" ] && continue
    [ "$(iso_to_epoch "$rts")" -ge "$CUTOFF" ] && violations_24h=$((violations_24h+1))
  done < "$VIOLATIONS"
fi

# ---- activity: cron total + error count ----
cron_total=0; cron_error_count=0
if cron_out="$(openclaw cron list 2>/dev/null)"; then
  # data rows contain a status column; count lines whose status field == error/ok
  cron_total="$(printf '%s\n' "$cron_out" | grep -cE '\b(ok|error)\b')"
  cron_error_count="$(printf '%s\n' "$cron_out" | grep -cE '\berror\b')"
fi

# ---- finances: wallet usdc + delta over last 2 rows ----
wallet_usdc="null"; wallet_delta="null"
if [ -r "$WALLET" ]; then
  wallet_usdc="$(tail -1 "$WALLET" | "$JQ" -r '.usdc // empty' 2>/dev/null)"
  [ -z "$wallet_usdc" ] && wallet_usdc="null"
  prev="$(tail -2 "$WALLET" | head -1 | "$JQ" -r '.usdc // empty' 2>/dev/null)"
  if [ "$wallet_usdc" != "null" ] && [ -n "$prev" ]; then
    wallet_delta="$(awk "BEGIN{printf \"%.6f\", $wallet_usdc - $prev}")"
  fi
fi

# ---- finances: cfo makes/spends/lifeline ----
mrr_usd="null"; makes_usd="null"; spends_usd="null"; lifeline="unknown"
if [ -r "$CFO_JSON" ]; then
  mrr_usd="$("$JQ" -r '.makes.mrr_usd // empty' "$CFO_JSON" 2>/dev/null)"; [ -z "$mrr_usd" ] && mrr_usd="null"
  makes_usd="$("$JQ" -r '.makes.monthly_total_usd // empty' "$CFO_JSON" 2>/dev/null)"; [ -z "$makes_usd" ] && makes_usd="null"
  spends_usd="$("$JQ" -r '(.spends.anicca_runtime_usd // 0)' "$CFO_JSON" 2>/dev/null)"; [ -z "$spends_usd" ] && spends_usd="null"
  ll="$("$JQ" -r '.lifeline.status // .lifeline.tier // empty' "$CFO_JSON" 2>/dev/null)"
  [ -n "$ll" ] && lifeline="$ll"
fi
# derive lifeline if cfo didn't carry one: makes>=spends → THRIVE else HUNGRY
if [ "$lifeline" = "unknown" ] && [ "$makes_usd" != "null" ] && [ "$spends_usd" != "null" ]; then
  if awk "BEGIN{exit !($makes_usd >= $spends_usd)}"; then lifeline="THRIVE"; else lifeline="HUNGRY"; fi
fi

# ---- identity: constitution sha ----
sha=""
if [ -r "$STATE_DIR/constitution.sha" ]; then
  sha="$(tr -d '[:space:]' < "$STATE_DIR/constitution.sha")"
elif [ -r "$HEARTBEAT" ]; then
  sha="$(tail -1 "$HEARTBEAT" | "$JQ" -r '.constitution_sha // empty' 2>/dev/null)"
fi

"$JQ" -nc \
  --arg ts "$NOW" \
  --argjson wallet_usdc "${wallet_usdc:-null}" \
  --argjson wallet_delta "${wallet_delta:-null}" \
  --argjson mrr "${mrr_usd:-null}" \
  --argjson makes "${makes_usd:-null}" \
  --argjson spends "${spends_usd:-null}" \
  --arg lifeline "$lifeline" \
  --argjson cron_total "${cron_total:-0}" \
  --argjson cron_err "${cron_error_count:-0}" \
  --argjson hb_ratio "${hb_ok_ratio:-null}" \
  --arg last_hb "$last_hb_ts" \
  --argjson eval_fail "${eval_fail_24h:-0}" \
  --argjson viol "${violations_24h:-0}" \
  --arg sha "$sha" \
  '{ts:$ts,
    finances:{wallet_usdc:$wallet_usdc, wallet_delta_usdc:$wallet_delta, mrr_usd:$mrr, makes_usd:$makes, spends_usd:$spends, lifeline:$lifeline},
    activity:{cron_total:$cron_total, cron_error_count:$cron_err},
    health:{heartbeat_ok_ratio:$hb_ratio, last_heartbeat_ts:($last_hb|select(.!="")), eval_fail_24h:$eval_fail, violations_24h:$viol},
    identity:{constitution_sha:($sha|select(.!=""))}}'
