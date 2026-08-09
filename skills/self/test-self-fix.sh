#!/usr/bin/env bash
# test-self-fix.sh — FIND-028/030/031: cover the mechanisms re-patched in rounds 4-6.
# (A) FIND-025 loop-name normalization  (B) FIND-029/030 hang fingerprint  (C) FIND-026/031 real lock acquire/steal.
set -uo pipefail; P=0; F=0; H="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; SF="$H/self-fix.sh"
a(){ echo "$2"|grep -qF "$3"&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }
eq(){ [ "$2" = "$3" ]&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 ($2 vs $3)"; F=$((F+1)); }; }
ne(){ [ "$2" != "$3" ]&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 (both $2)"; F=$((F+1)); }; }

echo "(A) loop-name normalization"
S="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy hint 2>&1)"; L="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy-loop hint 2>&1)"
a "short 'capafy' → LOOP=capafy-loop" "$S" 'LOOP=capafy-loop'
a "short → RESULT .self-fix-capafy-loop.result" "$S" '.self-fix-capafy-loop.result'
eq "short==long identical" "$S" "$L"
a "life-manager → life-manager-loop" "$(SELF_FIX_DRYRUN=1 bash "$SF" life-manager h 2>&1)" 'LOOP=life-manager-loop'

echo "(B) FIND-029/030 hang fingerprint — frozen pane (only timer/tokens advance) = SAME hash; real progress = DIFF"
BODY='⏺ Running browser step
  ⎿  page.waitForSelector(".save-btn")'
F1="$(printf '%s\n✢ Deploying… (3m 12s · ↓ 19.4k tokens · esc to interrupt)' "$BODY" | bash "$SF" --fingerprint)"
F2="$(printf '%s\n✢ Deploying… (58m 40s · ↓ 77.8k tokens · esc to interrupt)' "$BODY" | bash "$SF" --fingerprint)"
eq "frozen body, only timer/tokens changed → SAME fingerprint (hang detectable)" "$F1" "$F2"
F3="$(printf '⏺ NEW: found the bug, editing publish_finish.sh now\n✢ Deploying… (59m · esc to interrupt)' | bash "$SF" --fingerprint)"
ne "real new text → DIFFERENT fingerprint (progress)" "$F1" "$F3"

echo "(D) FIND-032 past-ceiling continue-vs-kill decision (sf_should_continue)"
dec(){ bash "$SF" --should-continue "$1" "$2" "$3" >/dev/null 2>&1 && echo CONTINUE || echo KILL; }
a "generating + fingerprint advanced → CONTINUE" "$(dec 1 hashA hashB)" 'CONTINUE'
a "generating + fingerprint FROZEN → KILL (hung)" "$(dec 1 hashA hashA)" 'KILL'
a "not generating (idle/errored) → KILL" "$(dec 0 hashA hashB)" 'KILL'
a "first check (prev=none) generating → CONTINUE" "$(dec 1 hashA none)" 'CONTINUE'

echo "(C) FIND-026/031 real lock acquire/steal via hc_acquire_lock"
source "$H/healthcheck-lib.sh"; now=$(date +%s)
D="$(mktemp -d)"; LK="$D/.lk"
hc_acquire_lock "$LK" "$now" && { echo "  ok acquire when no lock"; P=$((P+1)); } || { echo "  FAIL acquire when free"; F=$((F+1)); }
# now a FRESH lock exists (just made) → a second acquire must REFUSE
hc_acquire_lock "$LK" "$now" && { echo "  FAIL acquired a fresh held lock"; F=$((F+1)); } || { echo "  ok refuse fresh held lock"; P=$((P+1)); }
# simulate a hard-killed run: NON-EMPTY stale lock (owner file, old mtime) → must be STOLEN (FIND-026)
rm -rf "$LK"; mkdir "$LK"; echo 88 > "$LK/owner"; touch -t 202607010000 "$LK"
hc_acquire_lock "$LK" "$now" && { echo "  ok steal NON-EMPTY stale lock (rm -rf recovery)"; P=$((P+1)); } || { echo "  FAIL could not steal non-empty stale lock"; F=$((F+1)); }
rm -rf "$D"

echo "(E) A18 budget preflight — ANICCA_BUDGET_REQUIRED=1 without the scope/pass/daily trio must ABORT before spawn"
D2="$(mktemp -d)"
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 ANICCA_BUDGET_REQUIRED=1 ANICCA_BUDGET_SCOPE_ID= ANICCA_PASS_TOKEN_BUDGET= ANICCA_LOOP_DAILY_TOKEN_BUDGET= SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && { echo "  ok incomplete trio → nonzero exit ($rc)"; P=$((P+1)); } || { echo "  FAIL incomplete trio did not abort"; F=$((F+1)); }
a "abort message names the failure class" "$out" 'PREFLIGHT ABORT'
a "abort logged to the loop's self-fix log" "$(cat "$D2/.openclaw/logs/self-fix-gig-loop.log" 2>/dev/null)" 'PREFLIGHT ABORT'
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 ANICCA_BUDGET_REQUIRED=1 ANICCA_BUDGET_SCOPE_ID=selffix-test ANICCA_PASS_TOKEN_BUDGET=65536 ANICCA_LOOP_DAILY_TOKEN_BUDGET=262144 SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok complete trio → preflight passes"; P=$((P+1)); } || { echo "  FAIL complete trio aborted: $out"; F=$((F+1)); }
a "complete trio reaches the dryrun seam" "$out" 'LOOP=gig-loop'
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok REQUIRED unset → budget-less caller unaffected"; P=$((P+1)); } || { echo "  FAIL budget-less caller aborted: $out"; F=$((F+1)); }
rm -rf "$D2"

echo "(F) Capafy incident association — sidecar only; compatibility result marker remains untouched"
D3="$(mktemp -d)"; mkdir -p "$D3/.openclaw/state"
RESULT3="$D3/.openclaw/state/.self-fix-capafy-loop.result"
printf 'SUCCESS 2026-08-01T00:00:00Z existing evidence\n' > "$RESULT3"
before3="$(cat "$RESULT3")"
out="$(HOME="$D3" CAPAFY_INCIDENT_ID=capafy-builder-20260801T081400Z-a1b2c3d4 SELF_FIX_ASSOCIATE_ONLY=1 bash "$SF" capafy hint 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok incident association seam exits zero"; P=$((P+1)); } || { echo "  FAIL incident association seam rc=$rc: $out"; F=$((F+1)); }
SIDE3="$D3/.openclaw/state/.self-fix-capafy-loop.incident.json"
a "sidecar carries exact incident id" "$(cat "$SIDE3" 2>/dev/null)" '"incident_id":"capafy-builder-20260801T081400Z-a1b2c3d4"'
a "sidecar carries normalized loop" "$(cat "$SIDE3" 2>/dev/null)" '"loop":"capafy-loop"'
eq "existing one-line result marker unchanged" "$(cat "$RESULT3")" "$before3"
rm -rf "$D3"

echo "(G) D3 gig-loop worktree isolation — the fixer never edits the live tree the running loop executes from"
D4="$(mktemp -d)"
# Throwaway stand-ins for ~/anicca and ~/profitable-claude — SELF_FIX_ANICCA_REPO/SELF_FIX_GIG_REPO
# point self-fix.sh at these instead of the real mother repos, so the real repos stay untouched.
mkdir -p "$D4/anicca" "$D4/gig"
git -C "$D4/anicca" init -q -b live-main; git -C "$D4/anicca" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git -C "$D4/gig" init -q -b live-main; git -C "$D4/gig" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
# Real bare "origin" remotes so the finalize step's push is a genuine push, not a guaranteed no-op fail.
git init -q --bare "$D4/anicca-origin.git"; git -C "$D4/anicca" remote add origin "$D4/anicca-origin.git"; git -C "$D4/anicca" push -q origin live-main
git init -q --bare "$D4/gig-origin.git"; git -C "$D4/gig" remote add origin "$D4/gig-origin.git"; git -C "$D4/gig" push -q origin live-main
LIVE_ANICCA_HEAD="$(git -C "$D4/anicca" rev-parse HEAD)"; LIVE_GIG_HEAD="$(git -C "$D4/gig" rev-parse HEAD)"
HOME4="$D4/home"; mkdir -p "$HOME4"
SF_ENV=(HOME="$HOME4" SELF_FIX_ANICCA_REPO="$D4/anicca" SELF_FIX_GIG_REPO="$D4/gig" SELF_FIX_NO_ALERT=1 SELF_FIX_BACKOFF_MIN=0 SELF_FIX_SKIP_SPAWN=1)

out="$(env "${SF_ENV[@]}" bash "$SF" d3test "blocker text for the worktree isolation test" 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok setup run exits zero"; P=$((P+1)); } || { echo "  FAIL setup run rc=$rc: $out"; F=$((F+1)); }
ANICCA_WT="$(printf '%s' "$out" | sed -n 's/.*ANICCA_DIR=\([^ ]*\).*/\1/p')"
GIG_WT="$(printf '%s' "$out" | sed -n 's/.*GIG_DIR=\([^ ]*\).*/\1/p')"
PROMPT_FILE_OUT="$(printf '%s' "$out" | sed -n 's/.*PROMPT_FILE=\([^ ]*\).*/\1/p')"

[ -n "$ANICCA_WT" ] && [ -d "$ANICCA_WT" ] && { echo "  ok anicca worktree dir created"; P=$((P+1)); } || { echo "  FAIL anicca worktree dir missing: $ANICCA_WT"; F=$((F+1)); }
[ -n "$GIG_WT" ] && [ -d "$GIG_WT" ] && { echo "  ok gig worktree dir created"; P=$((P+1)); } || { echo "  FAIL gig worktree dir missing: $GIG_WT"; F=$((F+1)); }
case "$ANICCA_WT" in "$D4/anicca"/.worktrees/*) echo "  ok anicca worktree nested under live repo's .worktrees/"; P=$((P+1));; *) echo "  FAIL anicca worktree not under .worktrees/: $ANICCA_WT"; F=$((F+1));; esac
eq "live anicca repo HEAD untouched by worktree add" "$(git -C "$D4/anicca" rev-parse HEAD)" "$LIVE_ANICCA_HEAD"
eq "live gig repo HEAD untouched by worktree add" "$(git -C "$D4/gig" rev-parse HEAD)" "$LIVE_GIG_HEAD"
eq "live anicca repo never switched off its own branch" "$(git -C "$D4/anicca" rev-parse --abbrev-ref HEAD)" "live-main"
eq "live gig repo never switched off its own branch" "$(git -C "$D4/gig" rev-parse --abbrev-ref HEAD)" "live-main"
a "prompt points the fixer at the isolated anicca worktree" "$(cat "$PROMPT_FILE_OUT" 2>/dev/null)" "$ANICCA_WT"
a "prompt points the fixer at the isolated gig worktree" "$(cat "$PROMPT_FILE_OUT" 2>/dev/null)" "$GIG_WT"
a "prompt forbids editing the live checkout directly" "$(cat "$PROMPT_FILE_OUT" 2>/dev/null)" "never the live checkout"
WT_MARKER_OUT="$HOME4/.openclaw/state/.self-fix-d3test-loop.worktrees.env"
[ -f "$WT_MARKER_OUT" ] && { echo "  ok worktree marker persisted for later finalize"; P=$((P+1)); } || { echo "  FAIL worktree marker missing: $WT_MARKER_OUT"; F=$((F+1)); }

echo "  -- finalize SUCCESS: a commit made in the isolated worktree merges into the live branch, worktree is removed"
git -C "$ANICCA_WT" -c user.email=t@t -c user.name=t commit -q --allow-empty -m "self-fix test commit"
FIX_SHA="$(git -C "$ANICCA_WT" rev-parse HEAD)"
printf 'SUCCESS 2026-08-09T00:00:00Z test evidence\n' > "$HOME4/.openclaw/state/.self-fix-d3test-loop.result"
out2="$(env "${SF_ENV[@]}" bash "$SF" d3test "second call: finalize before deciding whether to respawn" 2>&1)"
a "second call's log records the merge" "$(cat "$HOME4/.openclaw/logs/self-fix-d3test-loop.log" 2>/dev/null)" "merged"
# --no-ff always makes a fresh merge commit SHA, so assert ancestry (the fix commit is IN the live
# branch's history now), not SHA equality.
git -C "$D4/anicca" merge-base --is-ancestor "$FIX_SHA" live-main \
  && { echo "  ok SUCCESS commit is an ancestor of the live anicca branch (merged in)"; P=$((P+1)); } \
  || { echo "  FAIL SUCCESS commit never landed on the live anicca branch"; F=$((F+1)); }
[ -d "$ANICCA_WT" ] && { echo "  FAIL worktree dir not removed after finalize"; F=$((F+1)); } || { echo "  ok worktree dir removed after finalize"; P=$((P+1)); }

echo "  -- finalize FAIL: worktree removed, branch kept for autopsy, live branch untouched"
ANICCA_WT2="$(printf '%s' "$out2" | sed -n 's/.*ANICCA_DIR=\([^ ]*\).*/\1/p')"
BRANCH2="$(printf '%s' "$out2" | sed -n 's/.*ANICCA_BRANCH=\([^ ]*\).*/\1/p')"
printf 'FAIL 2026-08-09T00:10:00Z could not reproduce\n' > "$HOME4/.openclaw/state/.self-fix-d3test-loop.result"
LIVE_HEAD_BEFORE_FAIL="$(git -C "$D4/anicca" rev-parse live-main)"
env "${SF_ENV[@]}" bash "$SF" d3test "third call: finalize the FAIL result" >/dev/null 2>&1
[ -n "$ANICCA_WT2" ] && [ -d "$ANICCA_WT2" ] && { echo "  FAIL FAIL-path worktree dir not removed"; F=$((F+1)); } || { echo "  ok FAIL-path worktree dir removed"; P=$((P+1)); }
git -C "$D4/anicca" rev-parse --verify "$BRANCH2" >/dev/null 2>&1 && { echo "  ok FAIL-path branch kept for autopsy"; P=$((P+1)); } || { echo "  FAIL FAIL-path branch was deleted"; F=$((F+1)); }
eq "FAIL path never merged into live branch" "$(git -C "$D4/anicca" rev-parse live-main)" "$LIVE_HEAD_BEFORE_FAIL"

echo "  -- fail-closed: worktree creation failure declines the run instead of falling back to the live tree"
out4="$(env HOME="$HOME4" SELF_FIX_ANICCA_REPO="$D4/does-not-exist" SELF_FIX_GIG_REPO="$D4/gig" SELF_FIX_NO_ALERT=1 SELF_FIX_BACKOFF_MIN=0 SELF_FIX_SKIP_SPAWN=1 bash "$SF" d3fail "blocker" 2>&1)"; rc4=$?
[ "$rc4" -ne 0 ] && { echo "  ok missing repo → nonzero exit (declined)"; P=$((P+1)); } || { echo "  FAIL missing repo did not decline: $out4"; F=$((F+1)); }
a "declined run records why in RESULT" "$(cat "$HOME4/.openclaw/state/.self-fix-d3fail-loop.result" 2>/dev/null)" "worktree setup failed"
a "declined run never claims SUCCESS" "$(cat "$HOME4/.openclaw/state/.self-fix-d3fail-loop.result" 2>/dev/null)" "FAIL"
rm -rf "$D4"

echo "=== self-fix: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
