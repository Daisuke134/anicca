#!/usr/bin/env bash
# poll.sh — ② ACK stage. Drains open issues, claims new @anicca mentions:
# adds 👀 reaction + creates a sticky tracking comment + records a state row.
# Idempotent: already-claimed issues are skipped. (#334 P9, spec 24 §2)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/_lib.sh"

INITIAL_BODY() {
  printf '%s\n' \
    "👀 **Anicca picked this up** — tracking here." \
    "" \
    "| stage | status |" \
    "|---|---|" \
    "| ack | ✅ claimed $(date -u +%Y-%m-%dT%H:%M:%SZ) |" \
    "| discuss | ⏳ pending |" \
    "" \
    "_This comment updates in place as the discussion progresses._"
}

main() {
  # Open issues only (gh /issues includes PRs; filter them out via .pull_request).
  local issues
  issues="$(gh api "repos/$REPO/issues?state=open&per_page=100" --paginate \
    | "$JQ" -c '.[] | select(.pull_request|not) | {n:.number, body:(.body // "")}')"

  [ -n "$issues" ] || { echo "poll: no open issues"; return 0; }

  local claimed_count=0
  while IFS= read -r issue; do
    [ -n "$issue" ] || continue
    local n body
    n="$(printf '%s' "$issue" | "$JQ" -r '.n')"
    body="$(printf '%s' "$issue" | "$JQ" -r '.body')"

    forum_claimed "$n" && continue

    # source of the first mention: body, else first matching comment.
    local src="" mention_text=""
    if forum_has_trigger "$body"; then
      src="issue-$n"; mention_text="$body"
    else
      # scan comments for the earliest @anicca mention
      local hit
      hit="$(gh api "repos/$REPO/issues/$n/comments" --paginate \
        | "$JQ" -c '.[] | {id:.id, body:(.body // "")}' \
        | while IFS= read -r c; do
            local cb; cb="$(printf '%s' "$c" | "$JQ" -r '.body')"
            if printf '%s' "$cb" | grep -Eq "$TRIGGER"; then printf '%s\n' "$c"; break; fi
          done)"
      if [ -n "$hit" ]; then
        src="$(printf '%s' "$hit" | "$JQ" -r '.id')"
        mention_text="$(printf '%s' "$hit" | "$JQ" -r '.body')"
      fi
    fi

    [ -n "$src" ] || continue

    echo "poll: claiming issue #$n (src=$src)"
    # 👀 reaction (OpenHands _add_reaction). Idempotent on GitHub side.
    gh api "repos/$REPO/issues/$n/reactions" -f content=eyes >/dev/null 2>&1 || true
    # sticky tracking comment
    local cid
    cid="$(gh api "repos/$REPO/issues/$n/comments" -f body="$(INITIAL_BODY)" --jq '.id')"
    forum_append "$("$JQ" -nc \
      --argjson issue_n "$n" --argjson comment_id "$cid" \
      --arg claimed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --arg src "$src" \
      '{issue_n:$issue_n, comment_id:$comment_id, claimed_at:$claimed_at, mentions_seen:[$src], responded_to:[]}')"
    claimed_count=$((claimed_count+1))
  done <<< "$issues"

  echo "poll: claimed $claimed_count new issue(s)"
}

main "$@"
