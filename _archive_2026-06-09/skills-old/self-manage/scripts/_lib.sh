#!/usr/bin/env bash
# Shared helpers for self-manage (#336 P13). Sourced by every script in this skill.
# No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash

JQ=/usr/bin/jq
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
PROPOSALS="$STATE_DIR/self-manage-proposals.jsonl"
DECISIONS="$STATE_DIR/self-manage-decisions.jsonl"

# Resolve the anicca-oss repo root from this skill (works in worktree or merged tree).
SM_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SM_SKILLS_ROOT="$(cd "$SM_SKILL_DIR/.." && pwd)"          # .../skills
SM_REPO_ROOT="$(cd "$SM_SKILLS_ROOT/.." && pwd)"          # .../anicca-oss(.worktrees/...)

GUARD_CHECK="$SM_SKILLS_ROOT/anicca-constitution-guard/scripts/check.sh"
EVAL_SH="$SM_SKILLS_ROOT/eval-loop/scripts/eval.sh"
SPAWN_CHILD="$SM_SKILLS_ROOT/spawn-child/scripts/spawn-child.sh"

FORUM_REPO="${FORUM_REPO:-Daisuke134/anicca-oss}"

mkdir -p "$STATE_DIR"
touch "$PROPOSALS" "$DECISIONS"

# sm_mktemp <tag> → temp file under STATE_DIR (never /tmp).
sm_mktemp() { mktemp "$STATE_DIR/.tmp-sm-${1:-x}-XXXX.$$"; }

# sm_id <proposal-json-line> → deterministic 16-hex id (resolution key).
sm_id() {
  printf '%s' "$1" | /usr/bin/shasum -a 256 | cut -c1-16
}

# sm_guard <intent-text> → run constitution-guard. Echoes nothing; returns guard exit code
# (0 OK, 2 rule BLOCKED, 3 hash BLOCKED, 4 usage). Fail-closed: if the guard script is
# missing or unrunnable, return non-zero so the caller blocks.
sm_guard() {
  [ -x "$GUARD_CHECK" ] || { echo "self-manage: guard not executable: $GUARD_CHECK" >&2; return 99; }
  "$GUARD_CHECK" --action "$1" >/dev/null 2>&1
}

# sm_log <id> <type> <decision> <detail>
sm_log() {
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  "$JQ" -nc --arg ts "$ts" --arg id "$1" --arg type "$2" \
        --arg decision "$3" --arg detail "$4" \
        '{ts:$ts, id:$id, type:$type, decision:$decision, detail:$detail}' >> "$DECISIONS"
}

# sm_resolved <id> → exit 0 if a decision row already exists for this id (idempotency).
sm_resolved() {
  [ -s "$DECISIONS" ] || return 1
  "$JQ" -e --arg id "$1" 'select(.id==$id)' "$DECISIONS" >/dev/null 2>&1
}

# sm_latest_unresolved <type> → emit the latest proposal line of <type> with no decision yet.
# Walks PROPOSALS oldest→newest, prints the LAST unresolved match (or nothing).
sm_latest_unresolved() {
  local want="$1" line id out=""
  [ -s "$PROPOSALS" ] || return 0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    [ "$(printf '%s' "$line" | "$JQ" -r '.type // empty' 2>/dev/null)" = "$want" ] || continue
    id="$(sm_id "$line")"
    sm_resolved "$id" && continue
    out="$line"
  done < "$PROPOSALS"
  [ -n "$out" ] && printf '%s\n' "$out"
}
