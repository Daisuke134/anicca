#!/usr/bin/env bash
# gig_pass.sh's B2 wedge-retry kickstart -k's the shared ai.anicca.hf-gig-browser without
# coordinating with reply-detector/auditor (spec Sec-ES'). It must drop a restart-intent
# file BEFORE the kickstart so those consumers can defer. This runs the REAL 3-line
# snippet lifted from gig_pass.sh (not a re-implementation).
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
FILE="$ROOT/gig_pass.sh"

# 1. Source-text pin: the intent write happens before the kickstart line.
BEFORE=$(grep -n 'restart_intent_file=' "$FILE" | head -1 | cut -d: -f1)
KICK=$(grep -n 'launchctl kickstart -k "gui/\$(id -u)/\${CLOAK_BROWSER_LAUNCHD_LABEL' "$FILE" | head -1 | cut -d: -f1)
[ -n "$BEFORE" ] || { echo 'FAIL: no restart_intent_file write found'; exit 1; }
[ -n "$KICK" ] || { echo 'FAIL: no kickstart -k found'; exit 1; }
[ "$BEFORE" -lt "$KICK" ] || { echo 'FAIL: intent file is not written before the kickstart'; exit 1; }

# 1b. P3 bridge safety: the operator brake must be checked before the global
#     lock and intent. The lock is the legacy shared browser lock, not the
#     lane-specific Hermes lock inherited by this child.
BRAKE_SOURCE=$(grep -n 'source "\$G/scripts/gig_brake.sh"' "$FILE" | head -1 | cut -d: -f1)
BRAKE=$(grep -n 'gig_brake_is_held' "$FILE" | head -1 | cut -d: -f1)
LOCK_SOURCE=$(grep -n 'source "\$G/scripts/cdp_lock.sh"' "$FILE" | head -1 | cut -d: -f1)
LOCK=$(grep -n 'cdp_lock_acquire "gig-pass-B2-browser-restart"' "$FILE" | head -1 | cut -d: -f1)
LOCK_PATH=$(grep -n 'CDP_LOCK_DIR="\$HOME/gig/.cdp-gig.lock"' "$FILE" | head -1 | cut -d: -f1)
[ -n "$BRAKE_SOURCE" ] || { echo 'FAIL: B2 recovery does not source the operator brake'; exit 1; }
[ -n "$BRAKE" ] || { echo 'FAIL: B2 recovery does not evaluate the operator brake'; exit 1; }
[ -n "$LOCK_SOURCE" ] || { echo 'FAIL: B2 recovery does not source the existing cdp_lock.sh'; exit 1; }
[ -n "$LOCK" ] || { echo 'FAIL: B2 recovery does not acquire the global CDP lock'; exit 1; }
[ -n "$LOCK_PATH" ] || { echo 'FAIL: B2 recovery does not pin the legacy global CDP lock path'; exit 1; }
[ "$BRAKE_SOURCE" -lt "$BRAKE" ] || { echo 'FAIL: operator brake source follows its predicate'; exit 1; }
[ "$BRAKE" -lt "$LOCK" ] || { echo 'FAIL: operator brake is evaluated after global lock acquisition'; exit 1; }
[ "$LOCK_PATH" -le "$LOCK" ] || { echo 'FAIL: global CDP lock path is assigned after acquisition'; exit 1; }
[ "$LOCK" -lt "$BEFORE" ] || { echo 'FAIL: global CDP lock is acquired after restart intent'; exit 1; }

# 1c. A busy global lock must defer visibly and release only after the existing
#     readiness + settle sequence. Direct cdp_lock.sh reuse avoids the wrapper's
#     GIG_CDP_LOCK_HELD=1 nested-lock bypass.
grep -q 'browser restart deferred.*global CDP lock busy' "$FILE" \
  || { echo 'FAIL: global CDP lock contention is not an explicit defer/log path'; exit 1; }
SETTLE=$(grep -n '[[:space:]]sleep 4$' "$FILE" | head -1 | cut -d: -f1)
RELEASE=$(grep -n 'cdp_lock_release' "$FILE" | head -1 | cut -d: -f1)
[ -n "$SETTLE" ] || { echo 'FAIL: existing browser settle sleep is missing'; exit 1; }
[ -n "$RELEASE" ] || { echo 'FAIL: B2 recovery does not release the global CDP lock'; exit 1; }
[ "$SETTLE" -lt "$RELEASE" ] || { echo 'FAIL: global CDP lock releases before settle completes'; exit 1; }

# 1d. Functional failure injection: a busy global lock must not write intent or
#     invoke launchctl -k. Execute the real bridge block with only its existing
#     shell helpers replaced by deterministic test doubles.
BRIDGE_START=$(grep -n '# P3 BRIDGE SAFETY: BEGIN' "$FILE" | head -1 | cut -d: -f1)
BRIDGE_END=$(grep -n '# P3 BRIDGE SAFETY: END' "$FILE" | head -1 | cut -d: -f1)
[ -n "$BRIDGE_START" ] && [ -n "$BRIDGE_END" ] && [ "$BRIDGE_START" -lt "$BRIDGE_END" ] \
  || { echo 'FAIL: B2 safety bridge block markers are missing'; exit 1; }
TMP_BUSY=$(mktemp -d)
trap 'rm -rf "$TMP_BUSY" "$TMP"' EXIT
mkdir -p "$TMP_BUSY/g/scripts" "$TMP_BUSY/b" "$TMP_BUSY/bin"
EVENTS="$TMP_BUSY/events.log"
cat > "$TMP_BUSY/g/scripts/gig_brake.sh" <<'EOF'
gig_brake_is_held() { return 1; }
gig_brake_refuse() { printf 'brake-refused %s\n' "$1" >> "${TEST_EVENTS:?}"; }
gig_brake_describe() { printf 'test-brake'; }
EOF
cat > "$TMP_BUSY/g/scripts/cdp_lock.sh" <<'EOF'
cdp_lock_acquire() {
  printf 'lock-attempt %s %s %s\n' "$1" "$2" "${CDP_LOCK_DIR:?}" >> "${TEST_EVENTS:?}"
  return 1
}
cdp_lock_release() { printf 'lock-release\n' >> "${TEST_EVENTS:?}"; }
EOF
cat > "$TMP_BUSY/bin/launchctl" <<'EOF'
printf 'launchctl %s\n' "$*" >> "${TEST_EVENTS:?}"
EOF
chmod +x "$TMP_BUSY/bin/launchctl"
{
  printf '%s\n' 'log() { printf "log %s\\n" "$*" >> "${TEST_EVENTS:?}"; }'
  sed -n "$BRIDGE_START,$BRIDGE_END p" "$FILE"
} > "$TMP_BUSY/bridge.sh"
set +e
PATH="$TMP_BUSY/bin:$PATH" HOME="$TMP_BUSY/home" G="$TMP_BUSY/g" B="$TMP_BUSY/b" \
  TEST_EVENTS="$EVENTS" GIG_CDP_LOCK_HELD=1 GIG_BROWSER_RESTART_INTENT_FILE="$TMP_BUSY/intent.json" \
  GIG_LEASE=test-lease b2_browser_retry_ok=0 bash "$TMP_BUSY/bridge.sh"
BUSY_RC=$?
set -e
[ "$BUSY_RC" -eq 0 ] || { echo "FAIL: busy-lock bridge fixture exited rc=$BUSY_RC"; exit 1; }
grep -q '^lock-attempt .*\.cdp-gig\.lock$' "$EVENTS" \
  || { echo 'FAIL: busy-lock fixture did not attempt the legacy global lock'; exit 1; }
! grep -q '^launchctl ' "$EVENTS" \
  || { echo 'FAIL: busy-lock fixture invoked launchctl despite contention'; exit 1; }
[ ! -e "$TMP_BUSY/intent.json" ] \
  || { echo 'FAIL: busy-lock fixture wrote restart intent despite contention'; exit 1; }

# 2. Functional: the extracted write snippet actually produces a readable, fresh intent file.
SNIPPET=$(sed -n "${BEFORE},$((BEFORE + 3))p" "$FILE")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
NOW_BEFORE=$(date +%s)
(cd "$TMP" && HOME="$TMP" bash -c "$SNIPPET")
NOW_AFTER=$(date +%s)

OUT="$TMP/.openclaw/state/gig-browser-restart-intent.json"
[ -f "$OUT" ] || { echo "FAIL: intent file not created at $OUT"; exit 1; }
TS=$(python3 -c "import json;print(json.load(open('$OUT'))['ts'])" 2>/dev/null) || { echo 'FAIL: intent file is not valid JSON with a ts field'; exit 1; }
[ "$TS" -ge "$NOW_BEFORE" ] && [ "$TS" -le "$NOW_AFTER" ] || { echo "FAIL: ts=$TS not within [$NOW_BEFORE,$NOW_AFTER]"; exit 1; }
REASON=$(python3 -c "import json;print(json.load(open('$OUT'))['reason'])")
[ "$REASON" = "cdp_browser_wedged" ] || { echo "FAIL: unexpected reason=$REASON"; exit 1; }

echo 'PASS: B2 wedge-retry writes a fresh restart-intent file before kickstart -k'
