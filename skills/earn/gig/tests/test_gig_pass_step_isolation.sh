#!/usr/bin/env bash
# Rung 3 of the pass-health ladder, as the pass itself sees it.
#
# A step that has failed three times running is taken out so the other lanes keep
# earning instead of dying with it. The gate that does that is the only place a
# bug could silence a revenue lane, so it is pinned here: it skips exactly the
# isolated step, it lets the window lapse, and it fails OPEN on every kind of
# broken input.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-step-isolation.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# Pull the two functions out of the driver rather than sourcing it: gig_pass.sh
# re-execs into the worker launcher on line one.
extract() {
  sed -n "/^$1() {/,/^}$/p" "$SKILL_DIR/gig_pass.sh"
}
HARNESS="$TMP/harness.sh"
{
  printf 'set -euo pipefail\n'
  printf 'STEP_ISOLATION_STORE="%s"\n' "$TMP/step-isolation.json"
  printf 'step_cooldown_now() { printf "%%s\\n" "${GIG_STEP_COOLDOWN_NOW:-0}"; }\n'
  extract step_is_isolated
} > "$HARNESS"

grep -q 'step_is_isolated' "$HARNESS" || { echo 'step_is_isolated was not extracted'; exit 1; }

ask() {  # ask <label> <now>  -> prints "isolated" or "open"
  if GIG_STEP_COOLDOWN_NOW="$2" bash -c ". '$HARNESS'; step_is_isolated '$1'"; then
    printf 'isolated\n'
  else
    printf 'open\n'
  fi
}

expect() {  # expect <what> <got> <message>
  [ "$1" = "$2" ] || { echo "FAIL: $3 (expected $1, got $2)"; exit 1; }
}

STORE="$TMP/step-isolation.json"

# 1. No store at all: nothing is isolated. This is the state of every healthy
#    host, so it must be the cheapest and safest answer.
expect open "$(ask B2 1000)" 'a missing store must isolate nothing'

# 2. An isolated step is skipped, and only that step.
printf '{"version":1,"steps":{"B2":{"until":2000,"reason":"r","consecutive":3,"since":1000}}}\n' > "$STORE"
expect isolated "$(ask B2 1000)" 'the isolated step must be skipped'
expect open "$(ask PAID_WORK 1000)" 'the other lanes must keep running'

# 3. The window lapses on its own, so an isolation can never outlive its defect
#    even if nothing ever comes back to lift it.
expect open "$(ask B2 2000)" 'isolation must expire at its own deadline'
expect open "$(ask B2 9999)" 'isolation must not resurrect after expiry'

# 4. Fail open on every shape of broken store. A bug here would reproduce the
#    outage this whole feature exists to end.
printf '{not json\n' > "$STORE"
expect open "$(ask B2 1000)" 'malformed JSON must isolate nothing'
printf '{"version":99,"steps":{"B2":{"until":9999}}}\n' > "$STORE"
expect open "$(ask B2 1000)" 'an unknown store version must isolate nothing'
printf '{"version":1,"steps":{"B2":{"until":"soon"}}}\n' > "$STORE"
expect open "$(ask B2 1000)" 'a non-numeric deadline must isolate nothing'
printf '{"version":1,"steps":[]}\n' > "$STORE"
expect open "$(ask B2 1000)" 'a wrong-typed steps field must isolate nothing'
: > "$STORE"
expect open "$(ask B2 1000)" 'an empty store must isolate nothing'

# 5. The gate is wired ahead of the cooldown gate at the single step-skip site,
#    and it never touches the pass's exit code -- it returns 0 like every other
#    skip.
grep -q 'if step_is_isolated "$label"; then' "$SKILL_DIR/gig_pass.sh" \
  || { echo 'FAIL: the isolation gate is not wired into the step dispatcher'; exit 1; }
grep -A3 'if step_is_isolated "$label"; then' "$SKILL_DIR/gig_pass.sh" \
  | grep -q 'return 0' \
  || { echo 'FAIL: an isolated step must skip, never fail the pass'; exit 1; }

echo 'PASS: step isolation skips only the isolated step, expires, and fails open'
