#!/usr/bin/env bash
# PROP-008: with ANICCA_INSTANCE set to a brand-new probe instance (no queue/accounts/
# ledger files exist yet), BOTH run.sh (EARN_MODE=discover) and monitor.sh must report
# that probe instance's empty state and must NEVER read/print the default (myclaude)
# instance's ledger lines or account handles. This is the check PROP-005's grep cannot
# catch (grep proves no model-name branching, not that monitor.sh sources
# _instance_paths.sh at all).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROBE="prop008-probe-$$"
FAIL=0

export ANICCA_INSTANCE="$PROBE"

# --- run.sh: must report nothing-to-post for the probe instance, must not touch the default queue ---
# Compare FILENAME SETS only (not full `ls -la` metadata) — metadata/mtime can shift from
# unrelated concurrent processes (e.g. the live claude-p hourly cron) and would false-positive.
DEFAULT_QUEUE_BEFORE=""
[ -d "$HOME/clips/queue" ] && DEFAULT_QUEUE_BEFORE=$(ls -1 "$HOME/clips/queue" 2>/dev/null | sort)

RUN_OUT=$(EARN_MODE=discover bash "$DIR/run.sh" 2>&1)
echo "$RUN_OUT" | grep -qi "nothing to post" || { echo "FAIL: run.sh (probe instance) did not report 'nothing to post': $RUN_OUT"; FAIL=1; }

DEFAULT_QUEUE_AFTER=""
[ -d "$HOME/clips/queue" ] && DEFAULT_QUEUE_AFTER=$(ls -1 "$HOME/clips/queue" 2>/dev/null | sort)
[ "$DEFAULT_QUEUE_BEFORE" = "$DEFAULT_QUEUE_AFTER" ] || { echo "FAIL: default myclaude queue file-set changed during probe-instance run.sh (before=[$DEFAULT_QUEUE_BEFORE] after=[$DEFAULT_QUEUE_AFTER])"; FAIL=1; }

# --- monitor.sh: must show the probe's (empty) state, never a myclaude ledger line/handle ---
MON_OUT=$(bash "$DIR/monitor.sh" 2>&1)
if echo "$MON_OUT" | grep -q "aiclipsvault"; then
  echo "FAIL: monitor.sh leaked the default instance's account handle (aiclipsvault) while ANICCA_INSTANCE=$PROBE"
  FAIL=1
fi
if echo "$MON_OUT" | grep -qE "posts recorded[[:space:]]*:[[:space:]]*[1-9]"; then
  echo "FAIL: monitor.sh reported nonzero posts for a probe instance that has never posted (cross-instance ledger leak)"
  FAIL=1
fi

# cleanup any dirs the probe instance may have created
rm -rf "$HOME/clips/queue-$PROBE" "$HOME/clips/posted-$PROBE" "$HOME/.cloak/clip-accounts-$PROBE.json" 2>/dev/null

if [ "$FAIL" = "0" ]; then echo "ALL PASS"; else echo "TESTS FAILED"; exit 1; fi
