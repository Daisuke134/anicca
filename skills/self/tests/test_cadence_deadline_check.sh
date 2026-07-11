#!/usr/bin/env bash
# test_cadence_deadline_check.sh — F-ITER3-1 fix regression test. Builds a fake SELF dir with a
# stub cadence-evidence.py (always reports met=false, no real ledger reads) and a stub self-fix.sh
# (records the call instead of spawning a real Opus fixer) so this test never spawns a real
# self-fix process. Proves: (a) the script no-ops before 21:00 JST (simulated via a fixed-hour
# stub — see below), (b) escalates exactly once per loop when called twice for the same JST day
# (marker-gate), (c) actually invokes self-fix.sh for an unmet loop.
set -uo pipefail
P=0; F=0
ok(){ echo "  ok $1"; P=$((P+1)); }
fail(){ echo "  FAIL $1"; F=$((F+1)); }

REAL_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/cadence-deadline-check.sh"

FAKE_SELF="$(mktemp -d)"
FAKE_HOME="$(mktemp -d)"
mkdir -p "$FAKE_HOME/.openclaw/state" "$FAKE_HOME/.openclaw/logs"

cat > "$FAKE_SELF/cadence-evidence.py" <<'PYEOF'
import json, sys
loop = sys.argv[2]
print(json.dumps({"loop": loop, "met": False, "streak": 0, "scorecard": "❌missed (streak=0)"}))
PYEOF

SELF_FIX_CALLS="$FAKE_HOME/.openclaw/state/self-fix-calls.log"
cat > "$FAKE_SELF/self-fix.sh" <<EOF
#!/usr/bin/env bash
echo "\$1" >> "$SELF_FIX_CALLS"
EOF
chmod +x "$FAKE_SELF/self-fix.sh"

cat > "$FAKE_SELF/cadence-contracts.json" <<'JSONEOF'
{}
JSONEOF

echo "--- run 0: before 21:00 JST (hour=14) -> no-op, zero escalations ---"
HOME="$FAKE_HOME" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF" CADENCE_DEADLINE_NOW_HOUR_JST=14 bash "$REAL_SCRIPT" >/dev/null 2>&1
CALLS_0=0
[ -f "$SELF_FIX_CALLS" ] && CALLS_0="$(wc -l < "$SELF_FIX_CALLS" | tr -d ' ')"
[ "$CALLS_0" = 0 ] && ok "run 0: before 21:00 JST -> no-op (0 self-fix calls)" || fail "run 0: expected 0 self-fix calls before 21:00, got $CALLS_0"

echo "--- run 1: at 21:00 JST (hour=21) -> should escalate all 7 loops (all report met=false) ---"
HOME="$FAKE_HOME" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF" CADENCE_DEADLINE_NOW_HOUR_JST=21 bash "$REAL_SCRIPT" >/dev/null 2>&1
CALLS_1=0
[ -f "$SELF_FIX_CALLS" ] && CALLS_1="$(wc -l < "$SELF_FIX_CALLS" | tr -d ' ')"
[ "$CALLS_1" = 7 ] && ok "run 1: escalated exactly 7 (one per Cadence Contract loop)" || fail "run 1: expected 7 self-fix calls, got $CALLS_1"

echo "--- run 2 (same JST day, hour=23): marker-gate must suppress re-escalation ---"
HOME="$FAKE_HOME" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF" CADENCE_DEADLINE_NOW_HOUR_JST=23 bash "$REAL_SCRIPT" >/dev/null 2>&1
CALLS_2=0
[ -f "$SELF_FIX_CALLS" ] && CALLS_2="$(wc -l < "$SELF_FIX_CALLS" | tr -d ' ')"
[ "$CALLS_2" = 7 ] && ok "run 2: still 7 total (marker-gate suppressed the duplicate escalation)" || fail "run 2: expected still 7 (no new calls), got $CALLS_2"

rm -rf "$FAKE_SELF" "$FAKE_HOME"

echo "--- G1 regression: a .<loop>-core-selfheal-request.json marker MUST spawn self-fix.sh even before 21:00 JST (LOOPS-TRUTH-AUDIT.md: clip-promote-core wrote such a marker and self-fix ran 0 times that day) ---"
FAKE_SELF2="$(mktemp -d)"; FAKE_HOME2="$(mktemp -d)"
mkdir -p "$FAKE_HOME2/.openclaw/state" "$FAKE_HOME2/.openclaw/logs"
cat > "$FAKE_SELF2/cadence-evidence.py" <<'PYEOF'
import json, sys
loop = sys.argv[2]
print(json.dumps({"loop": loop, "met": True, "streak": 1, "scorecard": "ok"}))
PYEOF
SELF_FIX_CALLS2="$FAKE_HOME2/.openclaw/state/self-fix-calls.log"
cat > "$FAKE_SELF2/self-fix.sh" <<EOF
#!/usr/bin/env bash
echo "\$1|\$2" >> "$SELF_FIX_CALLS2"
EOF
chmod +x "$FAKE_SELF2/self-fix.sh"
cat > "$FAKE_SELF2/cadence-contracts.json" <<'JSONEOF'
{}
JSONEOF
printf '{"loop":"clip-promote","ts":"2026-07-11T10:04:05Z","reason":"clip-promote-core DEAD","restarts_last_60min":5,"note":"gave up"}\n' \
  > "$FAKE_HOME2/.openclaw/state/.clip-promote-core-selfheal-request.json"
# an already-resolved marker (renamed with a trailing suffix, this codebase's own convention --
# see .connector-core-selfheal-request.json.resolved-2026-07-11) must NOT match the glob/re-fire.
printf '{"loop":"connector","ts":"2026-07-10T20:32:37Z","reason":"connector-core DEAD"}\n' \
  > "$FAKE_HOME2/.openclaw/state/.connector-core-selfheal-request.json.resolved-2026-07-11"

HOME="$FAKE_HOME2" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF2" CADENCE_DEADLINE_NOW_HOUR_JST=14 bash "$REAL_SCRIPT" >/dev/null 2>&1
G1_CALLS=0
[ -f "$SELF_FIX_CALLS2" ] && G1_CALLS="$(wc -l < "$SELF_FIX_CALLS2" | tr -d ' ')"
[ "$G1_CALLS" = 1 ] && ok "G1: exactly 1 self-fix call before 21:00 JST (the live marker only)" \
  || fail "G1: expected exactly 1 self-fix call (live marker), got $G1_CALLS"
grep -qF "clip-promote|" "$SELF_FIX_CALLS2" 2>/dev/null && ok "G1: self-fix.sh invoked with loop=clip-promote (from the json 'loop' field)" \
  || fail "G1: self-fix.sh was not invoked with loop=clip-promote"
grep -qF "connector|" "$SELF_FIX_CALLS2" 2>/dev/null && fail "G1: resolved marker (.resolved-YYYY-MM-DD suffix) must NOT re-trigger self-fix" \
  || ok "G1: resolved marker correctly excluded (no connector self-fix call)"

echo "--- G1 idempotency: calling again the same pass (no new marker) still re-invokes self-fix once per pass -- self-fix.sh's OWN idempotency (not this script) is the de-dup layer ---"
HOME="$FAKE_HOME2" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF2" CADENCE_DEADLINE_NOW_HOUR_JST=14 bash "$REAL_SCRIPT" >/dev/null 2>&1
G1_CALLS_2=0
[ -f "$SELF_FIX_CALLS2" ] && G1_CALLS_2="$(wc -l < "$SELF_FIX_CALLS2" | tr -d ' ')"
[ "$G1_CALLS_2" = 2 ] && ok "G1: a still-present marker re-escalates on the next pass (2 total calls across 2 passes)" \
  || fail "G1: expected 2 total self-fix calls after a 2nd pass with the marker still present, got $G1_CALLS_2"

rm -rf "$FAKE_SELF2" "$FAKE_HOME2"

echo "=== test_cadence_deadline_check: $P passed $F failed ==="
[ "$F" = 0 ] && exit 0 || exit 1
