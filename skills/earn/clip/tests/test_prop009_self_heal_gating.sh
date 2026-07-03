#!/usr/bin/env bash
# PROP-009: self-heal (REQ-008) runs ONCE per wake, is genuinely invoked (a real call-count
# assertion, not merely inferred), and NEVER blocks new-content posting even when self-heal
# itself makes no progress. Also: self-heal must run even on a wake where the queue is empty
# (independent gating -- a real gap caught while wiring self_heal.py into run.sh).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

export ANICCA_INSTANCE="vcsdd-test-prop009-$$-$RANDOM"
unset EARN_LEDGER
source "$DIR/_instance_paths.sh"
mkdir -p "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$(dirname "$CLIP_LEDGER")"
cat > "$CLIP_ACCTS" <<JSON
[{"handle":"testhandle","port":9999,"status":"ready"}]
JSON

CALL_LOG="$(mktemp "${TMPDIR:-/tmp}/vcsdd-prop009-calllog-XXXXXX")"
SELF_HEAL_STUB="$(mktemp "${TMPDIR:-/tmp}/vcsdd-prop009-selfheal-XXXXXX")"
# run.sh invokes SELF_HEAL via "$PY" "$SELF_HEAL" (python3), so this stub must be valid Python,
# not bash (an earlier version of this test used a bash stub, which python3 silently failed to
# parse -- swallowed by run.sh's `2>/dev/null`, producing a false PASS-looking absence of calls).
{
  printf '#!/usr/bin/env python3\n'
  printf 'import sys\n'
  printf "with open('%s', 'a') as f: f.write('called ' + ' '.join(sys.argv[1:]) + chr(10))\n" "$CALL_LOG"
  printf 'print("{\\"status\\":\\"still-pending\\",\\"picked\\":\\"stub\\"}")\n'
} > "$SELF_HEAL_STUB"

POSTER_STUB="$(mktemp "${TMPDIR:-/tmp}/vcsdd-prop009-poster-XXXXXX")"
{
  printf '#!/usr/bin/env python3\n'
  printf "print('''%s''')\n" '{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/testhandle/reel/PROP009/"}'
} > "$POSTER_STUB"

# case A: queue HAS a postable clip -- self-heal must still be called, AND new-content posting
# must still succeed even though self-heal itself made no progress (still-pending stub).
echo "fake mp4 bytes" > "$CLIP_QUEUE/testclip.mp4"
echo "test caption" > "$CLIP_QUEUE/testclip.txt"
EARN_MODE=execute CLIP_POSTER_OVERRIDE="$POSTER_STUB" CLIP_SELF_HEAL_OVERRIDE="$SELF_HEAL_STUB" \
  CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
  bash "$DIR/run.sh" >/tmp/vcsdd-prop009-out.$$ 2>&1

if [ ! -s "$CALL_LOG" ]; then
  echo "FAIL case A: self-heal was NOT invoked when a new clip was also queued"; FAIL=1
else
  echo "PASS case A part 1: self-heal WAS invoked (call-count >= 1) alongside new-content posting"
fi
if [ ! -f "$CLIP_POSTED/testclip.mp4" ]; then
  echo "FAIL case A: new-content posting did not succeed even though self-heal made no progress"; FAIL=1
else
  echo "PASS case A part 2: new-content posting succeeded despite self-heal making no progress"
fi

# case B: queue is EMPTY -- self-heal must STILL be invoked (this was the real gap this test exists
# to catch: run.sh originally exited on "nothing to post" BEFORE ever reaching self-heal).
: > "$CALL_LOG"
EARN_MODE=execute CLIP_POSTER_OVERRIDE="$POSTER_STUB" CLIP_SELF_HEAL_OVERRIDE="$SELF_HEAL_STUB" \
  CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
  bash "$DIR/run.sh" >/tmp/vcsdd-prop009-out.$$ 2>&1
if [ ! -s "$CALL_LOG" ]; then
  echo "FAIL case B: self-heal was NOT invoked on a wake with an empty queue"; FAIL=1
else
  echo "PASS case B: self-heal WAS invoked even though the queue was empty"
fi

rm -rf "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$CLIP_ACCTS" "$CLIP_LEDGER" "$CALL_LOG" "$SELF_HEAL_STUB" "$POSTER_STUB" /tmp/vcsdd-prop009-out.$$ 2>/dev/null

if [ "$FAIL" = 0 ]; then
  echo "ALL PASS (PROP-009 self-heal gating)"
  exit 0
else
  echo "SOME TESTS FAILED"
  exit 1
fi
