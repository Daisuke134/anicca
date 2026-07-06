#!/bin/bash
# SessionStart hook: Display session context
echo "=== Anicca Session Started ==="
echo "Branch: $(git -C /Users/anicca/anicca-project branch --show-current 2>/dev/null || echo 'unknown')"
echo "Date: $(date '+%Y-%m-%d %H:%M JST')"
echo "Rules: $(ls /Users/anicca/anicca-project/.claude/rules/*.md 2>/dev/null | wc -l | tr -d ' ') files"

# --- DEV DISCIPLINE (surfaced every session so it is the DEFAULT, not a thing Dais must ask for) ---
echo ""
echo "=== DEV DISCIPLINE (act on it WITHOUT being told) ==="
echo "  1. WORKTREE-PER-TASK: 'git worktree add .worktrees/<task> -b feature/<task>' BEFORE touching code. Never share a branch/folder with another agent."
echo "  2. FULL VCSDD (no 50%): /vcsdd-init -> spec -> spec-review -> tdd(RED) -> impl(GREEN) -> adversary -> harden -> converge -> merge."
echo "  3. FINISH = merge to main, THEN 'git worktree remove <path>' + 'git branch -d <br>'. Accumulated worktrees = disk death."
for R in /Users/anicca/anicca /Users/anicca/anicca-project; do
  N=$(git -C "$R" worktree list 2>/dev/null | grep -c .)
  [ "${N:-0}" -ge 6 ] && echo "  WARN: $R has $N worktrees (>=6) -- clean up merged ones below"
done
echo "  Stale worktrees (branch already merged into main = SAFE TO DELETE now):"
found_stale=0
for R in /Users/anicca/anicca /Users/anicca/anicca-project; do
  git -C "$R" worktree list 2>/dev/null | awk 'NR>1{gsub(/[][]/,"",$NF); print $1" "$NF}' | while read -r WTP BR; do
    [ "$BR" = "main" ] && continue
    case "$BR" in *detached*|*HEAD*) continue;; esac
    # NEVER suggest deleting protected stores (browser history / agent memory / state) even if branch is merged
    case "$WTP" in *anicca-rtdash*|*anicca-monk-factory*|*.cloak*|*/memory*) continue;; esac
    if git -C "$R" merge-base --is-ancestor "$BR" main 2>/dev/null; then
      echo "    DEL: (cd $R && git worktree remove $WTP && git branch -d $BR)"
    fi
  done
done
