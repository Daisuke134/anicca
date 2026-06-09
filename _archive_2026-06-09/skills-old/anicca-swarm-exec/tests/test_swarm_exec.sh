#!/usr/bin/env bash
# E2E (offline): build a local file:// mock repo, run swarm-exec.sh against it with an
# `echo:hello` runner, assert a ledger row with exit_code=0, then prove the clone dir is gone
# (cleanup) and that an unknown task_id fails-closed with exit_code=65.
#
# Fully offline: the "peer repo" is a local git repo we create here. The size gate is bypassed
# for file:// URLs (see SWARM_SKIP_SIZE_GATE) so no `gh` network call is needed.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")/../scripts" && pwd)"
JQ=/usr/bin/jq

pass=0; fail=0
ok()  { echo "PASS: $1"; pass=$((pass+1)); }
bad() { echo "FAIL: $1"; fail=$((fail+1)); }

# Isolated state + clone cache (never touch the live ~/.hermes or ~/.cache).
export STATE_DIR; STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/swarm-e2e-state-XXXX")"
export SWARM_CLONE_ROOT; SWARM_CLONE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/swarm-e2e-clones-XXXX")"
export SWARM_SKIP_SIZE_GATE=1   # offline: skip the gh repo-view network call
MOCK="$(mktemp -d "${TMPDIR:-/tmp}/swarm-e2e-mockrepo-XXXX")"

cleanup() { rm -rf "$STATE_DIR" "$SWARM_CLONE_ROOT" "$MOCK" 2>/dev/null || true; }
trap cleanup EXIT

# ---- Build a local mock peer repo (git init + one commit on branch `feat/mock`).
(
  cd "$MOCK"
  git init -q -b main
  git config user.email t@t.t; git config user.name t
  echo "hello world" > README.md
  git add -A; git commit -qm "init"
  git checkout -q -b feat/mock
  echo "branch work" >> README.md
  git add -A; git commit -qm "work"
) || { bad "could not build mock repo"; echo "RESULT: $pass passed, $fail failed"; exit 1; }

LEDGER="$STATE_DIR/swarm-exec.jsonl"

# ---- 1. Run swarm-exec with echo:hello runner against the mock repo's feat/mock branch.
bash "$SCRIPTS/swarm-exec.sh" "file://$MOCK" "feat/mock" "echo:hello" >/dev/null 2>&1 || true

if [ -s "$LEDGER" ] && \
   "$JQ" -e 'select(.task_id=="echo:hello" and .exit_code==0)' "$LEDGER" >/dev/null 2>&1; then
  ok "ledger has echo:hello row with exit_code=0"
else
  bad "no exit_code=0 echo:hello ledger row"
  echo "--- ledger ---"; cat "$LEDGER" 2>/dev/null
fi

# ---- 2. Row records the branch.
if "$JQ" -e 'select(.task_id=="echo:hello" and .branch=="feat/mock")' "$LEDGER" >/dev/null 2>&1; then
  ok "ledger row records branch feat/mock"
else
  bad "ledger row branch mismatch"
fi

# ---- 3. Clone dir cleaned up (HARD RULE: no /tmp clone, removed on exit).
if [ -z "$(ls -A "$SWARM_CLONE_ROOT" 2>/dev/null)" ]; then
  ok "clone root is empty after run (cleanup proven)"
else
  bad "clone root NOT cleaned: $(ls -A "$SWARM_CLONE_ROOT")"
fi

# ---- 4. Unknown task_id fails closed (exit_code=65).
bash "$SCRIPTS/swarm-exec.sh" "file://$MOCK" "feat/mock" "bogus-task" >/dev/null 2>&1 || true
if "$JQ" -e 'select(.task_id=="bogus-task" and .exit_code==65)' "$LEDGER" >/dev/null 2>&1; then
  ok "unknown task_id logged exit_code=65 (fail-closed)"
else
  bad "unknown task_id did not log exit_code=65"
  echo "--- ledger ---"; cat "$LEDGER" 2>/dev/null
fi

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
