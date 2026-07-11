#!/bin/bash
# claude-p-mainloop.sh — claude-p's autonomous MAIN loop runner (human-funded builder/monitor of
# the Anicca colony). Fired on a recurring schedule by
# ~/Library/LaunchAgents/ai.anicca.claude-p-mainloop.plist (StartInterval, RunAtLoad=false — this
# job never auto-fires on plist load, only on its schedule or an explicit `launchctl kickstart`).
#
# Single-instance guard: a pidfile, NOT flock — macOS has no flock(1) binary (same gotcha already
# documented at skills/_shared/proactive-loop.sh:5, which uses Python fcntl instead; this script
# has no Python dependency so a pidfile is the simpler equivalent for a bash-only guard).
#
# Kill-switch: touch ~/.anicca/claude-p-loop.pause to stop this loop cold before its next fire.
#
# Model division (REQ-005, spec: .vcsdd/features/build-loop-unify/specs/behavioral-spec.md):
# this loop is LOOP B (the large brain, Anthropic subscription). It defaults to
# `claude --model sonnet` unchanged from prior behavior; an operator may override with
# CLAUDE_P_MAINLOOP_MODEL=opus for a heavy-design run without editing this script or the
# launchd plist.
#
# Test isolation (REQ-006): this script's pidfile is the SAME file the live launchd cron
# uses ($HOME/.openclaw/state/claude-p-mainloop.pid), so tests must never run it against
# production paths. CLAUDE_P_MAINLOOP_TEST=1 + CLAUDE_P_MAINLOOP_STATE_DIR /
# CLAUDE_P_MAINLOOP_LOG_DIR / CLAUDE_P_MAINLOOP_PAUSE_FILE / CLAUDE_P_MAINLOOP_WORKDIR
# redirect those four paths to a temp dir, mirroring founder-loop.sh's own established
# FOUNDER_TEST/FOUNDER_DIR seam. Unset (the launchd/production case) -> every path below
# resolves exactly as before this seam existed.
#
# The prompt text lives in a SEPARATE file (claude-p-mainloop-prompt.txt, same directory) and is
# passed via `"$(cat "$PROMPT_FILE")"` — a command substitution — rather than being inlined in a
# double-quoted string in this script. The prompt contains literal backticks (`bash ...`, `.env`,
# etc.); embedding those directly inside a double-quoted bash string would make bash execute them
# as command substitutions (see memory feedback_never_backtick_in_double_quoted_commit_message.md
# for the exact same footgun in a git commit message). Reading the file via $(cat ...) sidesteps
# this entirely: cat's stdout is captured as literal bytes, and the surrounding double quotes only
# prevent word-splitting/globbing of the captured text — the backticks inside it are never
# re-parsed as shell syntax.
set -u

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

# REQ-006 test-isolation seam: production defaults are UNCHANGED when CLAUDE_P_MAINLOOP_TEST
# is unset. Mirrors founder-loop.sh's FOUNDER_TEST/FOUNDER_DIR pattern.
if [ "${CLAUDE_P_MAINLOOP_TEST:-}" = "1" ] && [ -n "${CLAUDE_P_MAINLOOP_WORKDIR:-}" ]; then
  WORKDIR="$CLAUDE_P_MAINLOOP_WORKDIR"
else
  WORKDIR="$HOME/anicca-project"
fi
if [ "${CLAUDE_P_MAINLOOP_TEST:-}" = "1" ] && [ -n "${CLAUDE_P_MAINLOOP_LOG_DIR:-}" ]; then
  LOG_DIR="$CLAUDE_P_MAINLOOP_LOG_DIR"
else
  LOG_DIR="$HOME/.openclaw/logs"
fi
mkdir -p "$LOG_DIR"
LOG_OUT="$LOG_DIR/claude-p-mainloop.out.log"
LOG_ERR="$LOG_DIR/claude-p-mainloop.err.log"

if [ "${CLAUDE_P_MAINLOOP_TEST:-}" = "1" ] && [ -n "${CLAUDE_P_MAINLOOP_STATE_DIR:-}" ]; then
  STATE_DIR="$CLAUDE_P_MAINLOOP_STATE_DIR"
else
  STATE_DIR="$HOME/.openclaw/state"
fi
mkdir -p "$STATE_DIR"
PIDFILE="$STATE_DIR/claude-p-mainloop.pid"

if [ "${CLAUDE_P_MAINLOOP_TEST:-}" = "1" ] && [ -n "${CLAUDE_P_MAINLOOP_PAUSE_FILE:-}" ]; then
  PAUSE_FILE="$CLAUDE_P_MAINLOOP_PAUSE_FILE"
else
  PAUSE_FILE="$HOME/.anicca/claude-p-loop.pause"
fi
PROMPT_FILE="$SKILL_DIR/claude-p-mainloop-prompt.txt"

# REQ-005 model division: default sonnet, opus override for heavy-design runs, unrelated to
# the CLAUDE_P_MAINLOOP_TEST seam above (usable in production too).
MODEL="${CLAUDE_P_MAINLOOP_MODEL:-sonnet}"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

echo "===== $(now) claude-p-mainloop fire (pid $$) =====" >> "$LOG_OUT"

# ---- Kill-switch (checked FIRST, before anything else — REQ from the task). ----
if [ -f "$PAUSE_FILE" ]; then
  echo "$(now) PAUSED — kill-switch file present at $PAUSE_FILE — exiting 0" >> "$LOG_OUT"
  exit 0
fi

# ---- Single-instance guard (pidfile; macOS has no flock(1)). ----
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "$(now) already running (pid $OLD_PID) — exiting 0" >> "$LOG_OUT"
    exit 0
  fi
  echo "$(now) stale pidfile (pid ${OLD_PID:-unknown} not alive) — reclaiming" >> "$LOG_OUT"
fi
echo "$$" > "$PIDFILE"
cleanup() { rm -f "$PIDFILE"; }
trap cleanup EXIT

if [ ! -f "$PROMPT_FILE" ]; then
  echo "$(now) FATAL prompt file missing: $PROMPT_FILE" >> "$LOG_ERR"
  exit 1
fi

cd "$WORKDIR" || { echo "$(now) FATAL cannot cd to $WORKDIR" >> "$LOG_ERR"; exit 1; }

echo "$(now) launching claude --model $MODEL (hard timeout 3600s) cwd=$(pwd)" >> "$LOG_OUT"
timeout 3600 claude --model "$MODEL" --dangerously-skip-permissions -p "$(cat "$PROMPT_FILE")" \
  >> "$LOG_OUT" 2>> "$LOG_ERR"
STATUS=$?
echo "$(now) claude-p-mainloop exit status=$STATUS" >> "$LOG_OUT"
exit "$STATUS"
