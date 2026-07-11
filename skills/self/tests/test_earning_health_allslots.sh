#!/usr/bin/env bash
# test_earning_health_allslots.sh — registry-driven wiring proof for earning-health-allslots.sh
# (REQ-AS-001..005, self-heal-allslots spec). Generalizes test_sol_trade_healthcheck.sh's proof
# pattern across MULTIPLE slots read from a temp registry — never touches the real
# skills/self/earning-health-registry.json or live ~/.openclaw state. All paths overridden to an
# isolated tmpdir (read-only-on-live-state rule).
set -uo pipefail; P=0; F=0
H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"     # skills/self/tests
SELF_DIR="$(cd "$H/.." && pwd)"                        # skills/self
SCRIPT="$SELF_DIR/earning-health-allslots.sh"

a(){ echo "$2" | grep -qF "$3" && { echo "  ok $1"; P=$((P+1)); } || { echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }
na(){ echo "$2" | grep -qF "$3" && { echo "  FAIL $1 (unexpectedly found:[$3])"; F=$((F+1)); } || { echo "  ok $1"; P=$((P+1)); }; }

REASON_A="identity-mismatch (own=none cli=none); slot-a"

mk_barren_trace(){
  local out="$1" reason="$2" n="${3:-20}"
  : > "$out"
  for i in $(seq 1 "$n"); do
    printf '{"ts":"2026-07-08T%02d:00:00Z","action":"skip","reason":"%s"}\n' "$((i % 24))" "$reason" >> "$out"
  done
}
mk_healthy_trace(){
  local out="$1"
  : > "$out"
  for i in $(seq 1 15); do
    printf '{"ts":"2026-07-08T%02d:00:00Z","action":"skip","reason":"%s"}\n' "$((i % 24))" "$REASON_A" >> "$out"
  done
  printf '{"ts":"2026-07-10T14:04:39Z","action":"live-pass","exit":0,"note":"WAIT"}\n' >> "$out"
}

D="$(mktemp -d)"
EARN_STATE="$D/earn-state"; mkdir -p "$EARN_STATE"
mk_barren_trace "$EARN_STATE/slot-a.trace.jsonl" "$REASON_A" 20
mk_healthy_trace "$EARN_STATE/slot-b.trace.jsonl"
# slot-c: instrumented=true but no trace file deployed yet (fresh instance) -> no-op
# slot-d: instrumented=false (documented gap) -> NOT-INSTRUMENTED, self-fix NEVER called for it

REGISTRY="$D/registry.json"
cat > "$REGISTRY" <<JSON
{
  "slots": [
    {"id":"earn/slot-a","instrumented":true,"traceFile":"slot-a.trace.jsonl","minRun":20,"selfFixTarget":"slot-a","escalateEveryHrs":24},
    {"id":"earn/slot-b","instrumented":true,"traceFile":"slot-b.trace.jsonl","minRun":20,"selfFixTarget":"slot-b","escalateEveryHrs":24},
    {"id":"earn/slot-c","instrumented":true,"traceFile":"slot-c.trace.jsonl","minRun":20,"selfFixTarget":"slot-c","escalateEveryHrs":24},
    {"id":"earn/slot-d","instrumented":false,"traceFile":null,"minRun":20,"selfFixTarget":"slot-d","escalateEveryHrs":24,"gapNote":"documented gap: no per-wake trace instrumented yet"}
  ]
}
JSON

echo "(A) full registry pass: barren/healthy/missing-trace/not-instrumented all in ONE run"
OUT="$(EARNHC_REGISTRY="$REGISTRY" EARNHC_EARN_STATE_DIR="$EARN_STATE" \
       EARNHC_STATE_DIR="$D/state" EARNHC_LOG="$D/hc.log" \
       SELF_FIX_DRYRUN=1 bash "$SCRIPT" 2>&1; cat "$D/hc.log" 2>/dev/null)"
a "slot-a BARREN detected"            "$OUT" "earn/slot-a BARREN"
a "slot-a self-fix fired (dry-run)"   "$OUT" "LOOP=slot-a-loop"
a "slot-a escalation marker written"  "$(ls -a "$D/state" 2>/dev/null)" ".earning-health-allslots-earn_slot_a-escalated"
a "slot-b OK (not barren)"            "$OUT" "earn/slot-b OK"
na "slot-b self-fix NOT fired"        "$OUT" "LOOP=slot-b-loop"
a "slot-c no trace yet -> no-op"      "$OUT" "earn/slot-c: no trace file"
na "slot-c self-fix NOT fired"        "$OUT" "LOOP=slot-c-loop"
a "slot-d logged as NOT-INSTRUMENTED" "$OUT" "NOT-INSTRUMENTED earn/slot-d"
na "slot-d self-fix NEVER fired (documented gap, not silently detected)" "$OUT" "LOOP=slot-d-loop"

echo "(B) second pass within escalation window -> slot-a does NOT spam a second self-fix call"
OUT2="$(EARNHC_REGISTRY="$REGISTRY" EARNHC_EARN_STATE_DIR="$EARN_STATE" EARNHC_STATE_DIR="$D/state" EARNHC_LOG="$D/hc2.log" \
        SELF_FIX_DRYRUN=1 bash "$SCRIPT" 2>&1; cat "$D/hc2.log" 2>/dev/null)"
a "slot-a second run logs already escalated" "$OUT2" "already escalated"
na "slot-a second run did NOT re-invoke self-fix" "$OUT2" "LOOP=slot-a-loop"

echo "(C) missing registry file -> no-op, never crashes"
D2="$(mktemp -d)"
OUT3="$(EARNHC_REGISTRY="$D2/missing-registry.json" EARNHC_STATE_DIR="$D2/state" EARNHC_LOG="$D2/hc.log" bash "$SCRIPT" 2>&1; echo "rc=$?"; cat "$D2/hc.log" 2>/dev/null)"
a "missing registry logs and exits cleanly" "$OUT3" "no registry at"
a "missing registry exits 0" "$OUT3" "rc=0"

rm -rf "$D" "$D2"
echo "=== earning-health-allslots: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
