#!/usr/bin/env bash
# gates/v05.sh — V0.5 fixed binary craft checklist gate (REQ-5 a-e). PASS = ALL true, any single FALSE =>
# FAIL:
#   (a) opening hook states a reader pain / curiosity / concrete number
#   (b) a CTA to a paid rail is present
#   (c) the free part ends at a payoff cut (the How is withheld)
#   (d) the draft makes NO claim of having executed/run anything, and contains NO error-log/stack-trace text
#   (e) readability, mechanical: >= 70% of sentences are <= 60 characters (mobile-scannable)
#
# INTERFACE:
#   arg1:    path to the draft artifact to gate
#   env in:  ARTICLE_TEST_FORCE_V05=PASS|FAIL  (test-injection override; test mode only)
#   stdout:  "V05_RESULT: PASS" | "V05_RESULT: FAIL" plus one "V05_CRIT_<a..e>: true|false" line each
#   exit:    0 on PASS, 1 on FAIL (or on a genuine gate error)
#
# Phase 2b GREEN: when ARTICLE_TEST_FORCE_V05 is set, honor it verbatim (deterministic test seam — real
# deployment scores the draft with a fresh-context adversary against this same fixed checklist). Otherwise
# this gate runs the checklist mechanically against the draft file (criteria a-d as text/pattern checks,
# criterion e as a literal sentence-length computation — never a subjective judgment).
set -uo pipefail

DRAFT="${1:-}"

emit_forced() {
  local v="$1"
  echo "V05_CRIT_a: $v"; echo "V05_CRIT_b: $v"; echo "V05_CRIT_c: $v"; echo "V05_CRIT_d: $v"; echo "V05_CRIT_e: $v"
}

if [ -n "${ARTICLE_TEST_FORCE_V05:-}" ]; then
  if [ "$ARTICLE_TEST_FORCE_V05" = "PASS" ]; then
    emit_forced true
    echo "V05_RESULT: PASS"
    exit 0
  else
    emit_forced false
    echo "V05_RESULT: FAIL"
    exit 1
  fi
fi

if [ -z "$DRAFT" ] || [ ! -f "$DRAFT" ]; then
  echo "V05_RESULT: FAIL (no draft artifact at '$DRAFT')"
  exit 1
fi

body="$(cat "$DRAFT")"

# (a) opening hook: the first non-heading, non-empty paragraph contains a digit, a '?', or a curiosity/pain
# keyword.
hook_line="$(grep -vE '^[[:space:]]*$' "$DRAFT" | grep -vE '^#' | head -1)"
crit_a=false
if echo "$hook_line" | grep -qE '[0-9]|\?|secret|nobody|never|why|mistake|waste|pain' ; then
  crit_a=true
fi

# (b) a CTA to a paid rail is present.
crit_b=false
if echo "$body" | grep -qiE 'cta:|→|-> https?://|get the full|read the full|unlock the full'; then
  crit_b=true
fi

# (c) the free part ends at a payoff cut — a heading marking the withheld "How"/paid section.
crit_c=false
if echo "$body" | grep -qiE '^#+[[:space:]].*(how|paid|premium)'; then
  crit_c=true
fi

# (d) no claim of having executed/run anything; no error-log/stack-trace text (REQ-3's semantic check).
crit_d=true
if echo "$body" | grep -qiE 'i (ran|executed|cloned)|running the (repo|script|tool)|error-log:|stack trace'; then
  crit_d=false
fi

# (e) readability: >= 70% of sentences are <= 60 characters. Split on '.', '!', '?'; drop headings/blank
# lines/empty fragments.
plain="$(echo "$body" | grep -vE '^#' | grep -vE '^[[:space:]]*$')"
sentences="$(echo "$plain" | tr '.!?' '\n' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -vE '^$')"
total=0
short=0
while IFS= read -r s; do
  [ -z "$s" ] && continue
  total=$((total+1))
  len=${#s}
  if [ "$len" -le 60 ]; then short=$((short+1)); fi
done <<EOF
$sentences
EOF
crit_e=false
if [ "$total" -gt 0 ]; then
  pct=$(( short * 100 / total ))
  if [ "$pct" -ge 70 ]; then crit_e=true; fi
fi

echo "V05_CRIT_a: $crit_a"
echo "V05_CRIT_b: $crit_b"
echo "V05_CRIT_c: $crit_c"
echo "V05_CRIT_d: $crit_d"
echo "V05_CRIT_e: $crit_e"

if [ "$crit_a" = true ] && [ "$crit_b" = true ] && [ "$crit_c" = true ] && [ "$crit_d" = true ] && [ "$crit_e" = true ]; then
  echo "V05_RESULT: PASS"
  exit 0
fi

echo "V05_RESULT: FAIL"
exit 1
