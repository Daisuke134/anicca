#!/usr/bin/env bash
# respond.sh — ③ DISCUSS stage (one debate round per tick).
# For each claimed issue: re-fetch the whole thread (= memory), find new real
# @anicca mentions not yet answered, call `hermes chat` (with backoff), and PATCH
# the sticky tracking comment in place. CONSENSUS / max_turns bound the loop.
# (#334 P9, spec 24 §2: thread=memory, AutoGen selector fallback, debate round)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/_lib.sh"

# hermes chat with exponential backoff (2s,4s,8s). Echoes the response, or empty.
# Strips the trailing `session_id: ...` line that -Q quiet mode appends.
hermes_chat_backoff() {
  local prompt="$1" out="" delay=2 i
  for i in 1 2 3; do
    out="$(hermes chat -Q -q "$prompt" 2>/dev/null | grep -v '^session_id:' || true)"
    out="$(printf '%s' "$out" | sed -e 's/[[:space:]]*$//')"
    [ -n "$out" ] && { printf '%s' "$out"; return 0; }
    sleep "$delay"; delay=$((delay*2))
  done
  return 0  # empty → caller writes fallback
}

# Render the final sticky body: header table + the discussion response.
render_sticky() {
  local stage="$1" note="$2" resp="$3"
  printf '%s\n' \
    "👀 **Anicca picked this up** — tracking here." \
    "" \
    "| stage | status |" \
    "|---|---|" \
    "| ack | ✅ claimed |" \
    "| discuss | $stage |" \
    "" \
    "$note" \
    "" \
    "---" \
    "" \
    "$resp"
}

process_issue() {
  local row="$1"
  local n cid
  n="$(printf '%s' "$row" | "$JQ" -r '.issue_n')"
  cid="$(printf '%s' "$row" | "$JQ" -r '.comment_id')"

  local issue thread
  issue="$(gh api "repos/$REPO/issues/$n" --jq '{title:.title, body:(.body // "")}')"
  thread="$(gh api "repos/$REPO/issues/$n/comments" --paginate \
    | "$JQ" -c '.[] | {id:.id, user:.user.login, body:(.body // "")}')"

  # CONSENSUS stop-word: any comment containing the standalone token ends discussion.
  if printf '%s' "$thread" | "$JQ" -r '.body' | grep -Eq '(^|[[:space:]])CONSENSUS([[:space:].!]|$)'; then
    gh api --method PATCH "repos/$REPO/issues/comments/$cid" \
      -f body="$(render_sticky "✅ CONSENSUS reached" "_Discussion closed by stop-word._" "")" >/dev/null
    echo "respond: issue #$n CONSENSUS — closed"
    return 0
  fi

  # max_turns guard.
  local turns
  turns="$(printf '%s' "$row" | "$JQ" -r '.responded_to | length')"
  if [ "$turns" -ge "$FORUM_MAX_TURNS" ]; then
    gh api --method PATCH "repos/$REPO/issues/comments/$cid" \
      -f body="$(render_sticky "⏹ max turns ($FORUM_MAX_TURNS)" "_Discussion bounded; awaiting human/implement stage._" "")" >/dev/null
    echo "respond: issue #$n max_turns — stopped"
    return 0
  fi

  # Find new REAL mentions (body + comments) not in responded_to[].
  local responded new_srcs="" src_body=""
  responded="$(printf '%s' "$row" | "$JQ" -c '.responded_to')"

  local body title
  title="$(printf '%s' "$issue" | "$JQ" -r '.title')"
  body="$(printf '%s' "$issue" | "$JQ" -r '.body')"
  if forum_has_trigger "$body" && forum_is_real "$body"; then
    if ! printf '%s' "$responded" | "$JQ" -e --arg s "issue-$n" 'index($s)' >/dev/null 2>&1; then
      new_srcs="issue-$n"; src_body="$body"
    fi
  fi
  if [ -z "$new_srcs" ]; then
    while IFS= read -r c; do
      [ -n "$c" ] || continue
      local cid2 cb
      cid2="$(printf '%s' "$c" | "$JQ" -r '.id')"
      cb="$(printf '%s' "$c" | "$JQ" -r '.body')"
      if printf '%s' "$cb" | grep -Eq "$TRIGGER" && forum_is_real "$cb"; then
        if ! printf '%s' "$responded" | "$JQ" -e --argjson s "$cid2" 'index($s)' >/dev/null 2>&1; then
          new_srcs="$cid2"; src_body="$cb"; break
        fi
      fi
    done <<< "$thread"
  fi

  if [ -z "$new_srcs" ]; then
    echo "respond: issue #$n no new mentions — skip"
    return 0
  fi

  # Build the debate-round prompt (opinion-update + stop-word instruction).
  local thread_pretty
  thread_pretty="$(printf '%s' "$thread" | "$JQ" -r '"@" + .user + ": " + .body')"
  local prompt
  read -r -d '' prompt <<EOF || true
You are Anicca, an autonomous agent participating in a discussion on the anicca-oss GitHub Issues forum (the swarm collective brain). Speak as yourself in the first person.

ISSUE #$n — $title
$body

FULL THREAD (memory):
$thread_pretty

The most recent message addressed to you:
$src_body

Read the other participants latest messages, update your own position accordingly, and advance the discussion with a concrete, useful reply (max ~150 words). If — and only if — you and the others now fully agree and there is nothing left to decide, end your message with the single word CONSENSUS on its own line.
EOF

  local resp
  resp="$(hermes_chat_backoff "$prompt")"
  local stage note
  if [ -z "$resp" ]; then
    # AutoGen selector fallback: discussion NEVER stalls.
    resp="_(still thinking — will respond next tick)_"
    stage="⏳ pending (retrying)"; note="_LLM did not respond this round._"
  else
    stage="✅ responded"; note="_Round $((turns+1)) — opinion updated from thread._"
  fi

  gh api --method PATCH "repos/$REPO/issues/comments/$cid" \
    -f body="$(render_sticky "$stage" "$note" "$resp")" >/dev/null

  # Re-append updated row (latest-wins).
  forum_append "$("$JQ" -nc \
    --argjson issue_n "$n" --argjson comment_id "$cid" \
    --arg claimed_at "$(printf '%s' "$row" | "$JQ" -r '.claimed_at')" \
    --argjson responded "$responded" --arg src "$new_srcs" \
    '{issue_n:$issue_n, comment_id:$comment_id, claimed_at:$claimed_at,
      mentions_seen:($responded + [$src] | unique),
      responded_to:($responded + [$src] | unique)}')"
  echo "respond: issue #$n responded (src=$new_srcs)"
}

main() {
  local rows
  rows="$(forum_rows_latest)"
  [ -n "$rows" ] || { echo "respond: no claimed issues"; return 0; }
  while IFS= read -r row; do
    [ -n "$row" ] || continue
    process_issue "$row"
  done <<< "$rows"
}

main "$@"
