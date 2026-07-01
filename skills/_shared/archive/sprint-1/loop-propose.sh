#!/usr/bin/env bash
# loop-propose.sh — STEP 5 SELF-PROPOSE: scan gh issues for earning-skill-proposal,
# sandbox-eval, promote if ROI clears bar.
#
# Sprint-1 scaffold; sprint-2 wires git clone into .worktrees/sandbox-<sha>/ + 3-day
# adversary review window.
#
# Usage: loop-propose.sh
set -uo pipefail
gh issue list --label "earning-skill-proposal" --limit 10 \
   --json number,title,body 2>/dev/null || echo "[]"
echo "loop-propose: scaffold (sprint-2: clone candidate skills into .worktrees/sandbox/)"
