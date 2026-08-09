#!/usr/bin/env bash

RUN_AGENT="$HOME/anicca/skills/earn/marketing-engine/run_agent.sh"
if [ "${AGENT_WIRING_PROBE_ONLY:-0}" = "1" ]; then
  printf '{"task_class":"high-value-agent","runner":"%s"}\n' "$RUN_AGENT"
  exit 0
fi

# The browser is shared with the other money loops: heal it, restore the logins, collect stray tabs.
bash "$HOME/anicca/skills/browser/ensure_browser.sh" || echo "WARN: browser not recovered"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# self-fix.sh — TRUE autonomous self-heal launcher (no human, no "file issue and wait"). When a loop hits a
# code/automation blocker it cannot fix in-pass, it (or a healthcheck) calls this to spawn a detached, full-power
# high-value agent that diagnoses → edits the correct mother-repo code → VERIFIES by a REAL side-effect → commits+pushes
# → writes a result marker. That is how the loops self-improve their own code without babysitting.
# Usage: self-fix.sh <loop-name> "<blocker + concrete fix hint>"
set -uo pipefail
# FIND-029: fingerprint the SUBSTANTIVE pane content only — strip the CLI's ever-changing status line (elapsed
# timer, token counter, spinner glyphs, "esc to interrupt") so a genuinely FROZEN (deadlocked) fixer produces the
# SAME fingerprint across checks (its reasoning/tool text is unchanged; only the timer ticks), while real progress
# (new text) changes it. Without this strip, the incrementing timer made every check look like "progress".
sf_pane_fingerprint(){ printf '%s' "$1" | tail -25 \
  | sed -E 's/[0-9]+//g; s/esc to interrupt//g' \
  | tr -d '✻✳✶✢⏺◐◓◑◒·↑↓…' \
  | grep -avE 'tokens' \
  | cksum | awk '{print $1"-"$2}'; }
if [ "${1:-}" = "--fingerprint" ]; then sf_pane_fingerprint "$(cat)"; exit 0; fi
# FIND-032: the past-ceiling continue-vs-kill decision as a PURE, testable predicate. Returns 0 (=let the fixer
# CONTINUE) ONLY when it is still generating AND its fingerprint advanced since the last check; otherwise 1 (=KILL:
# frozen/hung, or not generating = idle/errored). args: <generating 0|1> <cur_fp> <prev_fp>.
sf_should_continue(){ [ "$1" = "1" ] && [ "$2" != "$3" ]; }
if [ "${1:-}" = "--should-continue" ]; then sf_should_continue "${2:-}" "${3:-}" "${4:-}"; exit $?; fi
# FIND-025: NORMALIZE the loop name to a single canonical form ("<x>-loop") so every call site — healthcheck
# (HC_LOOP=capafy-loop), STARTUP prompts (capafy), verify-loops (capafy) — maps to ONE session name + ONE result
# marker. Without this, "capafy" and "capafy-loop" spawn two mutually-unaware fixers and split the marker the
# anti-fake verifier reads. Idempotent: strip a trailing -loop then re-add it.
LOOP="${1:?loop name}"; LOOP="${LOOP%-loop}-loop"; BLOCKER="${2:?blocker+hint}"
SOCK="/tmp/anicca-selffix-$LOOP-tmux.sock"; SESSION="anicca-selffix-$LOOP"
STATE="$HOME/.openclaw/state"; mkdir -p "$STATE"
LOG="$HOME/.openclaw/logs/self-fix-$LOOP.log"; mkdir -p "$(dirname "$LOG")"
RESULT="$STATE/.self-fix-$LOOP.result"       # the fixer writes SUCCESS/FAIL + evidence here (FIND-003)
STARTMARK="$STATE/.self-fix-$LOOP.started"    # epoch when the current fixer was spawned (FIND-005 stale-guard)
INCIDENT_SIDECAR="$STATE/.self-fix-$LOOP.incident.json"
sf_write_incident_association(){
  local incident_id="${CAPAFY_INCIDENT_ID:-}" tmp
  [ -n "$incident_id" ] || return 0
  case "$incident_id" in *[!A-Za-z0-9._:-]*) echo "invalid CAPAFY_INCIDENT_ID" >&2; return 2 ;; esac
  tmp="$INCIDENT_SIDECAR.tmp"
  printf '{"schema_version":1,"incident_id":"%s","loop":"%s","result_path":"%s"}\n' \
    "$incident_id" "$LOOP" "$RESULT" > "$tmp"
  mv "$tmp" "$INCIDENT_SIDECAR"
}
# D3 (gig-loop spec §CC'/§EW', 2026-08-09): the fixer this script spawns used to be told to
# "cd into" whichever mother repo a file lives in and commit+push directly there — the SAME
# checkout a running loop (e.g. gig-pass reads ~/profitable-claude/skills/gig-work live every
# 30min) is executing from right now. A fixer editing/checking-out-branches in that live tree
# can corrupt an in-flight pass. Isolate every repo the fixer may touch in a throwaway worktree
# on its own branch BEFORE the agent starts; ~/.openclaw is the one exception (HARD RULE 0.40 —
# the gateway reads a single checkout path, `git worktree` is forbidden there), so it stays
# direct-edit exactly as before. Test seam: SELF_FIX_ANICCA_REPO / SELF_FIX_GIG_REPO point this
# at throwaway repos in tests instead of the real mother repos.
ANICCA_REPO="${SELF_FIX_ANICCA_REPO:-$HOME/anicca}"
GIG_REPO="${SELF_FIX_GIG_REPO:-$HOME/profitable-claude}"
WT_MARKER="$STATE/.self-fix-$LOOP.worktrees.env"
sf_wt_dir(){ printf '%s/.worktrees/selffix-%s-%s' "$1" "$2" "$3"; }      # repo loop ts
sf_wt_branch(){ printf 'selffix/%s-%s' "$1" "$2"; }                        # loop ts
# Create the worktree+branch off the repo's CURRENT branch; never touches the live checkout
# itself (worktree add does not move HEAD in the source repo). Prints the base branch name on
# stdout so the caller can merge back into the same branch later; rc!=0 = fail closed.
sf_wt_setup(){ # repo dir branch
  local repo="$1" dir="$2" branch="$3" base
  base="$(git -C "$repo" rev-parse --abbrev-ref HEAD 2>/dev/null)" || return 1
  [ -n "$base" ] && [ "$base" != "HEAD" ] || return 1
  git -C "$repo" worktree add -b "$branch" "$dir" "$base" >/dev/null 2>&1 || return 1
  git -C "$dir" push -u origin "$branch" >/dev/null 2>&1 || true  # best-effort upstream so the fixer's own `git push` works
  printf '%s' "$base"
}
# Merge the isolated branch back into the live tree via the SAME manual path (checkout base,
# merge --no-ff, push) used all day, THEN remove the worktree — success only. Any other outcome
# (FAIL, still-RUNNING/abandoned, or a merge/push failure) removes the worktree but keeps the
# branch for autopsy, and never touches the live tree's checked-out branch.
sf_wt_finalize(){ # repo dir branch base outcome log
  local repo="$1" dir="$2" branch="$3" base="$4" outcome="$5" log="$6"
  git -C "$repo" worktree remove --force "$dir" >/dev/null 2>&1 || git -C "$repo" worktree prune >/dev/null 2>&1
  if [ "$outcome" = "SUCCESS" ]; then
    if git -C "$repo" checkout "$base" >/dev/null 2>&1 \
      && git -C "$repo" merge --no-ff "$branch" -m "merge: self-fix/$branch" >/dev/null 2>&1 \
      && git -C "$repo" push origin "$base" >/dev/null 2>&1; then
      git -C "$repo" branch -d "$branch" >/dev/null 2>&1 || true
      echo "$(date '+%F %T') self-fix worktree finalize: merged $branch -> $base in $repo" >> "$log"
    else
      echo "$(date '+%F %T') self-fix worktree finalize: SUCCESS but merge/push of $branch -> $base FAILED in $repo — branch kept for autopsy" >> "$log"
    fi
  else
    echo "$(date '+%F %T') self-fix worktree finalize: outcome=$outcome — $branch kept for autopsy in $repo, not merged" >> "$log"
  fi
}
# Read a previously written WT_MARKER (key=%q-quoted values, sourced) and finalize both repos'
# worktrees against the current $RESULT content, then remove the marker so this runs exactly
# once per spawn. No-op if no marker exists (nothing to finalize).
sf_wt_finalize_marker(){ # marker_path result_path log
  local marker="$1" result="$2" log="$3" outcome=FAIL
  [ -f "$marker" ] || return 0
  # shellcheck disable=SC1090
  . "$marker"
  head -c 7 "$result" 2>/dev/null | grep -q '^SUCCESS' && outcome=SUCCESS
  [ -n "${ANICCA_DIR:-}" ] && sf_wt_finalize "$ANICCA_REPO" "$ANICCA_DIR" "$ANICCA_BRANCH" "$ANICCA_BASE" "$outcome" "$log"
  [ -n "${GIG_DIR:-}" ] && sf_wt_finalize "$GIG_REPO" "$GIG_DIR" "$GIG_BRANCH" "$GIG_BASE" "$outcome" "$log"
  rm -f "$marker"
}
# A18 PREFLIGHT (2026-08-01, gig 4-day silent outage 07-28→08-01): agent_runner is fail-closed on
# token budgets — if the caller's env carries ANICCA_BUDGET_REQUIRED=1 without the FULL
# scope/pass/daily trio, the spawned runner aborts at startup, AFTER this script already logged
# SPAWNED and wrote RUNNING to the result marker, and the abort is visible only in a log nobody
# tails. Failure class: "budget config incomplete → repair chain dies silently". Detect it BEFORE
# paying for any spawn side-effect and page it as an incident. Test seam: SELF_FIX_NO_ALERT=1.
if [ "${ANICCA_BUDGET_REQUIRED:-}" = "1" ] && { [ -z "${ANICCA_BUDGET_SCOPE_ID:-}" ] || [ -z "${ANICCA_PASS_TOKEN_BUDGET:-}" ] || [ -z "${ANICCA_LOOP_DAILY_TOKEN_BUDGET:-}" ]; }; then
  PF_MSG="self-fix[$LOOP] PREFLIGHT ABORT: ANICCA_BUDGET_REQUIRED=1 but token budget env is incomplete (scope='${ANICCA_BUDGET_SCOPE_ID:-}' pass='${ANICCA_PASS_TOKEN_BUDGET:-}' daily='${ANICCA_LOOP_DAILY_TOKEN_BUDGET:-}') — caller must export all three or the agent-runner spawn aborts silently (A18 class, self-heal chain dead)"
  echo "$(date '+%F %T') $PF_MSG" >> "$LOG"
  if [ "${SELF_FIX_NO_ALERT:-0}" != "1" ]; then
    openclaw message send --channel telegram --target 8547730585 -m "🚨 $PF_MSG" --json >/dev/null 2>&1 || true
  fi
  echo "$PF_MSG" >&2
  exit 2
fi
# FIND-028 test seam: print the normalized identity + derived paths and exit BEFORE any tmux/side-effect.
if [ "${SELF_FIX_DRYRUN:-}" = "1" ]; then printf 'LOOP=%s SESSION=%s SOCK=%s RESULT=%s\n' "$LOOP" "$SESSION" "$SOCK" "$RESULT"; exit 0; fi
if [ "${SELF_FIX_ASSOCIATE_ONLY:-0}" = "1" ]; then
  sf_write_incident_association || exit $?
  printf 'INCIDENT_SIDECAR=%s\n' "$INCIDENT_SIDECAR"
  exit 0
fi
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
  # FIND-023/027: past the ceiling, distinguish REAL PROGRESS from a HUNG tool. "esc to interrupt" alone is not enough
  # (a hung curl/waitForSelector shows the same spinner forever), so we compare the pane CONTENT between successive
  # past-ceiling checks: if the pane still shows generation AND its content ADVANCED since the last check → real
  # progress, continue; if it is frozen (unchanged) or not generating at all → genuinely hung/idle → kill+respawn.
  PANEHASH="$STATE/.self-fix-$LOOP.panehash"
  _pane="$(tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null)"
  cur="$(sf_pane_fingerprint "$_pane")"   # FIND-029: volatile timer/token/spinner stripped → frozen pane = same hash
  prev="$(cat "$PANEHASH" 2>/dev/null||echo none)"; printf '%s' "$cur" > "$PANEHASH"
  generating=0; printf '%s' "$_pane" | tail -6 | grep -qE 'esc to interrupt' && generating=1
  if sf_should_continue "$generating" "$cur" "$prev"; then
    echo "$(date '+%F %T') self-fix[$LOOP] ${age_min}min, generating + pane ADVANCED → real progress, continue" >> "$LOG"; echo "self-fix[$LOOP] still progressing (${age_min}min)"; exit 0
  fi
  echo "$(date '+%F %T') self-fix[$LOOP] ${age_min}min, pane frozen/idle (prev=$prev cur=$cur) → hung → kill+respawn" >> "$LOG"; rm -f "$PANEHASH"
  tmux -S "$SOCK" kill-session -t "$SESSION" 2>/dev/null||true; sleep 1
fi

# D3: the moment no fixer session is running (it exited on its own, or was just killed above as
# hung), finalize whatever worktree(s) the LAST spawn set up: merge on SUCCESS, else remove the
# worktree and keep the branch for autopsy. Runs before the backoff check below so a fresh
# worktree pair (further down) is only ever created after the previous pair is fully retired —
# never two live worktree sets for the same loop at once.
if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then
  sf_wt_finalize_marker "$WT_MARKER" "$RESULT" "$LOG"
fi

# FIND-035 (A6, 2026-07-18): RESULT-MARKER BACKOFF. The has-session guard above only prevents a
# CONCURRENT second fixer — it does NOT stop the every-6h auditor from re-spawning a FRESH high-value
# agent each cycle when the underlying condition PERSISTS but is NOT a code bug: e.g. published.jsonl
# is legitimately stale >30h because inventory is drained (nothing to publish), or a prior fixer
# already concluded this is a genuine external blocker. Without backoff this burned one Sonnet every
# 6h forever for a non-bug (the "verify-loops-audit reflex-spawns self-fix" landmine, capafy 2026-07).
# If the PRIOR fixer for THIS loop already CONCLUDED (RESULT no longer 'RUNNING') within BACKOFF_MIN,
# skip — the condition was addressed (SUCCESS) or is a known standing blocker (FAIL); retry only after
# the backoff so a real regression is still eventually re-attempted. Test seam: SELF_FIX_BACKOFF_MIN.
BACKOFF_MIN="${SELF_FIX_BACKOFF_MIN:-1200}"   # 20h → at most ~1 fixer/day/loop instead of 4
if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && [ -f "$RESULT" ] && ! grep -q '^RUNNING' "$RESULT" 2>/dev/null; then
  res_age_min=$(( ( $(date +%s) - $(stat -f %m "$RESULT" 2>/dev/null||echo 0) ) / 60 ))
  if [ "$res_age_min" -ge 0 ] && [ "$res_age_min" -lt "$BACKOFF_MIN" ]; then
    echo "$(date '+%F %T') self-fix[$LOOP] prior fixer concluded ${res_age_min}min ago (<${BACKOFF_MIN} backoff) → skip re-spawn [$(head -c 70 "$RESULT" | tr -d '\n')]" >> "$LOG"
    echo "self-fix[$LOOP] backoff — prior result ${res_age_min}min ago (<${BACKOFF_MIN}min)"; exit 0
  fi
fi

# FIND-033 (life-manager-loop 3-day outage, 2026-07-10): a near-full disk stops swap from growing, which
# surfaces as fork() failures for every fresh spawn — including this fixer's own tmux/claude spawn below.
# Without this, self-fix keeps respawning fixers that die before they can even diagnose anything (observed:
# 40+ spawns over 24h, none completed). Reclaim only 100%-regenerable package-manager caches; see
# hc_reclaim_disk_if_low in healthcheck-lib.sh for the full rationale and the excluded (approval-needed) paths.
# shellcheck source=healthcheck-lib.sh
. "$HOME/anicca/skills/self/healthcheck-lib.sh" 2>/dev/null && hc_reclaim_disk_if_low

# D3: isolate every repo the fixer may touch (except ~/.openclaw, worktree-forbidden by HARD
# RULE 0.40) in a fresh worktree BEFORE the agent starts. Fail closed: if either worktree cannot
# be created, decline to spawn — never fall back to letting the fixer edit the live checkout.
WT_TS="$(date +%s)-$$"  # pid-suffixed: two setups in the same wall-clock second must not collide on dir/branch name
ANICCA_WT_DIR="$(sf_wt_dir "$ANICCA_REPO" "$LOOP" "$WT_TS")"
GIG_WT_DIR="$(sf_wt_dir "$GIG_REPO" "$LOOP" "$WT_TS")"
ANICCA_WT_BRANCH="$(sf_wt_branch "$LOOP" "$WT_TS")"
GIG_WT_BRANCH="$(sf_wt_branch "gig-$LOOP" "$WT_TS")"
if ! ANICCA_BASE="$(sf_wt_setup "$ANICCA_REPO" "$ANICCA_WT_DIR" "$ANICCA_WT_BRANCH")"; then
  WT_MSG="self-fix[$LOOP] DECLINED: could not create isolated worktree for $ANICCA_REPO ($ANICCA_WT_DIR) — refusing to fall back to editing the live tree"
  echo "$(date '+%F %T') $WT_MSG" >> "$LOG"; echo "$WT_MSG" >&2; printf 'FAIL %s worktree setup failed: %s\n' "$(date -u +%FT%TZ)" "$ANICCA_REPO" > "$RESULT"; exit 2
fi
if ! GIG_BASE="$(sf_wt_setup "$GIG_REPO" "$GIG_WT_DIR" "$GIG_WT_BRANCH")"; then
  git -C "$ANICCA_REPO" worktree remove --force "$ANICCA_WT_DIR" >/dev/null 2>&1 || true
  git -C "$ANICCA_REPO" branch -D "$ANICCA_WT_BRANCH" >/dev/null 2>&1 || true
  WT_MSG="self-fix[$LOOP] DECLINED: could not create isolated worktree for $GIG_REPO ($GIG_WT_DIR) — refusing to fall back to editing the live tree"
  echo "$(date '+%F %T') $WT_MSG" >> "$LOG"; echo "$WT_MSG" >&2; printf 'FAIL %s worktree setup failed: %s\n' "$(date -u +%FT%TZ)" "$GIG_REPO" > "$RESULT"; exit 2
fi
{
  printf 'ANICCA_REPO=%q\n' "$ANICCA_REPO"
  printf 'ANICCA_DIR=%q\n' "$ANICCA_WT_DIR"
  printf 'ANICCA_BRANCH=%q\n' "$ANICCA_WT_BRANCH"
  printf 'ANICCA_BASE=%q\n' "$ANICCA_BASE"
  printf 'GIG_REPO=%q\n' "$GIG_REPO"
  printf 'GIG_DIR=%q\n' "$GIG_WT_DIR"
  printf 'GIG_BRANCH=%q\n' "$GIG_WT_BRANCH"
  printf 'GIG_BASE=%q\n' "$GIG_BASE"
} > "$WT_MARKER"
echo "$(date '+%F %T') self-fix[$LOOP] worktrees ready: anicca=$ANICCA_WT_DIR($ANICCA_WT_BRANCH off $ANICCA_BASE) gig=$GIG_WT_DIR($GIG_WT_BRANCH off $GIG_BASE)" >> "$LOG"

# FIND-003/004: the fixer MUST verify a real side-effect, commit in the CORRECT repo (the one the edited file lives
# in — discovered via git rev-parse, NOT guessed), and write a result marker the caller/healthcheck can check.
printf 'RUNNING %s\n' "$(date -u +%FT%TZ)" > "$RESULT"
sf_write_incident_association || exit $?
TASK="AUTONOMOUS SELF-FIX for the ${LOOP} loop. You are a high-value autonomous dev with browser (CloakBrowser daily-driver CDP :9222), Bash, Edit. NEVER ask a human and NEVER present a menu — a blocker is not stop. BLOCKER + HINT: ${BLOCKER}.
DO, in order:
(0) CHECK FOR PRIOR DIAGNOSIS FIRST (2026-07-13 fix — a prior self-fix spawn burned 400-1400min re-discovering an already-known external blocker from scratch): before any expensive live reproduction, search for an existing diagnosis of THIS exact blocker — tail the loop's own lessons/audit files under its state dir (e.g. ~/gig/lessons.jsonl, ~/gig/audit.jsonl) for recent matching entries, and run 'gh issue list -R Daisuke134/anicca --label gig-lesson --search \"<keyword from the blocker>\"' to find prior write-ups. If a recent (last ~24h) prior diagnosis already concluded this is a genuine external/physical blocker (e.g. a real-world device state, a third-party account lock needing a human's physical action, an outage) — do ONE cheap, fast confirmation that the same condition still holds (a single live check, not a repeat of the full multi-hour investigation), then write FAIL citing the existing issue/lesson instead of re-running the whole diagnosis. Only do a full fresh investigation when no matching prior diagnosis exists or the prior one looks stale/resolved.
(1) Reproduce the failure yourself and find the ROOT cause (read the actual code + run it + watch where it breaks).
(2) Fix the code. If the root cause is a brittle DOM-coordinate/selector script that broke on a UI change, do NOT just re-tune coordinates: rebuild the failing step as two-layer agentic (a thin script opens the page, then YOU look at real screenshots and decide each click/type, looping until the real success signal appears).
(3) VERIFY with a REAL side-effect — an actually-published skill URL you then curl and see live / a real posted comment URL / the tool actually succeeding once end-to-end. A patch that only compiles is NOT done. No dry runs, no fake success, no 'should work'.
(4) COMMIT IN THE CORRECT REPO, INSIDE YOUR ISOLATED WORKTREE (never the live checkout): the running loops read the LIVE ~/anicca and ~/profitable-claude directories directly (e.g. gig-pass executes ~/profitable-claude/skills/gig-work/gig_pass.sh every 30min) — editing or branch-switching those live paths WILL corrupt an in-flight pass. Your isolated workspace for ~/anicca is ${ANICCA_WT_DIR} (branch ${ANICCA_WT_BRANCH}, off ${ANICCA_BASE}); for ~/profitable-claude it is ${GIG_WT_DIR} (branch ${GIG_WT_BRANCH}, off ${GIG_BASE}). For EACH file you changed, run 'git rev-parse --show-toplevel' to confirm which of the two roots it belongs to, cd into the MATCHING isolated worktree above (never ~/anicca or ~/profitable-claude directly), then commit+push from there (upstream is already set — plain 'git push' works). The ONLY exception is ~/.openclaw (remote = anicca-dais, PRIVATE): git worktree is forbidden there (HARD RULE 0.40, the gateway reads a single checkout path) — edit, commit, and push ~/.openclaw directly as before. Never commit ~/.openclaw runtime state or secrets.
(5) Write the outcome to ${RESULT} as a single line: 'SUCCESS <utc> <one-line real evidence, e.g. published URL>' or 'FAIL <utc> <why + what is still blocked>'. If the fix resolved a selfheal-request json, rm it.
If after honest effort the fix is genuinely impossible (e.g. an external service is down), write FAIL with a precise diagnosis to ${RESULT} and invoke self/issue-dev — still never ask a human. Report what you fixed + the real evidence at the end."
if [ -n "${CAPAFY_INCIDENT_ID:-}" ]; then
  TASK="${TASK} This repair belongs to incident ${CAPAFY_INCIDENT_ID}. Preserve that exact incident id in all evidence and final reporting."
fi
TASK="${TASK} 重要な結果（数字・IDを含む成果、realized P&L、致命的エラー）が出たら PushNotification ツールで Dais へ verbatim 送信してから終了する。narration・定常報告には使わない。"
PROMPT_FILE="$STATE/.self-fix-$LOOP.prompt"
EVIDENCE_DIR="$STATE/agent-runner-evidence/self-fix-$LOOP/$(date +%s)-$$"
printf '%s\n' "$TASK" > "$PROMPT_FILE"

# D3 test seam: worktrees are already created and the prompt already written above (the real
# side-effects under test) — stop here, before the tmux/agent spawn, so characterization tests
# never pay for a real agent turn.
if [ "${SELF_FIX_SKIP_SPAWN:-0}" = "1" ]; then
  printf 'ANICCA_DIR=%s ANICCA_BRANCH=%s GIG_DIR=%s GIG_BRANCH=%s PROMPT_FILE=%s WT_MARKER=%s\n' \
    "$ANICCA_WT_DIR" "$ANICCA_WT_BRANCH" "$GIG_WT_DIR" "$GIG_WT_BRANCH" "$PROMPT_FILE" "$WT_MARKER"
  exit 0
fi

# Keep the historical detached tmux lifecycle, but delegate provider/model selection to the
# shared task-class runner. Shell-escape every interpolated value before tmux evaluates the command.
printf -v RUN_AGENT_Q '%q' "$RUN_AGENT"
printf -v EVIDENCE_DIR_Q '%q' "$EVIDENCE_DIR"
printf -v TASK_LABEL_Q '%q' "self-fix-$LOOP"
printf -v LOOP_Q '%q' "$LOOP"
printf -v PROMPT_FILE_Q '%q' "$PROMPT_FILE"
printf -v LOG_Q '%q' "$LOG"
tmux -S "$SOCK" new-session -d -s "$SESSION" \
  "exec /bin/bash $RUN_AGENT_Q --task-class high-value-agent --evidence-dir $EVIDENCE_DIR_Q --task-label $TASK_LABEL_Q --loop $LOOP_Q < $PROMPT_FILE_Q >> $LOG_Q 2>&1"
date +%s > "$STARTMARK"
echo "$(date '+%F %T') self-fix[$LOOP] SPAWNED (high-value-agent): ${BLOCKER:0:90}" >> "$LOG"
echo "self-fix[$LOOP] spawned (high-value-agent, detached). result→$RESULT log→$LOG evidence→$EVIDENCE_DIR"
