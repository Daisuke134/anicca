#!/usr/bin/env bash
# Shared helpers for forum-issues skill (#334 P9).
# Stages ②ACK + ③DISCUSS on github.com/Daisuke134/anicca-oss Issues.
# Sourced by poll.sh / respond.sh / run.sh. No top-level side effects beyond mkdir state dir.

JQ=/usr/bin/jq
REPO="${FORUM_REPO:-Daisuke134/anicca-oss}"
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
STATE="$STATE_DIR/forum-state.jsonl"
# Word-boundary @anicca trigger (claude-code-action trigger.ts pattern, spec 24 §2).
TRIGGER='(^|[[:space:]])@anicca([[:space:].,!?;:]|$)'
FORUM_MAX_TURNS="${FORUM_MAX_TURNS:-6}"

mkdir -p "$STATE_DIR"
touch "$STATE"

# forum_has_trigger <text> → exit 0 if the text @mentions anicca on a word boundary.
forum_has_trigger() {
  printf '%s' "$1" | grep -Eq "$TRIGGER"
}

# forum_is_real <text> → exit 0 if the mention is substantive (noise filter, spec 24 §2).
# Real = contains '?' OR has >12 chars of content beyond the bare @anicca token.
forum_is_real() {
  local text="$1"
  case "$text" in
    *\?*) return 0 ;;
  esac
  # strip the @anicca token then measure remaining non-space length
  local rest
  rest="$(printf '%s' "$text" | sed -E 's/@anicca//Ig' | tr -d '[:space:]')"
  [ "${#rest}" -gt 12 ]
}

# forum_claimed <issue_n> → exit 0 if any state row exists for the issue.
forum_claimed() {
  local n="$1"
  [ -s "$STATE" ] || return 1
  "$JQ" -e --argjson n "$n" 'select(.issue_n==$n)' "$STATE" >/dev/null 2>&1
}

# forum_rows_latest → emit the latest row per issue_n (JSONL), newest wins.
forum_rows_latest() {
  [ -s "$STATE" ] || return 0
  "$JQ" -s 'group_by(.issue_n) | map(.[-1]) | .[]' "$STATE" 2>/dev/null | "$JQ" -c .
}

# forum_row <issue_n> → emit the latest row for one issue (JSON, or nothing).
forum_row() {
  local n="$1"
  [ -s "$STATE" ] || return 0
  "$JQ" -c -s --argjson n "$n" '[.[]|select(.issue_n==$n)] | last // empty' "$STATE" 2>/dev/null
}

# forum_append <json-line> → append one row to the state log.
forum_append() {
  printf '%s\n' "$1" >> "$STATE"
}

# forum_mktemp <tag> → create a temp file under STATE_DIR (never /tmp), echo its path.
forum_mktemp() {
  mktemp "$STATE_DIR/.tmp-forum-${1:-x}-XXXXXX.$$"
}
