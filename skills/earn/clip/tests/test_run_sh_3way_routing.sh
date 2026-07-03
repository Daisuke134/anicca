#!/usr/bin/env bash
# PROP-005: run.sh's 3-way OUTCOME routing (published/unverified/failed), using a stubbed
# POSTER script (per spec's canonical shapes) instead of a real browser. Instance-isolated
# (uses ANICCA_INSTANCE="vcsdd-test-$$" so this never touches the real queue/ledger/etc).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

setup_wake() {
  # $1 = stub outcome shape (json), sets up a fresh isolated queue/clip/account for one wake
  export ANICCA_INSTANCE="vcsdd-test-3way-$$-$RANDOM"
  unset EARN_LEDGER
  source "$DIR/_instance_paths.sh"
  mkdir -p "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$(dirname "$CLIP_LEDGER")"
  echo "fake mp4 bytes" > "$CLIP_QUEUE/testclip.mp4"
  echo "test caption #hashtags" > "$CLIP_QUEUE/testclip.txt"
  cat > "$CLIP_ACCTS" <<JSON
[{"handle":"testhandle","port":9999,"status":"ready"}]
JSON
  STUB="$(mktemp "${TMPDIR:-/tmp}/vcsdd-stub-poster-XXXXXX")"
  # Print the raw JSON text VERBATIM (a python dict literal is NOT the same as JSON: true/false/null
  # are valid JSON tokens but NOT valid Python identifiers -- embedding $1 as literal python source via
  # `json.dumps($1)` raises NameError, which was silently swallowed by run.sh's `2>/dev/null`, making
  # every case here false-fail on first attempt). Triple-single-quote is safe: the JSON fixtures below
  # contain only double quotes, never single quotes.
  {
    printf '#!/usr/bin/env python3\n'
    printf "print('''%s''')\n" "$1"
  } > "$STUB"
}

teardown_wake() {
  rm -rf "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$CLIP_ACCTS" "$CLIP_LEDGER" "$STUB" 2>/dev/null
}

# --- case 1: published ---
setup_wake '{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/testhandle/reel/FAKE1/"}'
EARN_MODE=execute CLIP_POSTER_OVERRIDE="$STUB" CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
  bash "$DIR/run.sh" >/tmp/vcsdd-3way-out.$$ 2>&1
if [ ! -f "$CLIP_POSTED/testclip.mp4" ] || [ ! -f "$CLIP_POSTED/testclip.txt" ]; then
  echo "FAIL case 1 (published): clip/caption not moved to POSTED"; FAIL=1
fi
if ! grep -q '"status": *"posted"' "$CLIP_LEDGER" 2>/dev/null; then
  echo "FAIL case 1 (published): ledger missing status:posted line"; FAIL=1
fi
if ! grep -q 'FAKE1' "$CLIP_LEDGER" 2>/dev/null; then
  echo "FAIL case 1 (published): ledger missing the confirmed post_url"; FAIL=1
fi
[ "$FAIL" = 0 ] && echo "PASS case 1 (published -> POSTED + ledger status:posted)"
teardown_wake

# --- case 2: unverified ---
setup_wake '{"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null,"before_hrefs":["/testhandle/reel/A/","/testhandle/reel/B/"]}'
EARN_MODE=execute CLIP_POSTER_OVERRIDE="$STUB" CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
  bash "$DIR/run.sh" >/tmp/vcsdd-3way-out.$$ 2>&1
if [ ! -f "$CLIP_PENDING_VERIFY/testclip.mp4" ] || [ ! -f "$CLIP_PENDING_VERIFY/testclip.txt" ]; then
  echo "FAIL case 2 (unverified): clip/caption not moved to PENDING_VERIFY"; FAIL=1
fi
if [ ! -f "$CLIP_PENDING_VERIFY/testclip.before-hrefs.json" ]; then
  echo "FAIL case 2 (unverified): sidecar not written"; FAIL=1
else
  SIDE="$(cat "$CLIP_PENDING_VERIFY/testclip.before-hrefs.json")"
  echo "$SIDE" | grep -q '"before_hrefs"' || { echo "FAIL case 2: sidecar missing before_hrefs"; FAIL=1; }
  echo "$SIDE" | grep -q '"token"' || { echo "FAIL case 2: sidecar missing token"; FAIL=1; }
fi
if ! grep -q '"status": *"unverified"' "$CLIP_LEDGER" 2>/dev/null; then
  echo "FAIL case 2 (unverified): ledger missing status:unverified line"; FAIL=1
fi
if ! grep -q '"post_url": *null' "$CLIP_LEDGER" 2>/dev/null; then
  echo "FAIL case 2 (unverified): ledger post_url must be null, never a candidate"; FAIL=1
fi
[ "$FAIL" = 0 ] && echo "PASS case 2 (unverified -> PENDING_VERIFY + sidecar + ledger status:unverified,post_url:null)"
teardown_wake

# --- case 3: failed ---
setup_wake '{"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null,"error":"no share button"}'
EARN_MODE=execute CLIP_POSTER_OVERRIDE="$STUB" CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
  bash "$DIR/run.sh" >/tmp/vcsdd-3way-out.$$ 2>&1
if [ ! -f "$CLIP_QUEUE/testclip.mp4" ]; then
  echo "FAIL case 3 (failed): clip should stay in QUEUE for retry, but it was moved"; FAIL=1
fi
if [ -s "$CLIP_LEDGER" ]; then
  echo "FAIL case 3 (failed): no ledger line should be written on failure"; FAIL=1
fi
[ "$FAIL" = 0 ] && echo "PASS case 3 (failed -> stays in QUEUE, no ledger line)"
teardown_wake

rm -f /tmp/vcsdd-3way-out.$$

if [ "$FAIL" = 0 ]; then
  echo "ALL PASS (3/3 outcome-routing cases)"
  exit 0
else
  echo "SOME TESTS FAILED"
  exit 1
fi
