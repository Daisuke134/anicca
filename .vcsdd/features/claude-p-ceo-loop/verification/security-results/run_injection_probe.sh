#!/usr/bin/env bash
# CEO_AGENT_DECISIONS_JSON injection / malformed-input probe against the REAL run_pass.py, in a
# scratch CEO_STATE_DIR (never touches ~/.anicca-founder/state/). Each scenario below runs run_pass.py
# as an actual subprocess (not mocked) and records exit code + stdout + stderr.
set -uo pipefail
CEO_DIR="$HOME/anicca/.worktrees/ceo-loop/skills/self/founder-loop/ceo"
SCRATCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_STATE="$SCRATCH/state"

run_scenario() {
  local name="$1"
  local decisions_content="$2"
  local state_dir="$SCRATCH/state-$name"
  rm -rf "$state_dir"
  mkdir -p "$state_dir"
  local decisions_file="$SCRATCH/decisions-$name.json"
  printf '%s' "$decisions_content" > "$decisions_file"

  echo "########################################################################"
  echo "### SCENARIO: $name"
  echo "### CEO_AGENT_DECISIONS_JSON content:"
  cat "$decisions_file"
  echo
  echo "### run_pass.py output:"
  CEO_STATE_DIR="$state_dir" CEO_AGENT_DECISIONS_JSON="$decisions_file" \
    python3 "$CEO_DIR/run_pass.py"
  local rc=$?
  echo "### EXIT CODE: $rc"
  echo
}

echo "=== BASELINE (no CEO_AGENT_DECISIONS_JSON at all, sanity check the harness itself works) ==="
rm -rf "$SCRATCH/state-baseline"; mkdir -p "$SCRATCH/state-baseline"
CEO_STATE_DIR="$SCRATCH/state-baseline" python3 "$CEO_DIR/run_pass.py"
echo "### EXIT CODE: $?"
echo

run_scenario "invalid-json-syntax" '{this is not valid json!!! }}}'

run_scenario "json-array-not-object" '[1, 2, 3]'

run_scenario "json-bare-string" '"just-a-string"'

run_scenario "decision-value-not-dict" '{"clip": "not-a-dict-decision"}'

run_scenario "huge-capital-cap" '{"clip": {"allocation": {"capital_cap_usd": 999999999999999}}, "justification": "huge cap test"}'

run_scenario "negative-fleet-size" '{"clip": {"allocation": {"fleet_size_target": -5}}}'

run_scenario "shell-metachar-in-justification" '{"clip": {"allocation": {"fleet_size_target": 2}, "justification": "$(rm -rf /tmp/pwned-marker-'"'"'; touch /tmp/pwned-marker-file'"'"'; echo done)"}}'
touch "$SCRATCH/pre-existing-marker" 2>/dev/null
echo "### checking whether /tmp/pwned-marker-file was created by the shell-metachar payload above:"
ls -la /tmp/pwned-marker-file 2>&1 || echo "NOT CREATED (no shell injection occurred, as expected: subprocess.run uses a list, not shell=True)"
echo

run_scenario "unknown-loop-name" '{"totally-not-a-real-loop-xyz": {"allocation": {"capital_cap_usd": 500}}}'

run_scenario "deeply-nested-huge-json" '{"clip": {"allocation": {"capital_cap_usd": 1e308, "pass_frequency_multiplier": 1e308}}}'

run_scenario "null-decisions-file-content" 'null'

run_scenario "empty-file" ''

echo "=== ALL SCENARIOS COMPLETE ==="
