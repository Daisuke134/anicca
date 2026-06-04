#!/usr/bin/env bash
# E2E: `run.sh --dry-run --offline-fixture <path>` MUST produce a JSON envelope on stdout
# with mode=dry-run and exactly 3 scored candidates, and MUST NOT touch the runs jsonl.

set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE="$SKILL_DIR/tests/fixtures/sample-snapshot.json"
STATE_DIR="${HERMES_STATE_DIR:-$HOME/.hermes/state}"
LOG="$STATE_DIR/earn-lancers-runs.jsonl"
DRY_LATEST="$STATE_DIR/earn-lancers-dry-run-latest.json"
JQ="${JQ:-/usr/bin/jq}"

# Capture log size before
mkdir -p "$STATE_DIR"
LOG_BEFORE=$(wc -c < "$LOG" 2>/dev/null || echo 0)

OUT=$("$SKILL_DIR/scripts/run.sh" --dry-run --offline-fixture "$FIXTURE")

# Assertion 1: stdout is valid JSON
echo "$OUT" | "$JQ" -e . >/dev/null || { echo "FAIL: stdout not JSON: $OUT"; exit 1; }

# Assertion 2: mode == "dry-run"
echo "$OUT" | "$JQ" -e '.mode == "dry-run"' >/dev/null || { echo "FAIL: mode != dry-run"; exit 1; }

# Assertion 3: exactly 3 candidates
N=$(echo "$OUT" | "$JQ" '.candidates | length')
[ "$N" -eq 3 ] || { echo "FAIL: expected 3 candidates, got $N"; exit 1; }

# Assertion 4: every candidate has the required keys
for k in jid url title_truncated budget_jpy effort_estimate score generated_message; do
  PRESENT=$(echo "$OUT" | "$JQ" "[.candidates[] | has(\"$k\")] | all")
  [ "$PRESENT" = "true" ] || { echo "FAIL: candidate missing key $k"; exit 1; }
done

# Assertion 5: candidates are sorted desc by score
SORTED=$(echo "$OUT" | "$JQ" '[.candidates[].score] == ([.candidates[].score] | sort | reverse)')
[ "$SORTED" = "true" ] || { echo "FAIL: candidates not sorted by score desc"; exit 1; }

# Assertion 6: runs log untouched (~/.hermes/state/earn-lancers-runs.jsonl)
LOG_AFTER=$(wc -c < "$LOG" 2>/dev/null || echo 0)
[ "$LOG_BEFORE" = "$LOG_AFTER" ] || { echo "FAIL: $LOG mutated (before=$LOG_BEFORE after=$LOG_AFTER)"; exit 1; }

# Assertion 7: ~/.hermes/state/earn-lancers-dry-run-latest.json written
test -s "$DRY_LATEST" || { echo "FAIL: $DRY_LATEST not written"; exit 1; }

# Assertion 8: NO call would hit the submit URL (grep the dry-run-latest for forbidden URL substring)
if "$JQ" -r '.candidates[] | .url' "$DRY_LATEST" | grep -q 'propose_finish'; then
  echo "FAIL: candidate URLs leaked propose_finish path (= submit-side URL)"; exit 1
fi

echo "PASS"
