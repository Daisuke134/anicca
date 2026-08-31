#!/usr/bin/env bash
# article-self-fix.sh — TRUE autonomous self-heal launcher for the writer-agent loop (part 2/2 of
# the "render-verify + self-fix" pair, Dais's core ask: the loop must self-heal with no human
# babysitting). Copy+tweak of the proven pattern at ~/anicca/skills/self/self-fix.sh (see
# ~/anicca/skills/self/capafy-loop/capafy-loop-daily.sh STEP0 for that script's real calling
# convention -- this file mirrors its spawn/staleness/fingerprint/CLIProxyAPI-fallback structure
# almost verbatim; only the repo identity, task prompt, and log/state file names changed for this
# loop). When a step in article-daily.sh's pass hits a blocker it cannot fix in-pass (a broken
# publish script, a render-verify FAIL it cannot resolve itself, a selector that broke on a
# platform UI change), it calls THIS to spawn a detached, full-power development agent that diagnoses ->
# edits the correct repo's code -> VERIFIES by a real side-effect -> commits+pushes -> writes a
# result marker. That is the actual self-heal mechanism (never "file an issue and wait").
#
# Usage: article-self-fix.sh "<blocker + concrete fix hint>"
#
# Wiring note (explicitly NOT done by this file, per this task's scope): article-daily.sh's STEP0
# does not yet call this, and render-verify-draft.sh's STEP 6.5 slot does not yet exist -- both are
# authfix's follow-up wiring task after the current flat-restructure round completes. This script
# only needs to work correctly when invoked directly with a blocker string.
set -uo pipefail

LOOP="writer-agent"
BLOCKER="${1:?usage: article-self-fix.sh \"<blocker + concrete fix hint>\"}"

SOCK="/tmp/anicca-selffix-$LOOP-tmux.sock"
SESSION="anicca-selffix-$LOOP"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}/runtime/model-runner.sh}"
STATE="$HOME/.openclaw/state"; mkdir -p "$STATE"
LOG="$HOME/.openclaw/logs/self-fix-$LOOP.log"; mkdir -p "$(dirname "$LOG")"
RESULT="$STATE/.self-fix-$LOOP.result"       # the fixer writes SUCCESS/FAIL + evidence here
STARTMARK="$STATE/.self-fix-$LOOP.started"    # epoch when the current fixer was spawned (stale-guard)

# test seam (mirrors self-fix.sh's SELF_FIX_DRYRUN): print the identity + derived paths and exit
# BEFORE any tmux/side-effect. This is how this task's own verification runs ("--dry-run的に
# プロンプト組み立てのみ確認") without ever actually spawning a fixer.
if [ "${SELF_FIX_DRYRUN:-}" = "1" ]; then
  printf 'LOOP=%s SESSION=%s SOCK=%s RESULT=%s LOG=%s\n' "$LOOP" "$SESSION" "$SOCK" "$RESULT" "$LOG"
  exit 0
fi

# same volatile-status-line strip as self-fix.sh, so a genuinely FROZEN fixer produces the SAME
# fingerprint across checks (its reasoning/tool text is unchanged; only the timer ticks), while
# real progress (new text) changes it.
sf_pane_fingerprint() {
  printf '%s' "$1" | tail -25 \
    | sed -E 's/[0-9]+//g; s/esc to interrupt//g' \
    | tr -d '✻✳✶✢⏺◐◓◑◒·↑↓…' \
    | grep -avE 'tokens' \
    | cksum | awk '{print $1"-"$2}'
}
if [ "${1:-}" = "--fingerprint" ]; then sf_pane_fingerprint "$(cat)"; exit 0; fi

sf_should_continue() { [ "$1" = "1" ] && [ "$2" != "$3" ]; }
if [ "${1:-}" = "--should-continue" ]; then sf_should_continue "${2:-}" "${3:-}" "${4:-}"; exit $?; fi

MAX_FIXER_MIN=180   # a fixer older than 3h is presumed hung -> kill+respawn (same ceiling as self-fix.sh)

if tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  age_min=999; [ -f "$STARTMARK" ] && age_min=$(( ( $(date +%s) - $(cat "$STARTMARK" 2>/dev/null || echo 0) ) / 60 ))
  if [ "$age_min" -lt "$MAX_FIXER_MIN" ]; then
    echo "$(date '+%F %T') self-fix[$LOOP] running (${age_min}min<${MAX_FIXER_MIN}) — skip" >>"$LOG"
    echo "self-fix[$LOOP] already running (${age_min}min)"
    exit 0
  fi
  PANEHASH="$STATE/.self-fix-$LOOP.panehash"
  _pane="$(tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null)"
  cur="$(sf_pane_fingerprint "$_pane")"
  prev="$(cat "$PANEHASH" 2>/dev/null || echo none)"; printf '%s' "$cur" >"$PANEHASH"
  generating=0; printf '%s' "$_pane" | tail -6 | grep -qE 'esc to interrupt' && generating=1
  if sf_should_continue "$generating" "$cur" "$prev"; then
    echo "$(date '+%F %T') self-fix[$LOOP] ${age_min}min, generating + pane ADVANCED → real progress, continue" >>"$LOG"
    echo "self-fix[$LOOP] still progressing (${age_min}min)"
    exit 0
  fi
  echo "$(date '+%F %T') self-fix[$LOOP] ${age_min}min, pane frozen/idle (prev=$prev cur=$cur) → hung → kill+respawn" >>"$LOG"
  rm -f "$PANEHASH"
  tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null || true
  sleep 1
fi

printf 'RUNNING %s\n' "$(date -u +%FT%TZ)" >"$RESULT"
TASK="AUTONOMOUS SELF-FIX for the ${LOOP} loop (article-daily.sh / render-verify-draft.sh / the platform publish scripts). You are a full-power development agent with browser (the shared daily-driver CDP, default port 9222), Bash, Edit. NEVER ask a human and NEVER present a menu — a blocker is not stop. BLOCKER + HINT: ${BLOCKER}.
DO, in order:
(1) Reproduce the failure yourself and find the ROOT cause (read the actual code + run it + watch where it breaks) — for a broken publish script this usually means opening the real draft/editor page and looking at what actually happened, not guessing from the error text alone.
(2) Fix the code. If the root cause is a brittle DOM-coordinate/selector script that broke on a UI change, do NOT just re-tune coordinates: rebuild the failing step as two-layer agentic (a thin script opens the page, then YOU look at real screenshots and decide each click/type, looping until the real success signal appears).
(3) VERIFY with a REAL side-effect — re-run render-verify-draft.sh against the actual draft URL and see PASS, or otherwise directly observe the fixed behavior (a draft that now renders cleanly, a publish step that now returns a real URL). A patch that only compiles is NOT done. No dry runs, no fake success, no 'should work'.
(4) COMMIT IN THE CORRECT REPO: for EACH file you changed, cd into its directory, run 'git rev-parse --show-toplevel' and 'git remote -v' to confirm which repo it is, then commit+push THERE. Ground truth: this loop's own code (article-daily.sh, skills/writer-agent/) lives under the Mr.bot repository and its configured remote. Never commit runtime state, credentials, or anything under state/ or .env files.
(5) Write the outcome to ${RESULT} as a single line: 'SUCCESS <utc> <one-line real evidence, e.g. a render-verify PASS or a live draft URL>' or 'FAIL <utc> <why + what is still blocked>'. If the fix resolved a self-heal-request marker, rm it.
If after honest effort the fix is genuinely impossible (e.g. an external platform is down), write FAIL with a precise diagnosis to ${RESULT} — still never ask a human. Report what you fixed + the real evidence at the end."

TASK_FILE="$STATE/.self-fix-$LOOP.prompt"
printf '%s' "$TASK" >"$TASK_FILE"
chmod 600 "$TASK_FILE"
tmux -S "$SOCK" new-session -d -s "$SESSION" env \
  ARTICLE_RUN_ID="self-fix-$LOOP" ARTICLE_MODEL_LOG="$LOG" \
  "$MODEL_RUNNER" agent --prompt-file "$TASK_FILE"
date +%s >"$STARTMARK"
echo "$(date '+%F %T') self-fix[$LOOP] SPAWNED (provider-neutral): ${BLOCKER:0:90}" >>"$LOG"
echo "self-fix[$LOOP] spawned (provider-neutral, detached). result→$RESULT log→$LOG"
