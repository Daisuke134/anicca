#!/bin/bash
# run_evolve.sh — LOOP 2's recurring self-improve trigger (REQ-OE7). Invokes openevolve
# (`openevolve-run.py`) as the ONLY mechanism that proposes strategy edits (REQ-OE1) — no
# hand-written mutation/selection code path is added here as a substitute. No human prompt
# anywhere in this path; every input is a file already on disk (this script, config.yaml,
# strategies/pm_backtest_strategy.py, evaluator.py).
#
# This phase (behavioral-spec.md) is paper/backtest ONLY: evaluator.py never invokes any live
# order-execution path, and this script never sets/relies on a nonzero spend cap (INV-6).
#
# Trigger wiring (REQ-OE7): launchd/ai.anicca.self-improve-evolve.plist invokes this script on a
# recurring StartInterval — never a human manually running it.
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$SKILL_DIR/../state"; mkdir -p "$STATE_DIR"
RUNS_DIR="$SKILL_DIR/runs"; mkdir -p "$RUNS_DIR"
LOG="$STATE_DIR/self-improve-evolve.log"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# money-safety / operator kill-switch (mirrors skills/earn/polymarket-trade/run.sh's own
# KILL-file convention): touch KILL next to this script to stop the recurring trigger cold.
if [ -f "$SKILL_DIR/KILL" ]; then
  echo "$(now) skip kill-switch" >> "$LOG"
  exit 0
fi

ITERATIONS="${SELF_IMPROVE_ITERATIONS:-20}"
RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$RUNS_DIR/$RUN_ID"
mkdir -p "$RUN_DIR"

if ! command -v openevolve-run.py >/dev/null 2>&1; then
  # openevolve is vendored/pip-installed in a LATER stage (not this deterministic-core phase —
  # disk-tight constraint documented in execution-notes-self-improve.md). Record an inconclusive
  # run rather than failing loudly on every cron tick; the baseline strategy file is left
  # untouched either way (REQ-OE6).
  echo "$(now) skip openevolve-not-installed run_id=$RUN_ID" >> "$LOG"
  exit 0
fi

# REQ-OE6: a crashed/killed/timed-out openevolve run is treated as inconclusive — no candidate
# from it is promoted, and the baseline strategy file (outside $RUN_DIR) is left untouched. We
# rely on openevolve-run.py's own exit code here; a non-zero exit is logged, never silently
# retried as a "success", and nothing outside $RUN_DIR is ever written by this invocation.
openevolve-run.py \
  "$SKILL_DIR/strategies/pm_backtest_strategy.py" \
  "$SKILL_DIR/evaluator.py" \
  --config "$SKILL_DIR/config.yaml" \
  --iterations "$ITERATIONS" \
  --output "$RUN_DIR" \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(now) run_id=$RUN_ID status=$STATUS" >> "$LOG"
exit "$STATUS"
