#!/usr/bin/env bash
# VSDD oracle — PROP-15 (REQ-14): after 3 consecutive V0/V0.5 FAILs the wake ABORTS with no publish AND
# records the failure.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"
OUT="$(ARTICLE_TEST=1 ARTICLE_DIR="$T" AUTONOMY=on ARTICLE_TEST_TOPIC="AI agents" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS,PASS,PASS" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "3-round-fail wake completes (abort is a legitimate outcome), rc=0 (rc=$rc): $OUT"
ok "$(grep -q 'last_wake_result: ABORTED' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "3-round-fail -> STATE result ABORTED"
ok "$(grep -q 'rounds_used: 3' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "abort happened after exactly 3 rounds (ceiling), not sooner/later"
ok "$([ ! -f "$T/state/PUBLISHED" ] && echo 1 || echo 0)" "ABORTED -> no publish sentinel, ever"
ok "$([ -f "$T/state/failures.jsonl" ] && grep -q 'AI agents' "$T/state/failures.jsonl" 2>/dev/null && echo 1 || echo 0)" "a failure entry was recorded to state/failures.jsonl"

# ---------------------------------------------------------------------------------------------------------
# contract-review FIND-003: a topic containing a doublequote + embedded newline must still yield a valid,
# parseable, single-line JSONL entry — not corrupt the ledger (run.sh's json_escape fix).
# ---------------------------------------------------------------------------------------------------------
T2="$(mktemp -d)"
HOSTILE_TOPIC='a "quoted" topic
with an embedded newline'
OUT2="$(ARTICLE_TEST=1 ARTICLE_DIR="$T2" AUTONOMY=on ARTICLE_TEST_TOPIC="$HOSTILE_TOPIC" ARTICLE_TEST_RESEARCH=sufficient \
  ARTICLE_TEST_V0_RESULTS="PASS,PASS,PASS" ARTICLE_TEST_V05_RESULTS="FAIL,FAIL,FAIL" bash "$SKILL/run.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "hostile-topic (quote+newline) 3-round-fail wake still completes, rc=0 (rc=$rc2): $OUT2"
jsonl_line_count="$(wc -l < "$T2/state/failures.jsonl" 2>/dev/null | tr -d ' ')"
ok "$([ "${jsonl_line_count:-0}" = 1 ] && echo 1 || echo 0)" "hostile-topic failure entry is EXACTLY one physical line in failures.jsonl (no raw embedded newline broke the JSONL contract), got $jsonl_line_count lines"
if command -v python3 >/dev/null 2>&1; then
  parsed_ok="$(python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as f:
        line = f.readline()
    obj = json.loads(line)
    print(1 if obj.get("topic", "").startswith("a \"quoted\" topic") else 0)
except Exception:
    print(0)
' "$T2/state/failures.jsonl")"
  ok "$parsed_ok" "hostile-topic failure entry parses as valid JSON via python3 json.loads, topic value round-trips correctly"
fi

[ $fails -eq 0 ] && { echo "PASS — PROP-15 3-round abort, no publish, failure recorded"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
