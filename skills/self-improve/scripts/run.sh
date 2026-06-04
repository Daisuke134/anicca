#!/usr/bin/env bash
# run: orchestrate the self-improvement loop (spec 18 §1).
#   meta-cognition → detect → file-issue → attempt-fix → share-learning.
# Each step is idempotent: file-issue dedups per (issue_type, day);
# attempt-fix is invoked once per newly-filed issue this run.
#
# Emits ONE trace JSONL line to stdout + appends to self-improve.jsonl.
# Env:
#   DRY_RUN=1   propagate dry mode to all steps (no gh/worktree/hermes writes).
set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
JQ=/usr/bin/jq
mkdir -p "$STATE_DIR"
TRACE="$STATE_DIR/self-improve.jsonl"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. meta-cognition
meta="$("$SCRIPTS/meta-cognition.sh" 2>/dev/null)" || meta='{}'

# 2. detect
detected="$(printf '%s' "$meta" | "$SCRIPTS/detect.sh" 2>/dev/null)" || detected=""
n_detected="$(printf '%s\n' "$detected" | grep -c . || true)"

# 3. file-issue (dedups internally); capture newly-created issue numbers
filed_out="$(printf '%s\n' "$detected" | "$SCRIPTS/file-issue.sh" 2>/dev/null)" || filed_out=""
# new issue numbers = trailing digits of any printed gh URL (skip DRY titles)
new_issues="$(printf '%s\n' "$filed_out" | grep -oE 'github.com/[^ ]+/issues/[0-9]+$' | grep -oE '[0-9]+$' || true)"
n_filed="$(printf '%s\n' "$new_issues" | grep -c . || true)"

# 4. attempt-fix for each newly filed issue (one shot per run; idempotent
#    because file-issue won't refile the same type the same day)
n_fixed=0
if [ "${DRY_RUN:-}" != "1" ] && [ -n "$new_issues" ]; then
  while IFS= read -r issue; do
    [ -z "$issue" ] && continue
    pr="$("$SCRIPTS/attempt-fix.sh" "$issue" 2>/dev/null)" || pr=""
    if printf '%s' "$pr" | grep -qE 'github.com/.+/pull/[0-9]+'; then
      n_fixed=$((n_fixed+1))
      # 5. share-learning on success
      "$SCRIPTS/share-learning.sh" "$issue" "$pr" "auto-fix" \
        "Autonomous fix landed for issue #$issue via self-improve loop." >/dev/null 2>&1 || true
    fi
  done <<EOF
$new_issues
EOF
fi

line="$("$JQ" -nc \
  --arg ts "$NOW" \
  --argjson detected "${n_detected:-0}" \
  --argjson filed "${n_filed:-0}" \
  --argjson fixed "${n_fixed:-0}" \
  --argjson dry "$([ "${DRY_RUN:-}" = "1" ] && echo true || echo false)" \
  '{ts:$ts, detected:$detected, filed:$filed, fixed:$fixed, dry_run:$dry}')"

printf '%s\n' "$line" >> "$TRACE"
echo "$line"
