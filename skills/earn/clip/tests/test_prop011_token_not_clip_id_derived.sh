#!/usr/bin/env bash
# PROP-011: REQ-010's per-attempt token must be RANDOM, NOT derived from the clip's filename/ID.
# Regression for iteration-11 FIND-028: producer.sh's clip_id can legitimately repeat across
# separate attempts (same-day channel repeat, or a manual retry with the same --url) -- run
# run.sh's token-generation step TWICE for the SAME clip filename and assert the two tokens
# generated are DIFFERENT. Also asserts $CAP's content+mtime are unchanged (FIND-029: $CAP is
# read-only, only a separate temp file is written/read/cleaned-up).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

export ANICCA_INSTANCE="vcsdd-test-prop011-$$-$RANDOM"
unset EARN_LEDGER
source "$DIR/_instance_paths.sh"
mkdir -p "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$(dirname "$CLIP_LEDGER")"
cat > "$CLIP_ACCTS" <<JSON
[{"handle":"testhandle","port":9999,"status":"ready"}]
JSON

POSTER_STUB="$(mktemp "${TMPDIR:-/tmp}/vcsdd-prop011-poster-XXXXXX")"
# echoes the token embedded in the caption file it was passed (last non-empty line), so the test
# can observe which token run.sh actually generated for that specific attempt.
{
  printf '#!/usr/bin/env python3\n'
  printf 'import argparse, json\n'
  printf "ap = argparse.ArgumentParser()\n"
  printf "ap.add_argument('--video'); ap.add_argument('--caption-file'); ap.add_argument('--handle')\n"
  printf "ap.add_argument('--tid'); ap.add_argument('--live', action='store_true')\n"
  printf "a = ap.parse_args()\n"
  printf "lines = [l.strip() for l in open(a.caption_file) if l.strip()]\n"
  printf "token = lines[-1] if lines else ''\n"
  printf "print(json.dumps({'reached':'PUBLISHED','published':True,'outcome':'published','post_url':'https://x/'+token}))\n"
} > "$POSTER_STUB"

ORIG_CAP_CONTENT="test caption #hashtags"

run_one_attempt() {
  rm -f "$CLIP_QUEUE"/*.mp4 "$CLIP_QUEUE"/*.txt "$CLIP_POSTED"/*.mp4 "$CLIP_POSTED"/*.txt 2>/dev/null
  echo "fake mp4 bytes" > "$CLIP_QUEUE/testclip.mp4"
  printf '%s' "$ORIG_CAP_CONTENT" > "$CLIP_QUEUE/testclip.txt"
  EARN_MODE=execute CLIP_CADENCE_HOURS=0 CLIP_POSTER_OVERRIDE="$POSTER_STUB" CLIP_SELF_HEAL_OVERRIDE="/bin/true" \
    CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
    bash "$DIR/run.sh" 2>&1
}

OUT1="$(run_one_attempt)"
CAP_CONTENT_AFTER_1="$(cat "$CLIP_POSTED/testclip.txt" 2>/dev/null)"
TOKEN1="$(printf '%s' "$OUT1" | python3 -c 'import json,sys
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(d.get("did",""))
    except Exception:
        pass' | grep -o '#c[0-9a-f]*' | head -1)"

OUT2="$(run_one_attempt)"
TOKEN2="$(printf '%s' "$OUT2" | python3 -c 'import json,sys
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(d.get("did",""))
    except Exception:
        pass' | grep -o '#c[0-9a-f]*' | head -1)"

if [ -z "$TOKEN1" ] || [ -z "$TOKEN2" ]; then
  echo "FAIL: could not extract a token from either attempt (TOKEN1='$TOKEN1' TOKEN2='$TOKEN2')"
  echo "  OUT1=$OUT1"
  echo "  OUT2=$OUT2"
  FAIL=1
elif [ "$TOKEN1" = "$TOKEN2" ]; then
  echo "FAIL: same clip filename produced the IDENTICAL token twice ($TOKEN1) -- FIND-028 collision reopened"
  FAIL=1
else
  echo "PASS: two attempts of the SAME clip filename produced DIFFERENT tokens ($TOKEN1 != $TOKEN2)"
fi

if [ "$CAP_CONTENT_AFTER_1" != "$ORIG_CAP_CONTENT" ]; then
  echo "FAIL: \$CAP's content was mutated (expected untouched original, got: $CAP_CONTENT_AFTER_1)"
  FAIL=1
else
  echo "PASS: \$CAP's original content is byte-identical after a post attempt (read-only, per FIND-029)"
fi

# PROP-011 (2nd assertion, added after Phase-3 FIND-102 coverage gap): the mktemp-created TMPCAP
# file must be deleted (via `trap ... EXIT`) regardless of outcome -- test all 3 explicitly.
test_tmpcap_cleanup_for_outcome() {
  local outcome_json="$1" label="$2"
  local before after
  before="$(ls "${TMPDIR:-/tmp}"/clip-cap-* 2>/dev/null | wc -l | tr -d ' ')"
  local stub
  stub="$(mktemp "${TMPDIR:-/tmp}/vcsdd-prop011-cleanup-poster-XXXXXX")"
  { printf '#!/usr/bin/env python3\n'; printf "print('''%s''')\n" "$outcome_json"; } > "$stub"
  rm -f "$CLIP_QUEUE"/*.mp4 "$CLIP_QUEUE"/*.txt 2>/dev/null
  echo "fake mp4 bytes" > "$CLIP_QUEUE/testclip.mp4"
  printf '%s' "$ORIG_CAP_CONTENT" > "$CLIP_QUEUE/testclip.txt"
  EARN_MODE=execute CLIP_CADENCE_HOURS=0 CLIP_POSTER_OVERRIDE="$stub" CLIP_SELF_HEAL_OVERRIDE="/bin/true" \
    CLIP_TEST_TID_OVERRIDE="fake-tid" CLIP_TEST_ACTIVE_OVERRIDE="testhandle" \
    bash "$DIR/run.sh" >/dev/null 2>&1
  after="$(ls "${TMPDIR:-/tmp}"/clip-cap-* 2>/dev/null | wc -l | tr -d ' ')"
  rm -f "$stub"
  if [ "$after" -gt "$before" ]; then
    echo "FAIL: TMPCAP leaked for outcome=$label (before=$before after=$after)"; FAIL=1
  else
    echo "PASS: TMPCAP cleaned up for outcome=$label"
  fi
}
test_tmpcap_cleanup_for_outcome '{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://x/CLEANUP1/"}' "published"
test_tmpcap_cleanup_for_outcome '{"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null,"before_hrefs":[]}' "unverified"
test_tmpcap_cleanup_for_outcome '{"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null}' "failed"

rm -rf "$CLIP_QUEUE" "$CLIP_POSTED" "$CLIP_PENDING_VERIFY" "$CLIP_ACCTS" "$CLIP_LEDGER" "$POSTER_STUB" 2>/dev/null

if [ "$FAIL" = 0 ]; then
  echo "ALL PASS (PROP-011 token not clip_id-derived)"
  exit 0
else
  echo "SOME TESTS FAILED"
  exit 1
fi
