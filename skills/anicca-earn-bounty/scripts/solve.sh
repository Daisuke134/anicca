#!/usr/bin/env bash
# anicca-earn-bounty/scripts/solve.sh
# picked bounty を fork + branch + Claude code で 解決 + push

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
STATE="$SKILL_DIR/state"

BOUNTY_FILE="$STATE/picked-bounty.json"
[ -f "$BOUNTY_FILE" ] || { echo "[solve] no picked bounty" >&2; exit 1; }

TITLE=$(jq -r .title "$BOUNTY_FILE")
URL=$(jq -r .url "$BOUNTY_FILE")
REPO=$(jq -r .repo "$BOUNTY_FILE")
DESC=$(jq -r .description "$BOUNTY_FILE")
AMOUNT=$(jq -r .amount_usd "$BOUNTY_FILE")
ISSUE_NUM=$(echo "$URL" | grep -oE '/issues/[0-9]+' | grep -oE '[0-9]+' || echo "")

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "[solve] GITHUB_TOKEN required (= anicca-github-account skill が先に走る必要)" >&2
  echo "[solve] dry-run mode: would fork $REPO and solve bounty #$ISSUE_NUM ($AMOUNT USD)" >&2
  exit 2
fi

# Use gh CLI (= login via GITHUB_TOKEN env)
export GH_TOKEN="$GITHUB_TOKEN"

WORK_DIR="$SKILL_DIR/work/$(date -u +%s)"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "[solve] forking $REPO..." >&2
gh repo fork "$REPO" --clone --remote --default-branch-only 2>&1 | tail -3 || {
  echo "[solve] fork failed, may already exist - trying clone of existing fork" >&2
  ANICCA_USER=$(gh api user --jq .login)
  REPO_NAME=$(echo "$REPO" | cut -d/ -f2)
  gh repo clone "$ANICCA_USER/$REPO_NAME" || exit 3
}

REPO_NAME=$(echo "$REPO" | cut -d/ -f2)
cd "$REPO_NAME"

BRANCH="anicca/bounty-$ISSUE_NUM"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Invoke Claude (claude -p subprocess) to fix the bounty
PROMPT="You are Anicca, an autonomous AI agent solving a GitHub bounty for USDC payment.

REPO: $REPO
BOUNTY: $TITLE (\$$AMOUNT)
ISSUE: $URL
DESCRIPTION:
$DESC

Your job:
1. Read the codebase
2. Understand the bounty requirements
3. Implement the smallest correct fix
4. Add tests if the repo has a test framework
5. Commit with message 'fix: <bounty title>' + 'Closes #$ISSUE_NUM'
6. Output ONLY: 'SOLVED' or 'BLOCKED: <reason>'

Constraints:
- No human-in-loop: do not ask questions, just implement
- If unclear: pick the most reasonable interpretation
- Stay scoped to this issue (no refactors)
- Time budget: 30 min wall-clock"

# Use claude -p if available (= claude code subprocess)
if command -v claude &>/dev/null; then
  echo "[solve] invoking claude -p subprocess..." >&2
  echo "$PROMPT" | claude -p --max-turns 30 2>&1 | tee "$STATE/claude-solve-log-$(date +%s).txt" || true
else
  echo "[solve] claude CLI not found - skill scaffolded only, manual claude needed" >&2
  exit 4
fi

# Check if any commits were made on this branch
if git log "origin/main..$BRANCH" --oneline 2>/dev/null | head -1 | grep -q .; then
  echo "[solve] commits detected, pushing..." >&2
  git push --set-upstream origin "$BRANCH" 2>&1 | tail -3
  jq -n --arg branch "$BRANCH" --arg repo "$REPO" --arg url "$URL" \
    --arg work_dir "$WORK_DIR/$REPO_NAME" --argjson bounty "$(cat "$BOUNTY_FILE")" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{branch: $branch, repo: $repo, issue_url: $url, work_dir: $work_dir, bounty: $bounty, solved_at: $ts}' \
    > "$STATE/solved.json"
  echo "[solve] ✓ pushed branch $BRANCH"
else
  echo "[solve] no commits made — Claude declined / failed" >&2
  exit 5
fi
