#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
# self-fix.sh — TRUE autonomous self-heal launcher (no human, no "file issue and wait"). When a loop hits a
# code/automation blocker it cannot fix in-pass, it (or a healthcheck) calls this to spawn a detached, full-power
# OPUS claude that diagnoses → edits the correct mother-repo code → VERIFIES by a REAL side-effect → commits+pushes
# → writes a result marker. That is how the loops self-improve their own code without babysitting.
# Usage: self-fix.sh <loop-name> "<blocker + concrete fix hint>"
set -uo pipefail
# FIND-025: NORMALIZE the loop name to a single canonical form ("<x>-loop") so every call site — healthcheck
# (HC_LOOP=capafy-loop), STARTUP prompts (capafy), verify-loops (capafy) — maps to ONE session name + ONE result
# marker. Without this, "capafy" and "capafy-loop" spawn two mutually-unaware fixers and split the marker the
# anti-fake verifier reads. Idempotent: strip a trailing -loop then re-add it.
LOOP="${1:?loop name}"; LOOP="${LOOP%-loop}-loop"; BLOCKER="${2:?blocker+hint}"
SOCK="/tmp/anicca-selffix-$LOOP-tmux.sock"; SESSION="anicca-selffix-$LOOP"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"
STATE="$HOME/.openclaw/state"; mkdir -p "$STATE"
LOG="$HOME/.openclaw/logs/self-fix-$LOOP.log"; mkdir -p "$(dirname "$LOG")"
RESULT="$STATE/.self-fix-$LOOP.result"       # the fixer writes SUCCESS/FAIL + evidence here (FIND-003)
STARTMARK="$STATE/.self-fix-$LOOP.started"    # epoch when the current fixer was spawned (FIND-005 stale-guard)
MAX_FIXER_MIN=180                             # FIND-023: a fixer older than 3h is presumed hung → kill+respawn. Set
                                              # ABOVE any legitimate fix duration (a real fix rarely needs >3h) so the
                                              # 6h audit re-invocation cannot kill an in-progress long fix; only a
                                              # genuinely stuck session (>3h) is replaced, still within the 6h window.

# FIND-005: skip only if a RECENT fixer is still running; if it is older than MAX_FIXER_MIN, it is hung → replace it.
if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  age_min=999; [ -f "$STARTMARK" ] && age_min=$(( ( $(date +%s) - $(cat "$STARTMARK" 2>/dev/null||echo 0) ) / 60 ))
  if [ "$age_min" -lt "$MAX_FIXER_MIN" ]; then
    echo "$(date '+%F %T') self-fix[$LOOP] running (${age_min}min<${MAX_FIXER_MIN}) — skip" >> "$LOG"; echo "self-fix[$LOOP] already running (${age_min}min)"; exit 0
  fi
  # FIND-023: past the wall-clock ceiling, do NOT kill a fixer that is still actively generating (real progress) —
  # active generation always shows "esc to interrupt". Only a session idle/stuck past 3h is genuinely hung.
  if tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null | tail -6 | grep -qE 'esc to interrupt'; then
    echo "$(date '+%F %T') self-fix[$LOOP] ${age_min}min but STILL GENERATING — let it continue" >> "$LOG"; echo "self-fix[$LOOP] still working (${age_min}min)"; exit 0
  fi
  echo "$(date '+%F %T') self-fix[$LOOP] HUNG+idle (${age_min}min≥${MAX_FIXER_MIN}) → kill+respawn" >> "$LOG"
  tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null||true; pkill -f "claude --name $SESSION" 2>/dev/null||true; sleep 1
fi

# FIND-003/004: the fixer MUST verify a real side-effect, commit in the CORRECT repo (the one the edited file lives
# in — discovered via git rev-parse, NOT guessed), and write a result marker the caller/healthcheck can check.
printf 'RUNNING %s\n' "$(date -u +%FT%TZ)" > "$RESULT"
TASK="AUTONOMOUS SELF-FIX for the ${LOOP} loop. You are a full-power Opus dev with browser (CloakBrowser daily-driver CDP :9222), Bash, Edit. NEVER ask a human and NEVER present a menu — a blocker is not stop. BLOCKER + HINT: ${BLOCKER}.
DO, in order:
(1) Reproduce the failure yourself and find the ROOT cause (read the actual code + run it + watch where it breaks).
(2) Fix the code. If the root cause is a brittle DOM-coordinate/selector script that broke on a UI change, do NOT just re-tune coordinates: rebuild the failing step as two-layer agentic (a thin script opens the page, then YOU look at real screenshots and decide each click/type, looping until the real success signal appears).
(3) VERIFY with a REAL side-effect — an actually-published skill URL you then curl and see live / a real posted comment URL / the tool actually succeeding once end-to-end. A patch that only compiles is NOT done. No dry runs, no fake success, no 'should work'.
(4) COMMIT IN THE CORRECT REPO: for EACH file you changed, cd into its directory, run 'git rev-parse --show-toplevel' and 'git remote -v' to confirm which repo it is, then commit+push THERE. Ground truth: the Capafy publish pipeline lives under ~/.openclaw (remote = anicca-dais, PRIVATE) — commit those there, NOT to anicca-products. The loop harness lives under ~/anicca (remote = anicca, public). Never commit ~/.openclaw runtime state or secrets.
(5) Write the outcome to ${RESULT} as a single line: 'SUCCESS <utc> <one-line real evidence, e.g. published URL>' or 'FAIL <utc> <why + what is still blocked>'. If the fix resolved a selfheal-request json, rm it.
If after honest effort the fix is genuinely impossible (e.g. an external service is down), write FAIL with a precise diagnosis to ${RESULT} and invoke self/issue-dev — still never ask a human. Report what you fixed + the real evidence at the end."
tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model opus --dangerously-skip-permissions --add-dir "$HOME" -- "$TASK"
date +%s > "$STARTMARK"
echo "$(date '+%F %T') self-fix[$LOOP] SPAWNED (opus): ${BLOCKER:0:90}" >> "$LOG"
echo "self-fix[$LOOP] spawned (opus, detached). result→$RESULT log→$LOG"
