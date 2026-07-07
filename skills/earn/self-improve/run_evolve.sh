#!/bin/bash
# run_evolve.sh — LOOP 2's recurring self-improve trigger (REQ-OE7). Invokes openevolve
# (real CLI entrypoint `openevolve-run`, NO `.py` suffix — that name does not exist anywhere on
# this machine, confirmed by `ls <venv>/bin` after `pip install openevolve`) as the ONLY
# mechanism that proposes strategy edits (REQ-OE1) — no hand-written mutation/selection code
# path is added here as a substitute. No human prompt anywhere in this path; every input is a
# file already on disk (this script, config.yaml, strategies/pm_backtest_strategy.py,
# evaluator.py).
#
# This phase (behavioral-spec.md) is paper/backtest ONLY: evaluator.py never invokes any live
# order-execution path, and this script never sets/relies on a nonzero spend cap (INV-6).
#
# Trigger wiring (REQ-OE7): launchd/ai.anicca.self-improve-evolve.plist invokes this script on a
# recurring StartInterval — never a human manually running it. launchd gives the process a
# minimal default PATH (no project/user customization), so this script does NOT rely on `command
# -v` finding openevolve on PATH at all — it invokes a fixed, durable, non-scratchpad venv by
# ABSOLUTE path (`~/.anicca-venvs/self-improve/bin/openevolve-run`, expanded via $HOME so it
# resolves under whatever HOME launchd sets). That venv is intentionally OUTSIDE this git repo
# (never committed) and outside any session scratchpad (which gets cleaned between sessions).
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
# config.yaml's database.db_path ("runs/db") is a RELATIVE path that openevolve resolves against
# the process's CWD, not against config.yaml's own location — so this script must not depend on
# being invoked FROM $SKILL_DIR (launchd's WorkingDirectory key covers the launchd path, but a
# manual/cron/other invocation with a different CWD would otherwise silently write runs/db/ under
# the WRONG directory). Force it explicitly.
cd "$SKILL_DIR" || { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) FATAL cannot cd to $SKILL_DIR" >&2; exit 1; }
STATE_DIR="$SKILL_DIR/../state"; mkdir -p "$STATE_DIR"
RUNS_DIR="$SKILL_DIR/runs"; mkdir -p "$RUNS_DIR"
LOG="$STATE_DIR/self-improve-evolve.log"
OPENEVOLVE_BIN="${OPENEVOLVE_BIN:-$HOME/.anicca-venvs/self-improve/bin/openevolve-run}"

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

if [ ! -x "$OPENEVOLVE_BIN" ]; then
  # LOUD failure, never a silent "pretend success" exit 0: a missing openevolve binary means
  # REQ-OE7's recurring trigger cannot run at all, and that must be visible (non-zero exit +
  # a clear log line), not swallowed as if it were merely "inconclusive this tick". The
  # baseline strategy file is still untouched either way (REQ-OE6) since we never get to
  # invoking openevolve.
  echo "$(now) FATAL openevolve-run not found or not executable at $OPENEVOLVE_BIN run_id=$RUN_ID" >> "$LOG"
  echo "FATAL: openevolve-run not found or not executable at $OPENEVOLVE_BIN" >&2
  echo "Install it with: python3 -m venv \"$HOME/.anicca-venvs/self-improve\" && \"$HOME/.anicca-venvs/self-improve/bin/pip\" install --no-cache-dir openevolve openai" >&2
  exit 1
fi

# REQ-OE6: a crashed/killed/timed-out openevolve run is treated as inconclusive — no candidate
# from it is promoted, and the baseline strategy file (outside $RUN_DIR) is left untouched. We
# rely on openevolve-run's own exit code here; a non-zero exit is logged, never silently
# retried as a "success", and nothing outside $RUN_DIR is ever written by this invocation.
"$OPENEVOLVE_BIN" \
  "$SKILL_DIR/strategies/pm_backtest_strategy.py" \
  "$SKILL_DIR/evaluator.py" \
  --config "$SKILL_DIR/config.yaml" \
  --iterations "$ITERATIONS" \
  --output "$RUN_DIR" \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(now) run_id=$RUN_ID status=$STATUS" >> "$LOG"
exit "$STATUS"
