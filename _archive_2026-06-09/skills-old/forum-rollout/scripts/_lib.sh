#!/usr/bin/env bash
# Shared helpers for forum-rollout (#338 P15). Sourced by rollout.sh / run.sh.
# No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash
# shellcheck disable=SC2034  # REPO / SELF_MANAGE_DIR are consumed by rollout.sh which sources this file.
JQ="${JQ:-/usr/bin/jq}"
REPO="${FORUM_REPO:-Daisuke134/anicca-oss}"
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
ROLLOUT_LOG="$STATE_DIR/forum-rollout.jsonl"

# Skills/targets Anicca may NEVER roll out against (canonical chokepoints; only Dais edits).
HARD_NO_LIST="anicca-constitution-guard eval-loop anicca-payout-ubi anicca-wallet forum-rollout"

# Resolve self-manage handler dir + guard (overridable for tests).
FR_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FR_SKILLS_ROOT="$(cd "$FR_SKILL_DIR/.." && pwd)"
SELF_MANAGE_DIR="${FR_SELF_MANAGE_DIR:-$FR_SKILLS_ROOT/self-manage/scripts}"
GUARD_CHECK="${FR_GUARD_CHECK:-$FR_SKILLS_ROOT/anicca-constitution-guard/scripts/check.sh}"

mkdir -p "$STATE_DIR"
touch "$ROLLOUT_LOG"

fr_mktemp() { mktemp "$STATE_DIR/.tmp-fr-${1:-x}-XXXX.$$"; }

# fr_extract_block <comment-body> → if it has a CONSENSUS: marker AND a ```rollout fence,
# echo the fence body (between ```rollout and the next ```). Else echo nothing, return 1.
fr_extract_block() {
  local body="$1"
  printf '%s\n' "$body" | grep -Eq '^[[:space:]]*CONSENSUS:' || return 1
  local fence
  fence="$(printf '%s\n' "$body" | awk '
    /^[[:space:]]*```rollout[[:space:]]*$/ {inb=1; next}
    inb && /^[[:space:]]*```[[:space:]]*$/ {inb=0; exit}
    inb {print}
  ')"
  [ -n "$fence" ] || return 1
  printf '%s\n' "$fence"
}

# fr_field <block> <KEY> → value of "KEY: ..." (case-insensitive key), trimmed.
fr_field() {
  printf '%s\n' "$1" | grep -iE "^[[:space:]]*$2:" | head -1 \
    | sed -E "s/^[[:space:]]*[A-Za-z-]+:[[:space:]]*//" | sed -E 's/[[:space:]]+$//'
}

# fr_payload <block> → the PAYLOAD JSON (everything after PAYLOAD:), or {} if absent/invalid.
fr_payload() {
  local raw
  raw="$(printf '%s\n' "$1" | grep -iE '^[[:space:]]*PAYLOAD:' | head -1 \
    | sed -E 's/^[[:space:]]*[Pp][Aa][Yy][Ll][Oo][Aa][Dd]:[[:space:]]*//')"
  [ -n "$raw" ] || { echo '{}'; return 0; }
  if printf '%s' "$raw" | "$JQ" -ce . >/dev/null 2>&1; then printf '%s' "$raw"; else echo '{}'; fi
}

# fr_consensus_sha <consensus-marker-line> <block> → 64-hex sha256 (idempotency key).
fr_consensus_sha() {
  printf '%s\n%s' "$1" "$2" | /usr/bin/shasum -a 256 | cut -c1-64
}

# fr_hard_no <target> → exit 0 (BLOCK) if target matches any HARD-NO token as a whole
# word or path segment. exit 1 = allowed.
fr_hard_no() {
  local t="$1" tok
  for tok in $HARD_NO_LIST; do
    [ "$t" = "$tok" ] && return 0
    case "$t" in
      *"/$tok/"*|*"/$tok"|"$tok/"*) return 0 ;;
      *" $tok "*|"$tok "*|*" $tok") return 0 ;;
    esac
  done
  return 1
}

# fr_applied <issue_n> <sha> → exit 0 if (issue_n, sha) already in the log (idempotency).
fr_applied() {
  [ -s "$ROLLOUT_LOG" ] || return 1
  "$JQ" -e --argjson n "$1" --arg s "$2" \
    'select(.issue_n==$n and .consensus_sha==$s)' "$ROLLOUT_LOG" >/dev/null 2>&1
}

# fr_log <issue_n> <sha> <action_type> <target> <applied bool> <exit_code> <evidence>
fr_log() {
  "$JQ" -nc --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson issue_n "$1" --arg consensus_sha "$2" --arg action_type "$3" \
    --arg target "$4" --argjson applied "$5" --argjson exit_code "$6" --arg evidence_url "$7" \
    '{ts:$ts, issue_n:$issue_n, consensus_sha:$consensus_sha, action_type:$action_type,
      target:$target, applied:$applied, exit_code:$exit_code, evidence_url:$evidence_url}' \
    >> "$ROLLOUT_LOG"
}

# fr_guard <summary> → guard exit code. Fail-closed if guard missing.
fr_guard() {
  [ -x "$GUARD_CHECK" ] || { echo "forum-rollout: guard not executable: $GUARD_CHECK" >&2; return 99; }
  "$GUARD_CHECK" --action "$1" >/dev/null 2>&1
}

# fr_build_argv <action_type> <target> <payload-json> → merged JSON for self-manage handlers.
fr_build_argv() {
  local at="$1" target="$2" pj="$3"
  case "$at" in
    edit-skill)         printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"skill-edit", skill:($t), reason:(.reason // "forum consensus")}' ;;
    edit-heartbeat)     printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"heartbeat", schedule:(.schedule // $t), reason:(.reason // "forum consensus")}' ;;
    spawn-clone)        printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"spawn", name:(.name // $t), reason:(.reason // "forum consensus")}' ;;
    architecture-shift) printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"arch-shift", title:(.title // $t), body:(.body // ""), reason:(.reason // "forum consensus")}' ;;
    *) return 1 ;;
  esac
}
