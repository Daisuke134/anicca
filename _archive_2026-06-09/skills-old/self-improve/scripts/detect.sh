#!/usr/bin/env bash
# detect: read meta-cognition JSON (stdin or $1) + raw state files → decide
# "what's wrong?" → emit JSONL of detected issues, one object per line:
#   {ts, issue_type, severity, evidence, affected_skill}
# No issues → no output, exit 0.
set -uo pipefail

STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
JQ=/usr/bin/jq
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CUTOFF="$(( $(date -u +%s) - 86400 ))"

EVAL_COST="$STATE_DIR/eval-cost.jsonl"
DAILY="$STATE_DIR/daily-report.jsonl"

# read meta-cognition JSON
if [ "${1:-}" = "-" ] || [ -z "${1:-}" ]; then
  META="$(cat)"
else
  META="$1"
fi
[ -z "$META" ] && { echo "detect.sh: empty meta-cognition input" >&2; exit 2; }

iso_to_epoch() {
  local t="${1%Z}"; t="${t%%.*}"
  date -u -j -f "%Y-%m-%dT%H:%M:%S" "$t" +%s 2>/dev/null || echo 0
}

emit() {
  # emit <issue_type> <severity> <evidence> <affected_skill>
  "$JQ" -nc \
    --arg ts "$NOW" --arg it "$1" --arg sev "$2" --arg ev "$3" --arg sk "$4" \
    '{ts:$ts, issue_type:$it, severity:$sev, evidence:$ev, affected_skill:($sk|select(.!="")) }'
}

# map an eval rubric task_class to a skill name (best-effort)
map_task_class() {
  case "$1" in
    post-to-x|*x*) echo "anicca-x-useful" ;;
    daily-report*) echo "daily-report" ;;
    *) echo "" ;;
  esac
}

# ---- rule: slop-detected (any eval-cost pass:false within 24h) ----
if [ -r "$EVAL_COST" ]; then
  while IFS= read -r row; do
    [ -z "$row" ] && continue
    pass="$(printf '%s' "$row" | "$JQ" -r 'if has("pass") then .pass else "missing" end' 2>/dev/null)"
    [ "$pass" != "false" ] && continue
    rts="$(printf '%s' "$row" | "$JQ" -r '.ts // empty' 2>/dev/null)"
    [ -z "$rts" ] && continue
    [ "$(iso_to_epoch "$rts")" -lt "$CUTOFF" ] && continue
    tc="$(printf '%s' "$row" | "$JQ" -r '.rubric_task_class // "unknown"' 2>/dev/null)"
    tot="$(printf '%s' "$row" | "$JQ" -r '.total // "?"' 2>/dev/null)"
    emit "slop-detected" "warn" "eval $tc scored $tot (<0.7) at $rts" "$(map_task_class "$tc")"
    break  # one slop issue per run is enough; fix raises the bar broadly
  done < "$EVAL_COST"
fi

# ---- rule: law-violation (any non-OK constitution decision within 24h) ----
viol="$(printf '%s' "$META" | "$JQ" -r '.health.violations_24h // 0' 2>/dev/null)"
if [ "${viol:-0}" -gt 0 ] 2>/dev/null; then
  emit "law-violation" "critical" "$viol constitution-violation row(s) with decision!=OK in last 24h" "anicca-constitution-guard"
fi

# ---- rule: cron-degraded (cron_error_count > 10) ----
cerr="$(printf '%s' "$META" | "$JQ" -r '.activity.cron_error_count // 0' 2>/dev/null)"
if [ "${cerr:-0}" -gt 10 ] 2>/dev/null; then
  emit "cron-degraded" "warn" "$cerr crons in error state (threshold 10)" ""
fi

# ---- rule: income-stalled (wallet 0 AND lifeline not THRIVE) ----
wusdc="$(printf '%s' "$META" | "$JQ" -r '.finances.wallet_usdc // "null"' 2>/dev/null)"
life="$(printf '%s' "$META" | "$JQ" -r '.finances.lifeline // "unknown"' 2>/dev/null)"
if [ "$wusdc" != "null" ] && awk "BEGIN{exit !($wusdc == 0)}" 2>/dev/null && [ "$life" != "THRIVE" ]; then
  emit "income-stalled" "info" "wallet 0 USDC and lifeline=$life" "anicca-earn-lancers"
fi

# ---- rule: report-broken (daily-report newest row > 24h stale) ----
if [ -r "$DAILY" ]; then
  dts="$(tail -1 "$DAILY" | "$JQ" -r '.ts // empty' 2>/dev/null)"
  if [ -n "$dts" ] && [ "$(iso_to_epoch "$dts")" -lt "$CUTOFF" ]; then
    emit "report-broken" "warn" "daily-report newest row $dts is >24h stale" "daily-report"
  fi
fi

exit 0
