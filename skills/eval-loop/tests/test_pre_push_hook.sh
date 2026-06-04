#!/usr/bin/env bash
# Verify the pre-push hook blocks slop and lets good outputs through.
#
# Strategy (codex P6 round 2 fix): the hook makes commits and would mutate
# the caller's branch — so run the entire test inside an ISOLATED git
# worktree under the repo's approved `.worktrees/` location (matches
# CLAUDE.md HARD RULE #0 worktree pattern). This means the user's main
# working tree is NEVER touched: no `git checkout main`, no `git branch -D`
# in the caller's index, no risk on a dirty worktree. After the test the
# worktree is removed completely.
#
# The hook's stdin contract is simulated directly (no actual push needed)
# by running .githooks/pre-push with hand-crafted ref lines spanning a
# single commit made INSIDE the worktree.
#
# BACKEND NOTE (2026-06-04): the hook hardcodes EVAL_MODE=production, which
# fail-closes (pass:false) on the heuristic when ALL judge backends are down.
# In that state the SLOP-blocks assertion is fully verified, but the
# GOOD-passes assertion requires a LIVE LLM judge (production must NOT pass
# heuristic — that's the contract). When every backend is out of credit we
# verify SLOP-blocks and emit a GOOD-passes SKIP (never a false PASS). Set
# EVAL_HOOK_LIVE=1 once a backend has credit to assert the GOOD-passes half.
set -uo pipefail
# REPO is the directory THIS test file lives in, walked up to the git toplevel,
# so the test works from either the worktree or the merged canonical checkout.
REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
HOOK="$REPO/.githooks/pre-push"
GOOD="$REPO/skills/eval-loop/tests/fixtures/good_output.txt"
SLOP="$REPO/skills/eval-loop/tests/fixtures/slop_output.txt"
GOOD_IN="$REPO/skills/eval-loop/tests/fixtures/good_input.txt"
SLOP_IN="$REPO/skills/eval-loop/tests/fixtures/slop_input.txt"

WT="$REPO/.worktrees/eval-loop-hook-test-$$"
BR="prepush-hook-test-$$"

cleanup() {
  # Always cleanup the worktree (no effect on caller's branch / index).
  if [ -d "$WT" ]; then
    git -C "$REPO" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
  fi
  git -C "$REPO" branch -D "$BR" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$REPO/.worktrees"
git -C "$REPO" worktree add -b "$BR" "$WT" HEAD >/dev/null
cd "$WT"

# Detect whether a live judge is reachable: a production-mode eval of the GOOD
# fixture returns backend != "heuristic" only when a real backend scored it.
LIVE_PROBE="$(EVAL_MODE=production "$REPO/skills/eval-loop/scripts/eval.sh" "$GOOD_IN" "$GOOD" "$REPO/skills/eval-loop/rubrics/post-to-x.rubric.json" 2>/dev/null || echo '{}')"
LIVE_BACKEND="$(echo "$LIVE_PROBE" | /usr/bin/jq -r '.backend // "heuristic"')"
if [ "${EVAL_HOOK_LIVE:-}" = "1" ] || [ "$LIVE_BACKEND" != "heuristic" ]; then
  GOOD_CASE_LIVE=1
else
  GOOD_CASE_LIVE=0
fi

# Slop case → expect hook exit 1
mkdir -p skills/_hook_test/eval-output
cp "$SLOP"    skills/_hook_test/eval-output/sample.txt
cp "$SLOP_IN" skills/_hook_test/eval-output/sample.input.txt
git add skills/_hook_test/
git -c user.email=test@anicca -c user.name=test commit -m "test(prepush): slop sample" >/dev/null

LOCAL_SHA=$(git rev-parse HEAD)
ZERO=0000000000000000000000000000000000000000
SLOP_LOG="$HOME/.hermes/state/.tmp-prepush_slop.$$.log"
RC=0
echo "refs/heads/$BR $LOCAL_SHA refs/heads/$BR $ZERO" | "$HOOK" >"$SLOP_LOG" 2>&1 || RC=$?
cat "$SLOP_LOG"; rm -f "$SLOP_LOG"
if [ "$RC" -eq 0 ]; then
  echo "FAIL: slop should have blocked push (exit 1) but hook returned 0"
  exit 1
fi
echo "SLOP BLOCKED OK (rc=$RC)"

# Good case → expect hook exit 0 (only assertable with a live judge)
cp "$GOOD"    skills/_hook_test/eval-output/sample.txt
cp "$GOOD_IN" skills/_hook_test/eval-output/sample.input.txt
git add skills/_hook_test/
git -c user.email=test@anicca -c user.name=test commit -m "test(prepush): good sample" >/dev/null

LOCAL_SHA=$(git rev-parse HEAD)
GOOD_LOG="$HOME/.hermes/state/.tmp-prepush_good.$$.log"
RC=0
echo "refs/heads/$BR $LOCAL_SHA refs/heads/$BR $ZERO" | "$HOOK" >"$GOOD_LOG" 2>&1 || RC=$?
cat "$GOOD_LOG"; rm -f "$GOOD_LOG"
if [ "$GOOD_CASE_LIVE" -eq 1 ]; then
  if [ "$RC" -ne 0 ]; then
    echo "FAIL: good output should have passed (exit 0) but hook returned $RC"
    exit 1
  fi
  echo "GOOD PASSED OK (rc=$RC)"
else
  # All backends down: production mode correctly fail-closes the good output
  # too (rc=1). Asserting "good passes" is impossible without a live judge, so
  # we verify the fail-closed behavior instead and SKIP the live half.
  if [ "$RC" -ne 1 ]; then
    echo "FAIL: backends-down good case expected fail-closed (exit 1), got $RC"
    exit 1
  fi
  echo "GOOD-PASSES SKIPPED (all backends down — production fail-closed rc=1 as designed; rerun with a funded backend or EVAL_HOOK_LIVE=1)"
fi

# Cleanup runs via trap (worktree removed, branch deleted) — no manual
# checkout / branch -D in the caller's main tree.
echo "PASS"
