#!/usr/bin/env bash
# REQ-102/REQ-103: clip-cli.sh's STARTUP prompt (claude-p's own onboarding instructions) must tell
# the agent to self-provision a new IG account via ig-account-create when no ready account exists
# (closing the real gap found this session: neither loop was ever told this action exists), AND
# must instruct a validation step before retrying run.sh (closing the real 9222-default danger in
# run.sh:50's `x.get("port",9222)`).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAIL=0

STARTUP_TEXT="$(grep '^STARTUP=' "$DIR/clip-cli.sh")"

check() {
  local pattern="$1" label="$2"
  if echo "$STARTUP_TEXT" | grep -qi "$pattern"; then
    echo "PASS: STARTUP mentions $label"
  else
    echo "FAIL: STARTUP does NOT mention $label"
    FAIL=1
  fi
}

check "ig-account-create" "the ig-account-create skill by name"
check "ready_account=none\|no ready account\|ready account" "the no-ready-account condition"
check "port" "the account-file port field (for the validation instruction)"
check "9222" "the explicit 9222-collision warning"

if [ "$FAIL" = 0 ]; then
  echo "ALL PASS (clip-cli.sh STARTUP self-provisioning + validation instructions present)"
  exit 0
else
  echo "SOME CHECKS FAILED"
  exit 1
fi
