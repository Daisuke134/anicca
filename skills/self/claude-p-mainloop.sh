#!/bin/bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
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
WORKDIR="$LIFE_MANAGER_REPO"
LOG_DIR="$HOME/.local/state/life-manager/logs"
mkdir -p "$LOG_DIR"
LOG_OUT="$LOG_DIR/claude-p-mainloop.out.log"
LOG_ERR="$LOG_DIR/claude-p-mainloop.err.log"

STATE_DIR="$HOME/.local/state/life-manager/state"
mkdir -p "$STATE_DIR"
PIDFILE="$STATE_DIR/claude-p-mainloop.pid"

PAUSE_FILE="$HOME/.anicca/claude-p-loop.pause"
PROMPT_FILE="$SKILL_DIR/claude-p-mainloop-prompt.txt"

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

TIMEOUT_LIB="$SKILL_DIR/mainloop-timeout-lib.sh"
if [ ! -f "$TIMEOUT_LIB" ]; then
  echo "$(now) FATAL timeout lib missing: $TIMEOUT_LIB" >> "$LOG_ERR"
  exit 1
fi
# shellcheck source=./mainloop-timeout-lib.sh
source "$TIMEOUT_LIB"
TIMEOUT_SEC="$(resolve_mainloop_timeout_sec)"

echo "$(now) launching claude --model sonnet (hard timeout ${TIMEOUT_SEC}s) cwd=$(pwd)" >> "$LOG_OUT"
timeout "$TIMEOUT_SEC" claude --model sonnet --dangerously-skip-permissions -p "$(cat "$PROMPT_FILE")" \
  >> "$LOG_OUT" 2>> "$LOG_ERR"
STATUS=$?
echo "$(now) claude-p-mainloop exit status=$STATUS" >> "$LOG_OUT"
exit "$STATUS"
