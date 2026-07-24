#!/usr/bin/env bash
# register-crons.sh — register the 3 Life Manager cron-COMMAND jobs on the OpenClaw Gateway.
#
# COMMAND payloads run deterministic node scripts on the Gateway host with ZERO model tokens
# (https://docs.openclaw.ai/automation/cron-jobs — "Command payloads ... without starting a
# model-backed isolated agent turn"). Requires operator.admin. Idempotent: each job is removed then
# re-created. Commands are generated from crons.json via build-commands.js (single source of truth).
#
# SINGLE-WRITER MIGRATION (race truth — do NOT run two schedulers at once):
#   - WAKE is race-safe: lm_wake_log atomic INSERT unique(uid,event_key) -> 409 (scheduler.js:53-64).
#   - TRAVEL + ASK are NOT race-safe: their dedup is an in-memory read-then-write (the [Travel] scan in
#     lib/travel.js and the lm_ask_log SELECT-then-POST in lib/ask.js) with no atomic unique constraint.
#     Two overlapping runs (Railway + this cron) can BOTH see dup=false and double-insert a [Travel]
#     block / double-ask.
# THEREFORE B4 cutover must be a SWITCH, not coexistence: disable the Railway scheduler loops (startScheduler + startTravelLoop/startAskLoop/startOnboardLoop) as you
# enable these cron jobs. Single writer at all times. (Follow-up hardening C-H1: atomic unique
# constraints on [Travel] + lm_ask_log so they become race-safe like wake.)
#
# command-cron requires openclaw >= the version that ships --command-argv (VERIFIED present in
# openclaw@latest 2026.6.10; ABSENT in 2026.6.1). The product gateway runs latest; do not run this on
# an older gateway.
#
# Usage:
#   LIFE_CALL_DIR=/abs/path/to/apps/life-call ./register-crons.sh
# LIFE_CALL_DIR = the apps/life-call directory ON THE GATEWAY HOST (it must contain
# skill-life-manager/scripts/{tick,travel,ask}.js and the lib/* + scheduler.js they require).
set -euo pipefail

DIR="${LIFE_CALL_DIR:?set LIFE_CALL_DIR to the apps/life-call dir on the gateway host}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/crons.json" ] || { echo "crons.json not found at $HERE/crons.json" >&2; exit 1; }

# Generate the rm+create lines from crons.json and run them under errexit (a failed create aborts).
node "$HERE/build-commands.js" "$DIR" | bash -eo pipefail

echo "--- registered Life Manager cron jobs ---"
openclaw cron list 2>/dev/null | grep -E "lm-wake|lm-travel|lm-ask" || {
  echo "WARN: jobs not visible in 'openclaw cron list' — check operator.admin + gateway version (>=2026.6.10)" >&2
  exit 1
}
