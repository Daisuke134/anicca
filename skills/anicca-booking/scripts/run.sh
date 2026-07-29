#!/usr/bin/env bash
# anicca-booking entry point — invoked by cron + heartbeat.
# Pipeline: scan_gcal_horizon → propose → apply (3-gate + state log + Slack)
# Ships the scan → propose → apply pipeline; browser form-fill remains agentic.
set -euo pipefail

SKILL_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
STATE_DIR="$LIFE_MANAGER_STATE_HOME/state/anicca-booking"
mkdir -p "$STATE_DIR"
RUN_LOG="$STATE_DIR/run.log"

# Load .env so children inherit Firecrawl / Slack / gog keys
set -a
[ -f "$LIFE_MANAGER_STATE_HOME/.env" ] && . "$LIFE_MANAGER_STATE_HOME/.env"
set +a

NOW="$(date -u +%FT%TZ)"
{
  echo "=== anicca-booking $NOW ==="
  echo "[step 1/3] scan_gcal_horizon"
  SLOTS_JSON="$(python3 "$SKILL_DIR/scan_gcal_horizon.py")"
  echo "$SLOTS_JSON" | jq -r 'length as $n | "  found \($n) empty slots"' 2>/dev/null || true

  echo "[step 2/3] propose"
  CANDIDATES_JSON="$(echo "$SLOTS_JSON" | python3 "$SKILL_DIR/propose.py")"
  APPROVED_N=$(echo "$CANDIDATES_JSON" | jq '[.[] | select(.status=="approved")] | length' 2>/dev/null || echo 0)
  BLOCKED_N=$(echo "$CANDIDATES_JSON" | jq '[.[] | select(.status | startswith("blocked"))] | length' 2>/dev/null || echo 0)
  echo "  approved=$APPROVED_N blocked=$BLOCKED_N"

  echo "[step 3/3] apply"
  SUMMARY_JSON="$(echo "$CANDIDATES_JSON" | python3 "$SKILL_DIR/apply.py")"
  echo "SUMMARY_JSON: $SUMMARY_JSON"
} 2>&1 | tee -a "$RUN_LOG"

# HARD RULE #14 verify-public-state
if [ -x "$LIFE_MANAGER_REPO/skills/_shared/verify-public-state.sh" ]; then
  bash "$LIFE_MANAGER_REPO/skills/_shared/verify-public-state.sh" "$RUN_LOG" "anicca-booking run" 1 || true
fi
