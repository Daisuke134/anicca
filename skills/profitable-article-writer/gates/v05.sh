#!/usr/bin/env bash
# gates/v05.sh — V0.5 fixed binary craft checklist gate (REQ-5 a-e). PASS = ALL true, any single FALSE =>
# FAIL:
#   (a) opening hook states a reader pain / curiosity / concrete number
#   (b) a CTA to a paid rail is present
#   (c) the free part ends at a payoff cut (the How is withheld)
#   (d) the draft makes NO claim of having executed/run anything, and contains NO error-log/stack-trace text
#   (e) readability, mechanical: >= 70% of sentences are <= 60 characters (mobile-scannable)
#
# JUDGMENT SPLIT (verification-architecture.md purity boundary map + PROP-3: "judged by the running model,
# NOT hardcoded regex"):
#   (a)-(d) = AGENT JUDGMENT. This script NEVER decides them itself via grep/keyword-list — that is
#             exactly the anti-pattern building-effective-ai-agents.md forbids ("brittle hardcoded
#             if-else/regex standing in for a model decision"). Instead this script is a THIN tool: it
#             emits a structured judgment-request artifact (the draft + the 4 binary questions) for the
#             RUNNING AGENT to read and answer in natural language, then reads the agent's verdict back
#             from a documented response hook (env `ARTICLE_JUDGE_V05_RESPONSE`, see below). Sprint 1 does
#             not wire a LIVE judge_v05 call yet (same seam pattern as run.sh's real topic-pick) — so a
#             real run with no response present fails CLOSED to false/FAIL, never silently assumes PASS.
#   (e)     = genuine MECHANICAL PARSING of a fixed, objective metric (sentence-length %) — arithmetic, not
#             judgment — so it stays a deterministic computation, exactly as REQ-5(e) specifies.
#
# INTERFACE:
#   arg1:    path to the draft artifact to gate
#   env in:  ARTICLE_TEST_FORCE_V05=PASS|FAIL          (test-injection override; deterministic test mode
#                                                        only — see tests/, exercises the WIRING, not the
#                                                        real judged/arithmetic logic below)
#   env in:  ARTICLE_JUDGE_V05_RESPONSE=<path>          (judge_v05 HOOK, real/non-test path only) — the
#                                                        RUNNING AGENT writes its (a)-(d) verdict to this
#                                                        file, in the same "V05_CRIT_<a..d>: true|false"
#                                                        line format this script itself prints, after
#                                                        reading the judgment-request artifact this script
#                                                        emits at "<draft>.v05-judgment-request.txt". Not
#                                                        set / file missing => fail-closed (a)-(d)=false.
#   stdout:  "V05_RESULT: PASS" | "V05_RESULT: FAIL" plus one "V05_CRIT_<a..e>: true|false" line each
#   exit:    0 on PASS, 1 on FAIL (or on a genuine gate error)
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

# ---------------------------------------------------------------------------------------------------------
# (a)-(d) AGENT JUDGMENT — this script is a THIN tool: emit a structured judgment-request artifact, then
# read the running agent's verdict back from the documented judge_v05 hook. It NEVER decides (a)-(d) via
# grep/keyword-list itself.
# ---------------------------------------------------------------------------------------------------------
judge_request="${DRAFT}.v05-judgment-request.txt"
cat > "$judge_request" <<EOF
V05_JUDGMENT_REQUEST (judge_v05 hook — REQ-5 a-d, agent judgment, NOT a keyword/regex check)

Answer these 4 binary craft-checklist questions about the DRAFT below in natural language, then write your
verdict as exactly 4 lines (this same "V05_CRIT_<letter>: true|false" format) to a response file, and set
ARTICLE_JUDGE_V05_RESPONSE to that file's path before this gate is (re-)run:
  V05_CRIT_a: true|false   -- does the opening hook state a reader pain / curiosity / concrete number?
  V05_CRIT_b: true|false   -- is a CTA to a paid rail present?
  V05_CRIT_c: true|false   -- does the free part end at a payoff cut (the How withheld)?
  V05_CRIT_d: true|false   -- does the draft AVOID any claim of having executed/run anything, and contain
                              NO error-log/stack-trace text?

--- DRAFT ($DRAFT) ---
$body
--- END DRAFT ---
EOF

crit_a=false
crit_b=false
crit_c=false
crit_d=false
if [ -n "${ARTICLE_JUDGE_V05_RESPONSE:-}" ] && [ -f "$ARTICLE_JUDGE_V05_RESPONSE" ]; then
  # Parse the running agent's own already-produced verdict back (structured parsing of the agent's answer,
  # not a judgment made by this script).
  resp="$(cat "$ARTICLE_JUDGE_V05_RESPONSE")"
  echo "$resp" | grep -qE '^V05_CRIT_a: true$' && crit_a=true
  echo "$resp" | grep -qE '^V05_CRIT_b: true$' && crit_b=true
  echo "$resp" | grep -qE '^V05_CRIT_c: true$' && crit_c=true
  echo "$resp" | grep -qE '^V05_CRIT_d: true$' && crit_d=true
fi
# Sprint 1 wires no live judge_v05 call yet (Sprint 2 integration seam, same as run.sh's real topic-pick
# seam) — ARTICLE_JUDGE_V05_RESPONSE unset/missing => (a)-(d) stay fail-closed false above.

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
