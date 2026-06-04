#!/usr/bin/env bash
# attempt-fix: symphony-style autonomous fix for one filed issue.
#   1. Parse affected skill from the issue body.
#   2. Isolate a worktree off main under ~/.cache/anicca-clones (NEVER /tmp).
#   3. Read the offending skill's primary script.
#   4. Ask `hermes chat` to improve it to fix the issue.
#   5. Apply edit → run skill tests if present → eval-loop on a sample output.
#   6. If eval >= 0.7 AND tests pass → commit + `gh pr create` referencing the issue.
#   7. Else → `gh issue comment` with verbatim error + remove fix worktree (no PR).
#
# Usage: attempt-fix.sh <issue_number>
# Env:
#   DRY_RUN=1     print intended actions, no worktree/gh writes, no hermes call.
#   REPO_ROOT     anicca-oss repo root (default: resolved from this script).
#   GH_TOKEN      inherited by gh (never echoed).
set -uo pipefail

ISSUE="${1:-}"
[ -z "$ISSUE" ] && { echo "usage: attempt-fix.sh <issue_number>" >&2; exit 2; }

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SKILL_DIR/../.." && pwd)}"
REPO="${SELF_IMPROVE_REPO:-Daisuke134/anicca-oss}"
EVAL_LOOP="$REPO_ROOT/skills/eval-loop"
CLONE_BASE="${CLONE_BASE:-/Users/operator/.cache/anicca-clones}"
JQ=/usr/bin/jq

# ---- North Star guard: constitution is immutable, never auto-edited ----
guard_immutable() {
  case "$1" in
    *CONSTITUTION*|*constitution-guard*|*"North Star"*)
      return 0 ;;  # immutable
    *) return 1 ;;
  esac
}

# ---- fetch issue body + parse affected skill ----
body="$(gh issue view "$ISSUE" --repo "$REPO" --json body -q '.body' 2>/dev/null)" || {
  echo "could not fetch issue #$ISSUE" >&2; exit 1;
}
skill="$(printf '%s\n' "$body" | sed -n 's/.*\*\*Affected skill:\*\* *//p' | head -1 | tr -d '\r')"
[ -z "$skill" ] && skill="unknown"
echo "issue #$ISSUE → affected skill: $skill" >&2

if guard_immutable "$skill"; then
  echo "affected skill '$skill' is IMMUTABLE (North Star / constitution) — skipping auto-fix" >&2
  if [ "${DRY_RUN:-}" != "1" ]; then
    gh issue comment "$ISSUE" --repo "$REPO" \
      --body "self-improve: affected target is immutable (North Star / Law I / constitution). Auto-fix skipped; this requires human review." >/dev/null 2>&1 || true
  fi
  exit 0
fi

SKILL_PATH="$REPO_ROOT/skills/$skill"
if [ ! -d "$SKILL_PATH" ]; then
  echo "skill dir not found: $SKILL_PATH — cannot auto-fix" >&2
  [ "${DRY_RUN:-}" != "1" ] && gh issue comment "$ISSUE" --repo "$REPO" \
    --body "self-improve: could not locate skill '$skill' in skills/. Manual triage needed." >/dev/null 2>&1 || true
  exit 0
fi

# primary script = first .sh or .py under scripts/
TARGET="$(find "$SKILL_PATH/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) 2>/dev/null | sort | head -1)"
[ -z "$TARGET" ] && { echo "no script found under $SKILL_PATH/scripts" >&2; exit 0; }
echo "target file: $TARGET" >&2

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "DRY_RUN: would isolate worktree, ask hermes to improve $TARGET, eval-gate, then PR for issue #$ISSUE"
  exit 0
fi

# ---- isolate a worktree off main (NOT /tmp) ----
mkdir -p "$CLONE_BASE"
WT="$CLONE_BASE/self-improve-fix-$ISSUE"
BR="self-improve/fix-$ISSUE"
git -C "$REPO_ROOT" worktree remove --force "$WT" 2>/dev/null || true
git -C "$REPO_ROOT" branch -D "$BR" 2>/dev/null || true
if ! git -C "$REPO_ROOT" worktree add "$WT" -b "$BR" main >/dev/null 2>&1; then
  echo "worktree add failed" >&2
  gh issue comment "$ISSUE" --repo "$REPO" --body "self-improve: could not create isolated worktree. Manual triage needed." >/dev/null 2>&1 || true
  exit 1
fi

REL="${TARGET#$REPO_ROOT/}"
WT_TARGET="$WT/$REL"
cleanup() { git -C "$REPO_ROOT" worktree remove --force "$WT" 2>/dev/null || true; }

# ---- ask hermes to improve the file ----
orig="$(cat "$WT_TARGET")"
prompt="Improve this code to fix the issue described below. Return ONLY the full revised file contents, no markdown fences, no commentary.

ISSUE #$ISSUE: $(printf '%s' "$body" | head -c 1200)

CURRENT FILE ($REL):
$orig"

edit="$(hermes chat -Q -q "$prompt" 2>/dev/null)" || edit=""
# strip accidental markdown fences if the model added them
edit="$(printf '%s\n' "$edit" | sed -e '/^```/d')"

if [ -z "$edit" ] || [ "$edit" = "$orig" ]; then
  echo "hermes produced no usable edit" >&2
  gh issue comment "$ISSUE" --repo "$REPO" --body "self-improve: the model produced no usable edit for \`$REL\`. Manual triage needed." >/dev/null 2>&1 || true
  cleanup; exit 0
fi
printf '%s\n' "$edit" > "$WT_TARGET"

# ---- run skill tests if present ----
test_log="/Users/operator/.hermes/state/.tmp-fix-tests-$ISSUE.$$"
tests_ok=true
if ls "$WT/skills/$skill/tests/"*.sh >/dev/null 2>&1; then
  for t in "$WT/skills/$skill/tests/"*.sh; do
    if ! bash "$t" >"$test_log" 2>&1; then tests_ok=false; break; fi
  done
fi

# ---- eval-loop gate on the improved file as the "output" ----
eval_in="/Users/operator/.hermes/state/.tmp-fix-in-$ISSUE.$$"
printf 'Improve skills/%s to resolve issue #%s.\n' "$skill" "$ISSUE" > "$eval_in"
eval_json="$("$EVAL_LOOP/scripts/eval.sh" "$eval_in" "$WT_TARGET" 2>/dev/null)" || eval_json='{"pass":false,"total":0}'
eval_pass="$(printf '%s' "$eval_json" | "$JQ" -r '.pass // false' 2>/dev/null)"
eval_total="$(printf '%s' "$eval_json" | "$JQ" -r '.total // 0' 2>/dev/null)"
rm -f "$eval_in"

echo "tests_ok=$tests_ok eval_pass=$eval_pass eval_total=$eval_total" >&2

if [ "$tests_ok" = "true" ] && [ "$eval_pass" = "true" ]; then
  git -C "$WT" add -A
  git -C "$WT" commit -m "fix(self-improve): #$ISSUE — autonomous fix for $skill (eval $eval_total)" >/dev/null 2>&1
  git -C "$WT" push -u origin "$BR" >/dev/null 2>&1 || true
  pr_url="$(gh pr create --repo "$REPO" --head "$BR" --base main \
    --title "fix(self-improve): #$ISSUE $skill" \
    --body "Autonomous fix by skills/self-improve. eval total=$eval_total, tests passed. Closes #$ISSUE." 2>/dev/null)" || pr_url=""
  echo "$pr_url"
  rm -f "$test_log"
  # leave worktree for human inspection of PR; caller's share-learning runs next
  exit 0
else
  errsnip="$( [ -r "$test_log" ] && tail -20 "$test_log" || echo "(no test output)" )"
  gh issue comment "$ISSUE" --repo "$REPO" --body "self-improve: auto-fix gate FAILED (tests_ok=$tests_ok, eval_pass=$eval_pass, total=$eval_total).

\`\`\`
$errsnip
\`\`\`
Manual triage needed." >/dev/null 2>&1 || true
  rm -f "$test_log"
  cleanup
  exit 0
fi
