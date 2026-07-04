#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
# self-fix.sh — TRUE autonomous self-heal launcher (no human, no "file issue and wait"). When a money loop
# (sonnet) hits a code/automation blocker it cannot fix in-pass, it calls this to spawn a detached, full-power
# OPUS claude that actually diagnoses → edits the mother-repo code → VERIFIES by running it and confirming the
# REAL side-effect → commits + pushes. That is how the loops self-improve their own code without babysitting.
# Usage: self-fix.sh <loop-name> "<blocker + concrete fix hint>"
# Idempotent: one self-fix session per loop at a time (skips if already running).
set -uo pipefail
LOOP="${1:?loop name}"; BLOCKER="${2:?blocker+hint}"
SOCK="/tmp/anicca-selffix-$LOOP-tmux.sock"; SESSION="anicca-selffix-$LOOP"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"
LOG="$HOME/.openclaw/logs/self-fix-$LOOP.log"; mkdir -p "$(dirname "$LOG")"
# one fixer per loop; don't stack
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then echo "$(date '+%F %T') self-fix[$LOOP] already running — skip" >> "$LOG"; echo "self-fix[$LOOP] already running"; exit 0; fi
TASK="AUTONOMOUS SELF-FIX for the ${LOOP} loop. You are a full-power Opus dev with browser (CloakBrowser daily-driver CDP :9222), Bash, Edit. NEVER ask a human; a blocker is not stop. BLOCKER + HINT: ${BLOCKER}. DO: (1) reproduce the failure yourself and find the ROOT cause (read the actual code + run it + watch where it breaks); (2) fix the code in the mother repo (~/anicca or ~/.openclaw) — if the root cause is a brittle DOM-coordinate/selector script that broke on a UI change, do NOT just re-tune coordinates: rebuild the failing step as two-layer agentic (thin script opens the page, then YOU look at real screenshots and decide each click/type, loop until the real success signal); (3) VERIFY with a REAL side-effect (an actually-published skill URL / a real posted comment / the tool actually succeeding once) — a patch that only compiles is NOT done, no dry runs, no fake success; (4) git add -A && commit && push in the correct repo (verify remote first); (5) clear the loop's selfheal-request json if the fix resolves it. If after honest effort it is truly impossible, THEN invoke self/issue-dev with a precise diagnosis. Report what you fixed + the real evidence at the end."
tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model opus --dangerously-skip-permissions --add-dir "$HOME" -- "$TASK"
echo "$(date '+%F %T') self-fix[$LOOP] SPAWNED (opus): ${BLOCKER:0:80}" >> "$LOG"
echo "self-fix[$LOOP] spawned (opus, detached). log: $LOG"
