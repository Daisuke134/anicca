#!/usr/bin/env bash
# Shared helpers for anicca-predict (#337 P14, spec 18 §3 PREDICTION / MiroFish-style wager).
# Sourced by predict.sh / resolve.sh. No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash

JQ=/usr/bin/jq
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
PREDICTIONS="$STATE_DIR/predictions.jsonl"
POT="$STATE_DIR/predict-pot.jsonl"
TRACE="$STATE_DIR/predict.jsonl"
EVIDENCE_DIR="$STATE_DIR/predict-evidence"

mkdir -p "$STATE_DIR" "$EVIDENCE_DIR"
touch "$PREDICTIONS"

# pr_now → current unix time, overridable for tests via PREDICT_NOW_OVERRIDE.
pr_now() { echo "${PREDICT_NOW_OVERRIDE:-$(date +%s)}"; }

# pr_id <string> → deterministic 16-hex id.
pr_id() { printf '%s' "$1" | /usr/bin/shasum -a 256 | cut -c1-16; }

# pr_mktemp <tag> → temp file under STATE_DIR (never /tmp).
pr_mktemp() { mktemp "$STATE_DIR/.tmp-pr-${1:-x}-XXXX.$$"; }

# pr_testable <claim> → exit 0 iff the claim has BOTH a metric token AND a deadline token.
# Metric:   a digit, OR one of {first paid contract views USDC $ % >= ≥ >}.
# Deadline: one of {within by before "in N (h|hours|d|days)" deadline}.
pr_testable() {
  local c="$1"
  printf '%s' "$c" | grep -Eiq '([0-9]|first|paid|contract|views|usdc|\$|%|>=|≥|>)' || return 1
  printf '%s' "$c" | grep -Eiq '(within|by |before|deadline|in [0-9]+ ?(h|hours|d|days))' || return 1
  return 0
}

# pr_horizon_secs <claim> → seconds until deadline. Parses "within/in N h|d|hours|days".
# Default 48h when a deadline token exists but no parseable N-unit horizon.
pr_horizon_secs() {
  local c="$1" n unit
  if [[ "$c" =~ (within|in)[[:space:]]+([0-9]+)[[:space:]]*(h|hours|hour|d|days|day) ]]; then
    n="${BASH_REMATCH[2]}"; unit="${BASH_REMATCH[3]}"
    case "$unit" in
      h|hour|hours) echo $(( n * 3600 )) ;;
      d|day|days)   echo $(( n * 86400 )) ;;
    esac
    return 0
  fi
  echo $(( 48 * 3600 ))
}
