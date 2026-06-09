#!/usr/bin/env bash
# share-learning: after a successful auto-fix PR, record the learning so ALL
# instances benefit (the forum brain, spec 18 §2). Appends one row to
# learnings.jsonl + comments the source issue with the insight.
#
# Usage: share-learning.sh <issue_number> <pr_url_or_number> <category> <insight>
# Env:
#   DRY_RUN=1   print the learning JSON only, no state write, no gh comment.
#   GH_TOKEN    inherited by gh (never echoed).
set -uo pipefail

ISSUE="${1:-}"; PR="${2:-}"; CATEGORY="${3:-}"; INSIGHT="${4:-}"
if [ -z "$ISSUE" ] || [ -z "$INSIGHT" ]; then
  echo "usage: share-learning.sh <issue_number> <pr_url_or_number> <category> <insight>" >&2
  exit 2
fi

STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
REPO="${SELF_IMPROVE_REPO:-Daisuke134/anicca-oss}"
JQ=/usr/bin/jq
mkdir -p "$STATE_DIR"
LEARNINGS="$STATE_DIR/learnings.jsonl"

# normalize PR to a number if a URL was passed
pr_num="$(printf '%s' "$PR" | grep -oE '[0-9]+$' || echo "$PR")"

row="$("$JQ" -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg issue "$ISSUE" --arg pr "$pr_num" \
  --arg cat "${CATEGORY:-general}" --arg insight "$INSIGHT" \
  '{ts:$ts, issue:($issue|tonumber?), pr:($pr|tonumber?), category:$cat, insight:$insight}')"

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "$row"
  exit 0
fi

printf '%s\n' "$row" >> "$LEARNINGS"

gh issue comment "$ISSUE" --repo "$REPO" --body "**Learning shared to the forum** (category: ${CATEGORY:-general})

$INSIGHT

PR: #$pr_num — recorded to learnings.jsonl so every instance benefits. Closing." >/dev/null 2>&1 || true
gh issue close "$ISSUE" --repo "$REPO" >/dev/null 2>&1 || true

echo "$row"
