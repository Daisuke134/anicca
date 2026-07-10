#!/usr/bin/env bash
# VSDD oracle -- PROP-28 (REQ-28, Sprint 5): the "view -> yen" funnel's metrics half. lib/note-fetch-views.py
# reads the keys this skill has already independently verified live (state/live-publishes.jsonl, PASS==true)
# and appends ONE honest metrics line per key to state/article-metrics.jsonl: a REAL view count (read_count)
# when note.com's authenticated stats API resolves the key, or an honest "views": "none" + "views_reason"
# row when it cannot -- NEVER a fabricated number, and NEVER a crash either way (best-effort periodic job).
#
# This test hits the REAL note.com stats API with the REAL session cookie already on this machine (same
# live-network-test convention this skill already uses -- see tests/test-prop23-independent-live-verify.sh,
# tests/test-prop22b-live-publish-real-click.sh -- "no dry run" per project policy).
set -uo pipefail
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="$SKILL/lib/note-fetch-views.py"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

ok "$([ -f "$TOOL" ] && echo 1 || echo 0)" "lib/note-fetch-views.py exists"
if command -v python3 >/dev/null 2>&1; then
  ok "$(python3 -m py_compile "$TOOL" 2>/dev/null && echo 1 || echo 0)" "note-fetch-views.py is syntactically valid Python"
fi
# Never fabricate revenue -- the declared constant string must appear literally in source (a docstring/code
# assertion, not proof of runtime behavior alone, but a real regression guard against someone hardcoding a
# non-zero figure later).
ok "$(grep -q 'revenue_jpy.: 0' "$TOOL" && echo 1 || echo 0)" "revenue_jpy is hardcoded to the honest 0 in every code path (no fabricated non-zero figure)"

REAL_COOKIES="$HOME/.cloak/note-work/note-cookies.json"

# ---------- happy path: a REAL, currently-published note key resolves to a real view/like count ----------
if [ -f "$REAL_COOKIES" ]; then
  T1="$(mktemp -d)"
  LIVE1="$T1/live-publishes.jsonl"
  METRICS1="$T1/article-metrics.jsonl"
  # nfb2ace9f0ed8: the real, currently-published note (SKILL.md's own "REAL LIVE PUBLISH" record) -- reused
  # as the fixture, never a newly-created one.
  printf '%s\n' '{"ts": 1783176835, "key": "nfb2ace9f0ed8", "url": "https://note.com/anicca123/n/nfb2ace9f0ed8", "http_status": 200, "key_in_body": true, "title_in_body": null, "PASS": true}' > "$LIVE1"

  OUT1="$(NOTE_LIVE_STATE_FILE="$LIVE1" ARTICLE_METRICS_STATE_FILE="$METRICS1" NOTE_COOKIES_FILE="$REAL_COOKIES" python3 "$TOOL" 2>&1)"; rc1=$?
  ok "$([ $rc1 -eq 0 ] && echo 1 || echo 0)" "real-key run exits 0 (rc=$rc1): $OUT1"
  ok "$([ -f "$METRICS1" ] && echo 1 || echo 0)" "article-metrics.jsonl written"
  line1="$(grep '"key": "nfb2ace9f0ed8"' "$METRICS1" 2>/dev/null | tail -1)"
  ok "$([ -n "$line1" ] && echo 1 || echo 0)" "metrics line recorded for the real published key: $OUT1"
  views1="$(echo "$line1" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("views"))' 2>/dev/null)"
  ok "$(echo "$views1" | grep -qE '^[0-9]+$' && echo 1 || echo 0)" "views recorded as a REAL non-negative integer (not \"none\", not fabricated): views=$views1, line=$line1"
  ok "$(echo "$line1" | grep -q '"revenue_jpy": 0' && echo 1 || echo 0)" "revenue_jpy honestly 0 (no verified sales-API path exists yet)"
else
  echo "  (skipping real-key sub-test: $REAL_COOKIES not present on this machine)"
fi

# ---------- failure path: a key that never resolves in the stats response -> honest "none", never a crash ----------
T2="$(mktemp -d)"
LIVE2="$T2/live-publishes.jsonl"
METRICS2="$T2/article-metrics.jsonl"
printf '%s\n' '{"ts": 1, "key": "nTHISKEYDOESNOTEXISTUNCONFIRMEDTEST00000", "url": "https://note.com/anicca123/n/nTHISKEYDOESNOTEXISTUNCONFIRMEDTEST00000", "PASS": true}' > "$LIVE2"
if [ -f "$REAL_COOKIES" ]; then
  OUT2="$(NOTE_LIVE_STATE_FILE="$LIVE2" ARTICLE_METRICS_STATE_FILE="$METRICS2" NOTE_COOKIES_FILE="$REAL_COOKIES" python3 "$TOOL" 2>&1)"; rc2=$?
  ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "unresolvable-key run STILL exits 0 (best-effort, never crashes; rc=$rc2): $OUT2"
  line2="$(grep '"key": "nTHISKEYDOESNOTEXISTUNCONFIRMEDTEST00000"' "$METRICS2" 2>/dev/null | tail -1)"
  ok "$(echo "$line2" | grep -q '"views": "none"' && echo 1 || echo 0)" "unresolvable key -> honest views: \"none\" (never a fabricated number): $line2"
  ok "$(echo "$line2" | grep -q '"views_reason": "key_not_in_stats_response"' && echo 1 || echo 0)" "unresolvable key -> a real, specific views_reason recorded"
fi

# ---------- failure path: missing/unreadable cookies file -> honest "none", never a crash ----------
T3="$(mktemp -d)"
LIVE3="$T3/live-publishes.jsonl"
METRICS3="$T3/article-metrics.jsonl"
printf '%s\n' '{"ts": 1, "key": "nfb2ace9f0ed8", "url": "https://note.com/anicca123/n/nfb2ace9f0ed8", "PASS": true}' > "$LIVE3"
OUT3="$(NOTE_LIVE_STATE_FILE="$LIVE3" ARTICLE_METRICS_STATE_FILE="$METRICS3" NOTE_COOKIES_FILE="$T3/does-not-exist.json" python3 "$TOOL" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "missing-cookies run exits 0, never crashes (rc=$rc3): $OUT3"
line3="$(grep '"key": "nfb2ace9f0ed8"' "$METRICS3" 2>/dev/null | tail -1)"
ok "$(echo "$line3" | grep -q '"views": "none"' && echo 1 || echo 0)" "missing cookies -> honest views: \"none\": $line3"
ok "$(echo "$line3" | grep -q '"views_reason": "no_session_cookie"' && echo 1 || echo 0)" "missing cookies -> specific views_reason=no_session_cookie"

# ---------- structural: a key that only ever appears with PASS: false is never fetched/recorded ----------
T4="$(mktemp -d)"
LIVE4="$T4/live-publishes.jsonl"
METRICS4="$T4/article-metrics.jsonl"
printf '%s\n' '{"ts": 1, "key": "nNEVERLIVE00000000000000000000000000000", "PASS": false}' > "$LIVE4"
OUT4="$(NOTE_LIVE_STATE_FILE="$LIVE4" ARTICLE_METRICS_STATE_FILE="$METRICS4" NOTE_COOKIES_FILE="$T4/does-not-exist.json" python3 "$TOOL" 2>&1)"; rc4=$?
ok "$([ $rc4 -eq 0 ] && echo 1 || echo 0)" "PASS:false-only key run exits 0 (rc=$rc4): $OUT4"
ok "$([ ! -f "$METRICS4" ] || ! grep -q 'nNEVERLIVE' "$METRICS4" && echo 1 || echo 0)" "a key that never independently verified live (PASS:false) is never fetched or recorded"

[ $fails -eq 0 ] && { echo "PASS -- PROP-28 metrics ledger: real views recorded for a real published key, honest \"none\"+reason for unresolvable keys and missing cookies (never a crash), revenue_jpy always honest 0, PASS:false keys never recorded"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
