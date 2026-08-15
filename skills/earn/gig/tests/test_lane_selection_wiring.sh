#!/usr/bin/env bash
# X4b: the selection wiring, exercised against the real lane_health binary.
#
# The unit tests prove select() cannot starve a lane. These prove the shell around it
# does the same thing -- that a pass drives every due lane, that the not-due lanes are
# recorded as policy skips rather than failures, and that a lane which fails still
# yields the next pass. That last one is the regression that would rebuild the outage:
# a lane whose clock never advances wins selection forever.
#
# X18 (2026-07-27): "exactly one lane per pass" used to be asserted here. It was never a
# requirement -- it was GIG_MODEL_CALL_LIMIT=1 showing through, which was itself the
# one-shared-browser-tab constraint showing through. Measured occupancy was 1.3%, so the
# pass now drives every DUE lane. Still demand-driven: a lane that is not past its
# deadline is not run, which is why widening the pass does not widen the day.
set -uo pipefail

G="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LH="$G/scripts/lane_health.py"
fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}

fresh_state() { GIG_STATE_DIR="$(mktemp -d)"; export GIG_STATE_DIR; }

selected_step() { python3 "$LH" select 2>/dev/null; }
selected_lane() {
  python3 "$LH" select --json 2>/dev/null \
    | python3 -c 'import json,sys; v=json.load(sys.stdin).get("selected") or {}; print(v.get("lane",""))'
}
# Mirrors the selection block in gig_pass.sh: every due step except PAID_WORK (which the
# paid path drives on its own), in deadline order, capped by the model-call budget.
due_steps() { # limit -> space-separated step list
  python3 "$LH" select --json 2>/dev/null \
    | LIMIT="$1" python3 -c 'import json,os,sys
due=[r["step"] for r in (json.load(sys.stdin).get("due") or []) if r["step"]!="PAID_WORK"]
limit=int(os.environ["LIMIT"])
print(" ".join(due[:limit] if limit>0 else due))'
}

# Mirrors the case block in gig_pass.sh step().
would_run() { # selected_steps candidate_label -> run|skip
  local sel=" $1 " label="$2"
  case "$label" in
    LEARN|B0|PROFILE|B1|B2)
      [ "${sel#* $label }" != "$sel" ] && echo run || echo skip ;;
    *) echo run ;;
  esac
}

# --- every due lane step runs in one pass -------------------------------------
# The whole point of X18: on a cold start every lane is overdue, and the pass used to
# spend that waking on one of them. "Applied but never replied" was structural.
fresh_state
sel="$(due_steps 4)"
ran=0
for label in LEARN B0 PROFILE B1 B2; do
  [ "$(would_run "$sel" "$label")" = run ] && ran=$((ran+1))
done
check "every due lane step runs in one pass, up to the budget" 4 "$ran"

# --- the budget still truncates -----------------------------------------------
# The limit is not removed, only raised. A pass that somehow wants more calls than it is
# allowed is cut off at selection time, deterministically, instead of dying mid-pass on
# claim_model_call after the earlier lanes already did customer work.
fresh_state
check "the model-call budget caps how many lanes a pass takes" 2 \
  "$(due_steps 2 | wc -w | tr -d ' ')"
check "a lane outside the budget is skipped, not run" skip "$(would_run "$(due_steps 1)" B0)"

# --- 返信 is never the one that gets cut --------------------------------------
# spec 0.3 orders Reply/Nouhin > Oubo > Shuppin. Deadline still decides; priority only
# breaks ties. Cold start is all-tied, so this is exactly where a bad tie-break would
# drop 返信 off the end of the budget.
fresh_state
check "with everything tied, 返信 is inside even a budget of one" run \
  "$(would_run "$(due_steps 1)" B1)"
fresh_state
revenue_steps="$(due_steps 4)"
check "hourly budget always includes listing" run "$(would_run "$revenue_steps" B0)"
check "hourly budget always includes reply" run "$(would_run "$revenue_steps" B1)"
check "hourly budget always includes apply" run "$(would_run "$revenue_steps" B2)"

# --- nothing due means nothing runs -------------------------------------------
fresh_state
for lane in apply reply fulfill list profile improve; do
  python3 "$LH" record "$lane" success --records 1 >/dev/null
done
check "no due lane means no lane step runs" 0 "$(due_steps 4 | wc -w | tr -d ' ')"

# --- the losers are skipped, never failed -------------------------------------
check "a non-due lane is skipped, not run" skip "$(would_run B2 B0)"
check "a due lane runs" run "$(would_run B2 B2)"

# --- a failing lane still yields the next pass --------------------------------
# The deadline clock is the attempt. If it were the success, this lane would stay the
# most overdue forever and every pass would go to it.
fresh_state
first="$(selected_lane)"
python3 "$LH" record "$first" failure >/dev/null
second="$(selected_lane)"
check "a lane that failed does not win the next pass again" different \
  "$([ "$first" != "$second" ] && echo different || echo "same:$first")"

# --- delivery cannot monopolise ------------------------------------------------
# The measured outage shape: delivery eligible on nearly every pass.
fresh_state
for _ in $(seq 1 40); do python3 "$LH" record fulfill success --records 1 >/dev/null; done
check "40 delivery runs cannot keep delivery selected" yes \
  "$([ "$(selected_lane)" != fulfill ] && echo yes || echo no)"

# --- every lane is reachable within one cycle ----------------------------------
fresh_state
seen=""
for _ in 1 2 3 4 5 6; do
  lane="$(selected_lane)"
  seen="$seen $lane"
  python3 "$LH" record "$lane" success --records 1 >/dev/null
done
distinct="$(printf '%s\n' $seen | sort -u | wc -l | tr -d ' ')"
check "all six lanes are driven within one cycle" 6 "$distinct"

# --- nothing is forced to run when every lane is fresh -------------------------
python3 "$LH" select >/dev/null 2>&1
check "with every lane fresh the selector reports nothing due" 3 "$?"

# --- the pass script still parses ----------------------------------------------
bash -n "$G/gig_pass.sh"
check "gig_pass.sh parses" 0 "$?"

# --- helpers are defined before they are called ---------------------------------
# bash -n does not catch this: record_lane_attempt was defined 100 lines below the
# selector that calls it, so the call became "command not found" at runtime and the
# lane clock silently never advanced. Only a live pass revealed it.
for fn in record_lane_attempt; do
  def_line="$(grep -n "^${fn}()" "$G/gig_pass.sh" | head -1 | cut -d: -f1)"
  first_call="$(grep -n "[^a-z_]${fn} \|^  *${fn} " "$G/gig_pass.sh" \
    | grep -v "^${def_line}:" | grep -v "()" | head -1 | cut -d: -f1)"
  if [ -z "$first_call" ]; then
    check "$fn is called somewhere" nonempty empty
  else
    check "$fn is defined before its first call" yes \
      "$([ "$def_line" -lt "$first_call" ] && echo yes || echo "no(def=$def_line call=$first_call)")"
  fi
done

echo
[ "$fails" -gt 0 ] && { echo "$fails failed"; exit 1; }
echo "all lane selection wiring tests passed"
