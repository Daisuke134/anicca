#!/usr/bin/env bash
# E2E: open a live test issue mentioning @anicca, run the orchestrator, and assert
# the ②ACK (👀 + sticky tracking comment) + ③DISCUSS (response in the sticky) cycle.
# Cleans up by closing the test issue. (#334 P9)
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
REPO="${FORUM_REPO:-Daisuke134/anicca-oss}"
JQ=/usr/bin/jq

# Isolated state so this run does not collide with the live cron's state log.
export STATE_DIR="$HOME/.hermes/state/.forum-e2e.$$"
mkdir -p "$STATE_DIR"

ISSUE_N=""
cleanup() {
  if [ -n "$ISSUE_N" ]; then
    gh issue close "$ISSUE_N" -R "$REPO" -c "e2e done — closing test issue" >/dev/null 2>&1 || true
  fi
  rm -rf "$STATE_DIR"
}
trap cleanup EXIT

echo "== 1. create test issue =="
URL="$(gh issue create -R "$REPO" \
  -t "[forum-e2e $(date -u +%H%M%S)] @anicca ping" \
  -b "@anicca please reply with pong-forum and confirm you can read this thread.")"
echo "issue: $URL"
ISSUE_N="$(printf '%s' "$URL" | grep -oE '[0-9]+$')"
[ -n "$ISSUE_N" ] || { echo "FAIL: could not parse issue number"; exit 1; }
echo "issue number: $ISSUE_N"

echo "== 2. wait for issue to appear in the REST list (propagation lag) =="
for i in 1 2 3 4 5 6 7 8 9 10; do
  if gh api "repos/$REPO/issues?state=open&per_page=100" --jq "any(.number==$ISSUE_N)" | grep -q true; then
    echo "issue visible in list (attempt $i)"; break
  fi
  [ "$i" -eq 10 ] && { echo "FAIL: issue never appeared in list within ~50s"; exit 1; }
  sleep 5
done

echo "== 3. run orchestrator =="
bash "$DIR/run.sh"

echo "== 4. assert 👀 reaction =="
if gh api "repos/$REPO/issues/$ISSUE_N/reactions" --jq 'any(.content=="eyes")' | grep -q true; then
  echo "ok: 👀 reaction present"
else
  echo "FAIL: no 👀 reaction"; exit 1
fi

echo "== 5. assert sticky tracking comment + response =="
CID="$("$JQ" -r -s --argjson n "$ISSUE_N" '[.[]|select(.issue_n==$n)]|last|.comment_id' "$STATE_DIR/forum-state.jsonl")"
[ -n "$CID" ] && [ "$CID" != "null" ] || { echo "FAIL: no tracking comment id in state"; exit 1; }
echo "tracking comment id: $CID"

BODY="$(gh api "repos/$REPO/issues/comments/$CID" --jq '.body')"
echo "--- sticky body ---"; printf '%s\n' "$BODY"; echo "-------------------"
printf '%s' "$BODY" | grep -q "Anicca picked this up" || { echo "FAIL: sticky header missing"; exit 1; }
echo "ok: sticky tracking comment exists"

# discuss section: must contain a non-empty response below the --- separator.
RESP="$(printf '%s' "$BODY" | awk '/^---$/{f=1;next} f')"
RESP_TRIM="$(printf '%s' "$RESP" | tr -d '[:space:]')"
if [ -n "$RESP_TRIM" ]; then
  echo "ok: discuss round produced a response ($(printf '%s' "$RESP" | wc -c | tr -d ' ') chars)"
else
  echo "FAIL: discuss section empty"; exit 1
fi

echo ""
echo "E2E PASS — issue=$URL comment_id=$CID"
