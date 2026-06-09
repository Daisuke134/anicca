#!/usr/bin/env bash
# run.sh — single Lancers beat. Default = --dry-run (safe). --confirm = LIVE.
#
# Flags:
#   --dry-run                      (default) scan + select + apply --dry-run, no submit
#   --confirm                      LIVE submit (read the runbook FIRST)
#   --offline-fixture <path>       use fixture instead of live Camofox (for tests/CI)
#   --max-apply N                  cap submits per run (default 3)
#   --max-budget-jpy B             cap budget per submit in --confirm mode
#
# Output: JSON envelope on stdout.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"

MODE="dry-run"
FIXTURE=""
MAX_APPLY=3
MAX_BUDGET_JPY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --confirm) MODE="live"; shift ;;
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    --max-apply) MAX_APPLY="$2"; shift 2 ;;
    --max-budget-jpy) MAX_BUDGET_JPY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

TS=$(date -u +%FT%TZ)
log "mode=$MODE fixture=${FIXTURE:-none}"

# Step 1: login (skip in offline mode)
if [ -z "$FIXTURE" ]; then
  "$SCRIPT_DIR/login-check.sh" || { err "login-check failed — abort"; exit 7; }
fi

# Step 2: scan → JIDs
if [ -n "$FIXTURE" ]; then
  JIDS=$("$SCRIPT_DIR/scan.sh" --offline-fixture "$FIXTURE")
else
  JIDS=$("$SCRIPT_DIR/scan.sh")
fi
[ -z "$JIDS" ] && { err "no JIDs found"; exit 8; }

# Step 3: select → top 3
if [ -n "$FIXTURE" ]; then
  CANDS=$(printf '%s\n' "$JIDS" | "$SCRIPT_DIR/select.sh" --offline-fixture "$FIXTURE")
else
  CANDS=$(printf '%s\n' "$JIDS" | "$SCRIPT_DIR/select.sh")
fi

# Step 4: apply
if [ "$MODE" = "dry-run" ]; then
  APPLY_OUT=$(printf '%s' "$CANDS" | "$SCRIPT_DIR/apply.sh" --dry-run)
else
  APPLY_ARGS=(--confirm --max-apply "$MAX_APPLY")
  [ "$MAX_BUDGET_JPY" -gt 0 ] && APPLY_ARGS+=(--max-budget-jpy "$MAX_BUDGET_JPY")
  APPLY_OUT=$(printf '%s' "$CANDS" | "$SCRIPT_DIR/apply.sh" "${APPLY_ARGS[@]}")
fi

# Step 5: write envelope
ENV=$("$JQ" -n --arg ts "$TS" --arg mode "$MODE" --argjson cands "$APPLY_OUT" \
              '{ts:$ts, mode:$mode, candidates:$cands}')

if [ "$MODE" = "dry-run" ]; then
  mkdir -p "$STATE_DIR"
  printf '%s' "$ENV" > "$STATE_DIR/earn-lancers-dry-run-latest.json"
fi

echo "$ENV"

# Step 6: optional Slack ping (HARD RULE #8: external report, never primary)
APPLIED_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "applied")] | length')
DRYRUN_N=$(echo "$ENV" | "$JQ" '[.candidates[] | select(.status == "dry-run")] | length')
slack_post "🟢 earn-lancers $MODE applied=$APPLIED_N dry-run=$DRYRUN_N"
