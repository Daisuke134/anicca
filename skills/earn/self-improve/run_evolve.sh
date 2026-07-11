#!/bin/bash
# run_evolve.sh — LOOP 2's recurring self-improve trigger (REQ-OE7). Full autonomous cycle
# (close-loop revision, 2026-07-08): OBSERVE (read the REAL realized-P&L ledger) -> EVOLVE (real
# openevolve, risk-adjusted fitness) -> promote_gate.sh (per-candidate fresh adversary, REQ-RH4) ->
# PROMOTE-or-log. Invokes openevolve (real CLI entrypoint `openevolve-run`, NO `.py` suffix — that
# name does not exist anywhere on this machine, confirmed by `ls <venv>/bin` after `pip install
# openevolve`) as the ONLY mechanism that proposes strategy edits (REQ-OE1) — no hand-written
# mutation/selection code path is added here as a substitute. No human prompt anywhere in this
# path; every input is a file already on disk (this script, config.yaml,
# strategies/pm_backtest_strategy.py, evaluator.py) or the real earn-ledger.jsonl (read-only).
#
# This phase (behavioral-spec.md) is paper/backtest ONLY: evaluator.py never invokes any live
# order-execution path, and this script never sets/relies on a nonzero spend cap (INV-6).
# promote_gate.sh's own promotion step only ever commits a backtest strategy FILE — never a live
# trade.
#
# Trigger wiring (REQ-OE7): launchd/ai.anicca.self-improve-evolve.plist invokes this script on a
# recurring StartInterval — never a human manually running it. launchd gives the process a
# minimal default PATH (no project/user customization), so this script does NOT rely on `command
# -v` finding openevolve (or python3, or claude) on PATH at all — it invokes fixed, durable,
# non-scratchpad paths by ABSOLUTE path (`~/.anicca-venvs/self-improve/bin/openevolve-run` /
# `.../bin/python3`, expanded via $HOME so they resolve under whatever HOME launchd sets; `claude`
# resolves via the plist's own explicit PATH, which includes /opt/homebrew/bin). That venv is
# intentionally OUTSIDE this git repo (never committed) and outside any session scratchpad (which
# gets cleaned between sessions).
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
PY_BIN="${PY_BIN:-$HOME/.anicca-venvs/self-improve/bin/python3}"

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

# ---- OBSERVE (close-loop Gap 1): read the REAL realized-P&L ledger before evolving anything. ----
# Read-only (lib/ledger_reader.py never writes earn-ledger.jsonl — see its own module docstring).
# A missing/sparse ledger degrades to an all-zero summary, never blocks this run (logged either
# way so the loop's own realized track record is visible over time, not just this run's backtest
# fitness).
if [ -x "$PY_BIN" ]; then
  OBSERVE_JSON="$("$PY_BIN" "$SKILL_DIR/lib/ledger_reader.py" 2>>"$LOG")"
  echo "$(now) OBSERVE realized_ledger=${OBSERVE_JSON:-'{"error":"ledger_reader produced no output"}'}" >> "$LOG"
else
  echo "$(now) OBSERVE SKIPPED (python not found at $PY_BIN) — proceeding to EVOLVE anyway" >> "$LOG"
fi

# ---- checkpoint_resume (self-improve-checkpoint-resume, REQ-CR6-9,12): resume this cycle's
# openevolve-run from the most recent PRIOR cycle's checkpoint instead of cold-starting every
# ~6h cycle (root cause of 3 consecutive tied-score, zero-forward-progress cycles — see
# behavioral-spec.md sources). Read-only path selection only (lib/checkpoint_resume.py never
# mutates anything on disk); a crashed/missing-$PY_BIN resume-check degrades to the same
# no-checkpoint fallback as "no prior run exists yet" for the purposes of this invocation
# (REQ-CR12) — resuming is a pure optimization, never a precondition for this cycle to run.
# Positioned BEFORE the $OPENEVOLVE_BIN existence check (not just before its invocation) so
# resume-check evidence lands in $LOG even on the rare path where openevolve itself is missing.
CHECKPOINT_PATH="$(RUNS_DIR="$RUNS_DIR" RUN_ID="$RUN_ID" "$PY_BIN" "$SKILL_DIR/lib/checkpoint_resume.py" 2>>"$LOG")"
CHECKPOINT_STATUS=$?
CHECKPOINT_ARGS=()
if [ "$CHECKPOINT_STATUS" -ne 0 ]; then
  echo "$(now) checkpoint_resume: resume-check crashed exit_status=$CHECKPOINT_STATUS" >> "$LOG"
elif [ -n "$CHECKPOINT_PATH" ]; then
  echo "$(now) checkpoint_resume: resuming from checkpoint $CHECKPOINT_PATH" >> "$LOG"
  CHECKPOINT_ARGS=(--checkpoint "$CHECKPOINT_PATH")
else
  echo "$(now) checkpoint_resume: no prior checkpoint found" >> "$LOG"
fi

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
  "${CHECKPOINT_ARGS[@]:-}" \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(now) run_id=$RUN_ID status=$STATUS" >> "$LOG"

# ---- promote_gate.sh (close-loop Gap 3, REQ-RH4 step 3): per-candidate fresh adversary review. --
# Only attempted when openevolve itself exited cleanly (REQ-OE6: a crashed/killed/timed-out run is
# inconclusive — no candidate from it is promoted, and this branch is skipped entirely) AND it
# actually produced a best-candidate file (openevolve/controller.py::_save_best_program writes
# `<output>/best/best_program.py` — verified against the installed openevolve==0.3.0 source, see
# execution-notes-self-improve.md). promote_gate.sh's own deterministic pre-checks
# (scope_guard/stage1/stage2/trip-wire, via lib/promote_gate.py) decide WITHOUT any LLM cost
# whether this candidate is even eligible for the real adversary call — an ineligible candidate
# (the common case for a small/free-model run) never spends a token here.
BEST_CANDIDATE="$RUN_DIR/best/best_program.py"
if [ "$STATUS" -eq 0 ] && [ -f "$BEST_CANDIDATE" ]; then
  echo "$(now) promote_gate: assessing $BEST_CANDIDATE" >> "$LOG"
  "$SKILL_DIR/promote_gate.sh" "$BEST_CANDIDATE" "$RUN_DIR" >> "$LOG" 2>&1
  PROMOTE_STATUS=$?
  echo "$(now) promote_gate: exit=$PROMOTE_STATUS verdict=$(cat "$RUN_DIR/verdict.json" 2>/dev/null || echo 'no verdict.json written')" >> "$LOG"
else
  echo "$(now) promote_gate SKIPPED (openevolve status=$STATUS, best_candidate_exists=$([ -f "$BEST_CANDIDATE" ] && echo yes || echo no))" >> "$LOG"
fi

exit "$STATUS"
