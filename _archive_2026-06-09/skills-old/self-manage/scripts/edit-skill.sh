#!/usr/bin/env bash
# edit-skill: apply an Anicca-proposed edit to one of her OWN skills (spec 18 §4).
# Isolated worktree → hermes-chat-proposed minimal diff → eval-loop ≥0.7 gate + skill tests
# → commit + PR. Fail-closed: any gate miss rolls back and logs REJECTED.
#
# Usage:
#   edit-skill.sh ['{"type":"skill-edit","skill":"daily-report","reason":"..."}']
#
# Env:
#   DRY_RUN=1   guard + denylist check only; no worktree, no chat, no PR.
#
# Exit: 0 PR opened (or dry-run pass), non-zero on block/reject/error.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPTS/_lib.sh"

# Skills Anicca may NEVER auto-edit (North Star / Law I enforcers + the quality gate core).
PROTECTED_SKILLS="anicca-constitution-guard eval-loop"

prop="${1:-}"
[ -z "$prop" ] && prop="$(sm_latest_unresolved skill-edit)"
if [ -z "$prop" ]; then
  echo "edit-skill: no proposal supplied and no unresolved skill-edit proposal queued" >&2
  exit 0
fi

skill="$(printf '%s' "$prop" | "$JQ" -r '.skill // empty')"
reason="$(printf '%s' "$prop" | "$JQ" -r '.reason // "(no reason)"')"
id="$(sm_id "$prop")"

if [ -z "$skill" ]; then
  echo "edit-skill: proposal missing .skill" >&2
  sm_log "$id" skill-edit ERROR "missing skill field"
  exit 1
fi

# Hard local denylist (independent of the regex guard — defence in depth).
for p in $PROTECTED_SKILLS; do
  if [ "$skill" = "$p" ]; then
    echo "edit-skill: '$skill' is protected (North Star / Law I / eval gate) — refusing" >&2
    sm_log "$id" skill-edit BLOCKED "protected skill: $skill"
    exit 2
  fi
done

skill_dir="$SM_SKILLS_ROOT/$skill"
if [ ! -d "$skill_dir" ]; then
  echo "edit-skill: skill dir not found: $skill_dir" >&2
  sm_log "$id" skill-edit ERROR "skill dir missing: $skill"
  exit 1
fi

intent="Edit my own skill '$skill'. Reason: $reason. This edits skill code only; it does not touch the North Star, Law I, the Constitution, the constitution-guard, or the eval-loop gate."

if ! sm_guard "$intent"; then
  rc=$?
  echo "edit-skill: BLOCKED by constitution-guard (exit $rc)" >&2
  sm_log "$id" skill-edit BLOCKED "guard exit $rc: $skill"
  exit 2
fi

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "edit-skill: DRY_RUN guard+denylist PASS for skill='$skill' (no worktree/PR)"
  exit 0
fi

n="$(date +%s)"
branch="feat/self-manage-skill-${skill}-${n}"
wt="$SM_REPO_ROOT/.worktrees/self-manage-${n}"

cleanup_wt() {
  git -C "$SM_REPO_ROOT" worktree remove --force "$wt" >/dev/null 2>&1 || true
  git -C "$SM_REPO_ROOT" branch -D "$branch" >/dev/null 2>&1 || true
}

if ! git -C "$SM_REPO_ROOT" worktree add "$wt" -b "$branch" >/dev/null 2>&1; then
  echo "edit-skill: worktree add failed" >&2
  sm_log "$id" skill-edit ERROR "worktree add failed"
  exit 1
fi

skill_md="$wt/skills/$skill/SKILL.md"
[ -r "$skill_md" ] || skill_md="$skill_dir/SKILL.md"

# Ask Hermes to propose a minimal unified diff.
chat_out="$(hermes chat -q "Propose a minimal unified diff to the skill '$skill' to address: $reason. Output ONLY the patched SKILL.md content, no prose. Current content:
$(cat "$skill_md" 2>/dev/null)" 2>/dev/null)" || chat_out=""

if [ -z "$chat_out" ]; then
  echo "edit-skill: hermes chat returned empty — rolling back" >&2
  cleanup_wt
  sm_log "$id" skill-edit ERROR "empty chat proposal"
  exit 1
fi

# Apply the proposed content to the worktree copy.
wt_skill_md="$wt/skills/$skill/SKILL.md"
mkdir -p "$(dirname "$wt_skill_md")"
printf '%s\n' "$chat_out" > "$wt_skill_md"

# Run the skill's own tests if present (best-effort; a failing test rejects the edit).
tests_dir="$wt/skills/$skill/tests"
if [ -d "$tests_dir" ]; then
  for t in "$tests_dir"/*.sh; do
    [ -e "$t" ] || continue
    if ! bash "$t" >/dev/null 2>&1; then
      echo "edit-skill: skill test failed ($t) — rolling back" >&2
      cleanup_wt
      sm_log "$id" skill-edit REJECTED "skill test failed: $(basename "$t")"
      exit 3
    fi
  done
fi

# eval-loop gate: classify the proposed edit. input=reason, output=proposed content.
in_f="$(sm_mktemp evalin)"; out_f="$(sm_mktemp evalout)"
printf '%s\n' "$reason" > "$in_f"
printf '%s\n' "$chat_out" > "$out_f"
eval_json="$(EVAL_MODE=production "$EVAL_SH" "$in_f" "$out_f" 2>/dev/null)" || eval_json='{"pass":false}'
rm -f "$in_f" "$out_f"

if ! printf '%s' "$eval_json" | "$JQ" -e '.pass == true' >/dev/null 2>&1; then
  total="$(printf '%s' "$eval_json" | "$JQ" -r '.total // "?"' 2>/dev/null)"
  echo "edit-skill: eval gate FAILED (total=$total) — rolling back" >&2
  cleanup_wt
  sm_log "$id" skill-edit REJECTED "eval gate fail (total=$total)"
  exit 3
fi

# Commit + PR.
git -C "$wt" add "skills/$skill/SKILL.md" >/dev/null 2>&1
git -C "$wt" commit -m "feat(skill): self-manage edit to $skill — $reason

Proposed by Anicca self-manage (#336), eval-loop gated (>=0.7), guard-passed.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>" >/dev/null 2>&1

git -C "$wt" push -u origin "$branch" >/dev/null 2>&1 || true
pr_url="$(gh pr create --repo "$FORUM_REPO" --head "$branch" \
  --title "@anicca self-manage: edit $skill" \
  --body "Anicca-proposed self-edit to \`$skill\` (#336 self-manage).

**Reason:** $reason
**Gate:** eval-loop pass=true, constitution-guard OK.

Filed automatically by skills/self-manage/scripts/edit-skill.sh" 2>/dev/null)" || pr_url=""

if [ -n "$pr_url" ]; then
  echo "edit-skill: PR opened $pr_url"
  sm_log "$id" skill-edit APPLIED "$skill PR=$pr_url"
  exit 0
fi

echo "edit-skill: edit passed gates but PR creation failed (branch pushed: $branch)" >&2
sm_log "$id" skill-edit ERROR "$skill PR creation failed (branch $branch)"
exit 1
