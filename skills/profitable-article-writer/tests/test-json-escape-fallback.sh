#!/usr/bin/env bash
# VSDD oracle — Phase-3 FIND-006: run.sh's json_escape() has a sed-fallback branch (used when python3 is
# absent) that no test exercised. run.sh honors ARTICLE_FORCE_SED_ESCAPE=1 to force that branch. This test
# drives the real 3-round-abort path with a hostile topic (quote + embedded newline) AND the sed fallback
# forced, asserting the failures.jsonl entry is still exactly one valid, parseable JSONL line.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"
HOSTILE_TOPIC='a "quoted" topic
with an embedded newline and a \backslash'
OUT="$(ARTICLE_FORCE_SED_ESCAPE=1 ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="$HOSTILE_TOPIC" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS,PASS,PASS" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "sed-fallback + hostile topic: wake completes rc=0 (rc=$rc): $OUT"
lines="$(wc -l < "$T/state/failures.jsonl" 2>/dev/null | tr -d ' ')"
ok "$([ "${lines:-0}" = 1 ] && echo 1 || echo 0)" "sed-fallback: failure entry is EXACTLY one physical line (got ${lines:-0})"
# Validate the sed-escaped line is real JSON (parse it; the sed branch produced the escaping, not python's json.dumps)
if command -v python3 >/dev/null 2>&1; then
  parsed="$(python3 -c '
import json, sys
try:
    line = open(sys.argv[1]).readline()
    obj = json.loads(line)
    t = obj.get("topic","")
    print(1 if (t.startswith("a \"quoted\" topic") and "\n" in t and "\\backslash" in t) else 0)
except Exception as e:
    print(0)
' "$T/state/failures.jsonl")"
  ok "$parsed" "sed-fallback: entry parses as valid JSON and the topic (quote+newline+backslash) round-trips"
fi

[ $fails -eq 0 ] && { echo "PASS — json_escape sed-fallback branch produces valid JSONL (FIND-006)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
