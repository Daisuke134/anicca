#!/usr/bin/env bash
# swarm-exec.sh — one Anicca runs code from another Anicca's PR/branch in a sandboxed shell and
# reports back (spec 18 §3 EXECUTION; P14 #337 Wave 1).
#
#   swarm-exec.sh <peer_repo_url> <branch> <task_id>
#
# Safety (HARD RULE):
#   * clone → ~/.cache/anicca-clones/<owner>__<repo> (NEVER /tmp), --depth 1, removed on EXIT.
#   * >100MB repo → no clone (raw mode), exit 78.
#   * isolated run: `timeout 600 env -i PATH=/usr/bin:/bin HOME=$HOME bash --noprofile --norc`.
#   * peer stdout/stderr → ~/.hermes/state/swarm-exec/<task_id>.log (chmod 600).
#   * GH_TOKEN (used only by outer gh) is never passed into the isolated shell.
#   * manual-invoke only (no cron); reports back to a forum sticky comment if SWARM_COMMENT_ID set.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/_lib.sh"

usage() { echo "usage: swarm-exec.sh <peer_repo_url> <branch> <task_id>" >&2; exit 64; }
[ "$#" -eq 3 ] || usage
PEER_URL="$1"; BRANCH="$2"; TASK_ID="$3"

OWNER_REPO="$(se_parse_owner_repo "$PEER_URL")"
OWNER="${OWNER_REPO%%/*}"
REPO="${OWNER_REPO#*/}"
CLONE_DIR="$SWARM_CLONE_ROOT/${OWNER}__${REPO}"
LOG="$LOG_DIR/$(printf '%s' "$TASK_ID" | tr '/:' '__').log"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
MODE="clone"
SIZE_MB=0

# Always remove the clone dir on exit (success OR failure).
cleanup() { rm -rf "$CLONE_DIR" 2>/dev/null || true; }
trap cleanup EXIT

emit() {  # emit <exit_code> <duration_s> <mode> <size_mb> <result_url>
  se_log "$("$JQ" -nc \
    --arg ts "$TS" --arg peer "$PEER_URL" --arg branch "$BRANCH" --arg task "$TASK_ID" \
    --argjson exit_code "$1" --argjson duration_s "$2" --arg mode "$3" \
    --argjson size_mb "$4" --arg result_url "$5" \
    '{ts:$ts, peer_repo:$peer, branch:$branch, task_id:$task, exit_code:$exit_code,
      duration_s:$duration_s, result_url:$result_url, size_mb:$size_mb, mode:$mode}')"
}

# ---- SIZE GATE (skipped for offline tests / file:// via SWARM_SKIP_SIZE_GATE).
if [ "${SWARM_SKIP_SIZE_GATE:-0}" != "1" ]; then
  KB="$(gh repo view "$OWNER/$REPO" --json diskUsage --jq '.diskUsage' 2>/dev/null || echo "")"
  if [ -n "$KB" ] && [ "$KB" -gt 0 ] 2>/dev/null; then
    SIZE_MB=$(( KB / 1024 ))
    if [ "$SIZE_MB" -gt 100 ]; then
      echo "swarm-exec: $OWNER/$REPO is ${SIZE_MB}MB > 100MB — raw mode, NOT cloning (HARD RULE)." >&2
      emit 78 0 "raw" "$SIZE_MB" ""
      exit 78
    fi
  fi
fi

# ---- CLONE (depth 1, specific branch).
START="$(date +%s)"
if ! git clone --depth 1 --branch "$BRANCH" "$PEER_URL" "$CLONE_DIR" >/dev/null 2>&1; then
  echo "swarm-exec: clone failed for $PEER_URL@$BRANCH" >&2
  emit 70 "$(( $(date +%s) - START ))" "$MODE" "$SIZE_MB" ""
  exit 70
fi

# ---- ISOLATED RUN: strip env, no profile, hard time cap. Peer code sees only PATH + HOME.
RUNNER="$(swarm_runner_for "$TASK_ID")"
: > "$LOG"; chmod 600 "$LOG"
timeout 600 env -i PATH=/usr/bin:/bin HOME="$HOME" bash --noprofile --norc -c "
  cd '$CLONE_DIR' || exit 71
  pwd
  git log -1 --oneline
  $RUNNER
" >>"$LOG" 2>&1
EXIT_CODE=$?
DURATION=$(( $(date +%s) - START ))

# ---- REPORT BACK to a forum-issues sticky comment (only if a comment id is provided).
RESULT_URL=""
if [ -n "${SWARM_COMMENT_ID:-}" ]; then
  SUMMARY="$(printf '🤖 **swarm-exec** ran \`%s\` on \`%s@%s\` → exit %s (%ss)\n\n<details><summary>tail</summary>\n\n\`\`\`\n%s\n\`\`\`\n</details>' \
    "$TASK_ID" "$OWNER/$REPO" "$BRANCH" "$EXIT_CODE" "$DURATION" "$(tail -c 1500 "$LOG")")"
  if RESP="$(gh api --method PATCH "repos/$OWNER/$REPO/issues/comments/$SWARM_COMMENT_ID" \
              -f body="$SUMMARY" 2>/dev/null)"; then
    RESULT_URL="$(printf '%s' "$RESP" | "$JQ" -r '.html_url // ""' 2>/dev/null || echo "")"
  fi
fi

emit "$EXIT_CODE" "$DURATION" "$MODE" "$SIZE_MB" "$RESULT_URL"
echo "swarm-exec: $TASK_ID on $OWNER/$REPO@$BRANCH → exit $EXIT_CODE (${DURATION}s), log=$LOG"
exit "$EXIT_CODE"
