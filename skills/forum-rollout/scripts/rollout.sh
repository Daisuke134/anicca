#!/usr/bin/env bash
# rollout.sh — #338 P15: CONSENSUS → action. Scans issues' threads for a
# `CONSENSUS:` marker + ```rollout fence, guards + denylists, dispatches to
# self-manage handlers (or gh), logs the decision, comments + closes on success.
# Dry-run by default; --confirm executes. Idempotent on (issue_n, consensus_sha).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/_lib.sh"

MODE="dry-run"
[ "${1:-}" = "--confirm" ] && MODE="confirm"
[ "${1:-}" = "--dry-run" ] && MODE="dry-run"

# Data seam: real gh, or fixtures when FR_FIXTURE_DIR is set (offline tests).
fr_list_issues() {
  if [ -n "${FR_FIXTURE_DIR:-}" ]; then
    "$JQ" -c '.[]' "$FR_FIXTURE_DIR/issues.json"
  else
    gh api "repos/$REPO/issues?state=open&per_page=100" --paginate \
      | "$JQ" -c '.[] | select(.pull_request|not) | {number:.number, body:(.body // "")}'
  fi
}
fr_thread() {
  local n="$1"
  if [ -n "${FR_FIXTURE_DIR:-}" ]; then
    "$JQ" -c '.[]' "$FR_FIXTURE_DIR/thread-$n.json"
  else
    gh api "repos/$REPO/issues/$n/comments" --paginate \
      | "$JQ" -c '.[] | {id:.id, body:(.body // "")}'
  fi
}

# dispatch <action_type> <target> <payload-json> → echoes an evidence string, returns exit code.
dispatch() {
  local at="$1" target="$2" pj="$3" out="" rc=0
  case "$at" in
    edit-skill|edit-heartbeat|spawn-clone|architecture-shift)
      local argv handler; handler="$SELF_MANAGE_DIR/$at.sh"
      argv="$(fr_build_argv "$at" "$target" "$pj")" || { echo "BLOCKED:bad-argv"; return 90; }
      [ -x "$handler" ] || { echo "ERROR:handler-missing"; return 91; }
      if [ "$MODE" = "confirm" ]; then
        out="$("$handler" "$argv" 2>&1)"; rc=$?
      else
        out="$(DRY_RUN=1 "$handler" "$argv" 2>&1)"; rc=$?
      fi
      printf '%s' "$out" | grep -oE 'https?://[^ ]+' | head -1 || printf 'exit-%d' "$rc"
      return "$rc" ;;
    merge-pr)
      if [ "$MODE" = "confirm" ]; then
        gh pr merge "$target" --squash --delete-branch --repo "$REPO" >/dev/null 2>&1; rc=$?
      else
        echo "DRYRUN gh pr merge $target --squash"; rc=0
      fi
      echo "pr#$target"; return "$rc" ;;
    close-issue)
      if [ "$MODE" = "confirm" ]; then
        gh issue close "$target" --repo "$REPO" --comment "rolled out (#338 forum-rollout)" >/dev/null 2>&1; rc=$?
      else
        echo "DRYRUN gh issue close $target"; rc=0
      fi
      echo "issue#$target"; return "$rc" ;;
    open-pr)
      local title head base body
      title="$(printf '%s' "$pj" | "$JQ" -r '.title // "@anicca rollout PR"')"
      head="$(printf '%s' "$pj" | "$JQ" -r '.head // empty')"
      base="$(printf '%s' "$pj" | "$JQ" -r '.base // "main"')"
      body="$(printf '%s' "$pj" | "$JQ" -r '.body // "Filed by forum-rollout (#338)."')"
      if [ "$MODE" = "confirm" ]; then
        out="$(gh pr create --repo "$REPO" --title "$title" --head "$head" --base "$base" --body "$body" 2>&1)"; rc=$?
        printf '%s' "$out" | grep -oE 'https?://[^ ]+' | head -1 || echo "exit-$rc"
      else
        echo "DRYRUN gh pr create --title '$title' --head '$head'"; rc=0
      fi
      return "$rc" ;;
    *) echo "BLOCKED:unknown-action"; return 90 ;;
  esac
}

process_issue() {
  local issue="$1" n body
  n="$(printf '%s' "$issue" | "$JQ" -r '.number')"
  body="$(printf '%s' "$issue" | "$JQ" -r '.body')"

  # Candidate sources: issue body + every comment body. Act on the FIRST that yields a block.
  local srcs=() s
  srcs+=("$body")
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    srcs+=("$(printf '%s' "$c" | "$JQ" -r '.body')")
  done <<< "$(fr_thread "$n")"

  for s in "${srcs[@]}"; do
    local blk; blk="$(fr_extract_block "$s")" || continue
    local marker; marker="$(printf '%s\n' "$s" | grep -iE '^[[:space:]]*CONSENSUS:' | head -1)"
    local sha; sha="$(fr_consensus_sha "$marker" "$blk")"
    if fr_applied "$n" "$sha"; then
      echo "rollout: issue #$n already-applied (sha ${sha:0:8})"; return 0
    fi

    local at target pj
    at="$(fr_field "$blk" ACTION)"; target="$(fr_field "$blk" TARGET)"; pj="$(fr_payload "$blk")"
    if [ -z "$at" ] || [ -z "$target" ]; then
      echo "rollout: issue #$n malformed block — skip"
      fr_log "$n" "$sha" "${at:-none}" "${target:-none}" false 90 "BLOCKED:malformed"
      return 0
    fi

    local summary="Roll out forum CONSENSUS on issue #$n: $at on '$target'. Source: anicca-oss collective forum."
    if ! fr_guard "$summary"; then
      local grc=$?
      echo "rollout: issue #$n BLOCKED by guard (exit $grc)"
      fr_log "$n" "$sha" "$at" "$target" false "$grc" "BLOCKED:guard"
      return 0
    fi
    if fr_hard_no "$target"; then
      echo "rollout: issue #$n TARGET '$target' on HARD-NO list — BLOCKED"
      fr_log "$n" "$sha" "$at" "$target" false 2 "BLOCKED:hard-no-list"
      return 0
    fi

    echo "rollout: issue #$n dispatch $at '$target' (mode=$MODE)"
    local ev rc applied
    ev="$(dispatch "$at" "$target" "$pj")"; rc=$?
    if [ "$MODE" = "confirm" ] && [ "$rc" -eq 0 ]; then applied=true; else applied=false; fi
    fr_log "$n" "$sha" "$at" "$target" "$applied" "$rc" "$ev"

    if [ "$MODE" = "confirm" ] && [ "$rc" -eq 0 ]; then
      gh api --method POST "repos/$REPO/issues/$n/comments" \
        -f body="✅ rolled out: $at \`$target\`. Evidence: $ev" >/dev/null 2>&1 || true
      gh issue close "$n" --repo "$REPO" --comment "rolled out (#338 forum-rollout)" >/dev/null 2>&1 || true
    fi
    return 0
  done
  echo "rollout: issue #$n no rollout block — skip"
}

main() {
  echo "forum-rollout: mode=$MODE repo=$REPO"
  local any=0
  while IFS= read -r issue; do
    [ -n "$issue" ] || continue
    any=1; process_issue "$issue"
  done <<< "$(fr_list_issues)"
  [ "$any" = "1" ] || echo "rollout: no open issues"
}
main "$@"
