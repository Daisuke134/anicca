#!/usr/bin/env bash
# X19 (2026-07-27): each lane's step prompt carries THAT lane's lessons and no other's.
#
# Measured before writing this: not one of the five lane prompts injected lessons at all.
# LEARN was merely told to "read lessons.jsonl" -- the whole 280-row pile, in which apply
# lessons and fulfil lessons were indistinguishable because no row carried a lane. So a
# lane could not learn from its own history even in principle, and LEARN's single extract
# had no lane to attribute the result to.
#
# The assertion that matters is the negative one: a lane must NOT see another lane's
# lessons. Injecting all of them into all of them would satisfy "lessons are in the
# prompt" while leaving the actual defect -- mixed skills -- exactly where it was.
set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-pass-lane-lessons.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" \
  "$HOME_DIR/profitable-claude/skills/agent-runner" "$HOME_DIR/gig"

cp "$SKILL_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SKILL_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
for script in delivery_queue delivery_cadence delivery_identity reply_queue \
              connector_outbox b1_conversation_gate b0_objective b0_result_gate b2_queue_gate \
              b2_result_gate lane_health lane_action_runtime lane_productivity lane_lessons \
              experiment_evaluator; do
  cp "$SKILL_DIR/scripts/$script.py" "$GIG_DIR/scripts/$script.py"
done
mkdir -p "$HOME_DIR/anicca/skills/browser/scripts"
printf '%s\n' '#!/usr/bin/env python3' > "$HOME_DIR/anicca/skills/browser/scripts/cdp_context_lease.py"
printf '%s\n' '#!/usr/bin/env python3' > "$GIG_DIR/scripts/cdp_nav_snapshot.py"
chmod +x "$HOME_DIR/anicca/skills/browser/scripts/cdp_context_lease.py" \
  "$GIG_DIR/scripts/cdp_nav_snapshot.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b0_result.schema.json" "$GIG_DIR/schemas/gig_b0_result.schema.json"
printf '%s\n' '{"captured_at":"2026-07-21T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"

# One lesson per lane, plus a legacy row with no lane at all -- the shape of all 280
# production rows. Markers are unique strings so a leak is unambiguous.
cat > "$HOME_DIR/gig/lessons.jsonl" <<'JSONL'
{"lane":"apply","ts":1,"category":"writing","outcome":"accepted","lesson":"MARKER_APPLY_LESSON"}
{"lane":"reply","ts":2,"category":"writing","outcome":"accepted","lesson":"MARKER_REPLY_LESSON"}
{"lane":"fulfill","ts":3,"category":"writing","outcome":"accepted","lesson":"MARKER_FULFILL_LESSON"}
{"lane":"list","ts":4,"category":"writing","outcome":"accepted","lesson":"MARKER_LIST_LESSON"}
{"lane":"profile","ts":5,"category":"writing","outcome":"accepted","lesson":"MARKER_PROFILE_LESSON"}
{"ts":6,"category":"writing","outcome":"accepted","lesson":"MARKER_LEGACY_UNATTRIBUTED"}
{"truncated append that production really has on line 242
JSONL

# The runner records who it was called as and then fails. Prompt files are written before
# the call, so every selected lane's prompt is on disk regardless of the outcome.
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import sys
raise SystemExit(42)
PY
chmod +x "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" "$GIG_DIR/gig_pass.sh"

EV="$TMP/evidence"
# Budget 5 so all five lane steps are selected and every prompt exists to inspect.
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/lock.d" GIG_EVIDENCE_DIR="$EV" GIG_MODEL_CALL_LIMIT=5 \
  bash "$GIG_DIR/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"

fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}
# grep -F -q on a file, never `grep | grep -q`: under pipefail a short-circuiting
# downstream grep kills the upstream one and the test reports 141 instead of a verdict.
has() { # file marker -> yes/no
  if [ -f "$1" ] && grep -Fq -- "$2" "$1"; then echo yes; else echo no; fi
}
prompt() { printf '%s/%s.prompt.txt' "$EV" "$1"; }

check "every selected lane wrote a prompt" yes \
  "$([ -f "$(prompt B2)" ] && [ -f "$(prompt B1)" ] && [ -f "$(prompt B0)" ] \
     && [ -f "$(prompt PROFILE)" ] && [ -f "$(prompt LEARN)" ] && echo yes \
     || echo "no(have=$(ls "$EV" 2>/dev/null | tr '\n' ',' ))")"

# --- each lane sees its own lessons ---
check "apply lane receives apply lessons"     yes "$(has "$(prompt B2)" MARKER_APPLY_LESSON)"
check "reply lane receives reply lessons"     yes "$(has "$(prompt B1)" MARKER_REPLY_LESSON)"
check "list lane receives list lessons"       yes "$(has "$(prompt B0)" MARKER_LIST_LESSON)"
check "profile lane receives profile lessons" yes "$(has "$(prompt PROFILE)" MARKER_PROFILE_LESSON)"

# --- and only its own: this is the whole point of the change ---
check "apply lane is not taught fulfil lessons" no "$(has "$(prompt B2)" MARKER_FULFILL_LESSON)"
check "apply lane is not taught reply lessons"  no "$(has "$(prompt B2)" MARKER_REPLY_LESSON)"
check "reply lane is not taught apply lessons"  no "$(has "$(prompt B1)" MARKER_APPLY_LESSON)"
check "list lane is not taught profile lessons" no "$(has "$(prompt B0)" MARKER_PROFILE_LESSON)"

# Unattributed history belongs to nobody. Handing it to every lane would rebuild the
# mixed pile inside each prompt while the file looked fixed.
for label in B2 B1 B0 PROFILE; do
  check "$label is not taught unattributed legacy lessons" no \
    "$(has "$(prompt "$label")" MARKER_LEGACY_UNATTRIBUTED)"
done

# --- a corrupt line does not stop any lane from getting its prompt ---
check "the corrupt production line does not break prompt building" yes \
  "$(has "$(prompt B2)" MARKER_APPLY_LESSON)"

# --- LEARN attributes what it writes, with no extra model call ---
check "LEARN is told which lanes this pass is about" yes \
  "$(has "$(prompt LEARN)" lanes_due_this_pass)"
check "LEARN must write through the lane-enforcing appender" yes \
  "$(has "$(prompt LEARN)" lane_lessons.py)"
check "LEARN is forbidden from guessing a lane" yes \
  "$(has "$(prompt LEARN)" "never guess")"

# --- shared knowledge stays shared: it must not migrate into the lessons window ---
# Browser etiquette is a prohibition on the agent, not a learned market fact, so it may
# not age out of a bounded recent-N window.
check "browser etiquette stays in the shared ownership contract" yes \
  "$(has "$(prompt B1)" "Never attach to, navigate, or close another worker's tab")"
check "ledger prohibitions stay in the shared ownership contract" yes \
  "$(has "$(prompt B2)" "Do not rewrite or truncate existing JSONL files")"

# --- the existing readers' file is untouched by prompt building ---
check "building prompts does not mutate lessons.jsonl" 7 \
  "$(wc -l < "$HOME_DIR/gig/lessons.jsonl" | tr -d ' ')"

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails failed"
  echo "--- stderr ---"; tail -30 "$TMP/err"
  exit 1
fi
echo "PASS: every lane learns from its own lane only, and LEARN attributes what it writes"
