#!/usr/bin/env bash
# anicca-earn-bounty/scripts/submit.sh
# solved branch から PR を open + Algora claim comment 追加

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-earn-bounty"
STATE="$SKILL_DIR/state"
SOLVED="$STATE/solved.json"

[ -f "$SOLVED" ] || { echo "[submit] no solved branch (run solve.sh first)" >&2; exit 1; }
[ -z "${GITHUB_TOKEN:-}" ] && { echo "[submit] GITHUB_TOKEN required" >&2; exit 2; }
export GH_TOKEN="$GITHUB_TOKEN"

BRANCH=$(jq -r .branch "$SOLVED")
REPO=$(jq -r .repo "$SOLVED")
ISSUE_URL=$(jq -r .issue_url "$SOLVED")
WORK_DIR=$(jq -r .work_dir "$SOLVED")
AMOUNT=$(jq -r .bounty.amount_usd "$SOLVED")
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')
PLATFORM=$(jq -r .bounty.platform "$SOLVED")

cd "$WORK_DIR" || exit 3

# PR title + body
TITLE=$(jq -r .bounty.title "$SOLVED")
PR_TITLE="$TITLE"
PR_BODY="Closes #$ISSUE_NUM

This PR is submitted by [Anicca](https://aniccaai.com), an autonomous AI agent running on OpenClaw + Claude. All commits are AI-generated.

Bounty platform: $PLATFORM
Reward target: \$$AMOUNT

/claim #$ISSUE_NUM
/attempt #$ISSUE_NUM"

# Open PR
PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY" --base main --head "$BRANCH" 2>&1 | grep -oE 'https://github.com/[^ ]+' | head -1)

if [ -z "$PR_URL" ]; then
  # try master branch
  PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY" --base master --head "$BRANCH" 2>&1 | grep -oE 'https://github.com/[^ ]+' | head -1)
fi

if [ -z "$PR_URL" ]; then
  echo "[submit] PR create failed" >&2
  exit 4
fi

echo "[submit] ✓ PR opened: $PR_URL"

# Add Algora bounty claim comment on the original issue
gh issue comment "$ISSUE_URL" --body "/attempt #$ISSUE_NUM

Anicca is attempting this bounty. PR: $PR_URL" 2>&1 | tail -3 || echo "[submit] issue comment skipped"

# Log
jq -n --arg pr "$PR_URL" --arg issue "$ISSUE_URL" --argjson amount "$AMOUNT" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg platform "$PLATFORM" --arg title "$TITLE" \
  '{platform: $platform, bounty_url: $issue, pr_url: $pr, amount_usd: $amount, status: "pr_opened", title: $title, ts: $ts}' \
  >> "$SKILL_DIR/data/bounty-history.jsonl"

echo "[submit] history logged"
