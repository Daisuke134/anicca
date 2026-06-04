#!/usr/bin/env bash
# Unit tests for _lib.sh helpers (trigger detection, noise filter, state log).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"

# Isolated state dir for the test (never /tmp).
export STATE_DIR="$HOME/.hermes/state/.forum-test-lib.$$"
mkdir -p "$STATE_DIR"
trap 'rm -rf "$STATE_DIR"' EXIT

# shellcheck disable=SC1091
source "$DIR/_lib.sh"

pass=0; fail=0
ok()  { pass=$((pass+1)); echo "  ok: $1"; }
bad() { fail=$((fail+1)); echo "  FAIL: $1"; }

# --- trigger detection ---
forum_has_trigger "hey @anicca can you help?" && ok "trigger: mid-sentence" || bad "trigger: mid-sentence"
forum_has_trigger "@anicca"                    && ok "trigger: bare at start" || bad "trigger: bare at start"
forum_has_trigger "ping @anicca."              && ok "trigger: trailing dot" || bad "trigger: trailing dot"
forum_has_trigger "mail me at foo@aniccaai.com" && bad "trigger: must NOT match email" || ok "trigger: email not matched"
forum_has_trigger "talk to @aniccabot please"   && bad "trigger: must NOT match @aniccabot" || ok "trigger: @aniccabot not matched"

# --- noise filter ---
forum_is_real "@anicca what model should we use today?" && ok "real: question" || bad "real: question"
forum_is_real "@anicca please investigate the spawn failure on Akash" && ok "real: long substance" || bad "real: long substance"
forum_is_real "@anicca" && bad "real: bare ping should be noise" || ok "noise: bare ping filtered"
forum_is_real "@anicca hi" && bad "real: short ping should be noise" || ok "noise: short ping filtered"

# --- state log ---
forum_claimed 42 && bad "claimed: empty should be false" || ok "claimed: empty=false"
forum_append '{"issue_n":42,"comment_id":1,"claimed_at":"t","mentions_seen":["issue-42"],"responded_to":[]}'
forum_claimed 42 && ok "claimed: after append=true" || bad "claimed: after append"
forum_claimed 99 && bad "claimed: other issue false" || ok "claimed: other issue=false"

# latest-row-wins
forum_append '{"issue_n":42,"comment_id":1,"claimed_at":"t","mentions_seen":["issue-42"],"responded_to":["issue-42"]}'
got="$(forum_row 42 | /usr/bin/jq -r '.responded_to|length')"
[ "$got" = "1" ] && ok "forum_row: latest wins (responded_to=1)" || bad "forum_row: latest wins (got=$got)"

n_latest="$(forum_rows_latest | wc -l | tr -d ' ')"
[ "$n_latest" = "1" ] && ok "forum_rows_latest: dedup to 1 issue" || bad "forum_rows_latest: got $n_latest"

echo "---"
echo "PASS=$pass FAIL=$fail"
[ "$fail" -eq 0 ]
