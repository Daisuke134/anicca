#!/usr/bin/env bash
# Offline E2E for forum-rollout (#338 P15): fixture thread with a CONSENSUS: + rollout
# fence → rollout.sh --dry-run → assert correct dispatch + jsonl row + idempotency.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../scripts" && pwd)"
export STATE_DIR="$HOME/.hermes/state/.fr-test-e2e.$$"
WORK="$STATE_DIR/work"; mkdir -p "$WORK"
trap 'rm -rf "$STATE_DIR"' EXIT
pass=0; fail=0
ok(){ pass=$((pass+1)); echo "  ok: $1"; }
bad(){ fail=$((fail+1)); echo "  FAIL: $1"; }

# fake self-manage handler dir: stub records its JSON arg + exits 0.
SM="$WORK/sm"; mkdir -p "$SM"
cat > "$SM/architecture-shift.sh" <<EOF
#!/usr/bin/env bash
echo "STUB-ARCH-SHIFT arg=\$1" >> "$STATE_DIR/stub.log"
echo "architecture-shift: FILED https://github.com/x/y/issues/99"
exit 0
EOF
chmod +x "$SM/architecture-shift.sh"
# fake guard: always allow.
GUARD="$WORK/guard.sh"; printf '#!/usr/bin/env bash\nexit 0\n' > "$GUARD"; chmod +x "$GUARD"

# fixture issue + thread with CONSENSUS: + rollout fence (block lives in a comment, not body).
FX="$WORK/fx"; mkdir -p "$FX"
cat > "$FX/issues.json" <<'EOF'
[{"number":11,"body":"arch-shift proposal, no block in body"}]
EOF
cat > "$FX/thread-11.json" <<'EOF'
[{"id":1,"body":"discussion ..."},
 {"id":2,"body":"CONSENSUS: merge it\n\n```rollout\nACTION: architecture-shift\nTARGET: merge-foo-bar\nPAYLOAD: {\"reason\":\"agreed\",\"title\":\"merge foo+bar\"}\n```"}]
EOF

export FR_SELF_MANAGE_DIR="$SM" FR_GUARD_CHECK="$GUARD" FR_FIXTURE_DIR="$FX" STATE_DIR
LOG="$STATE_DIR/forum-rollout.jsonl"

bash "$ROOT/rollout.sh" --dry-run >/dev/null 2>&1 || true

grep -q 'STUB-ARCH-SHIFT' "$STATE_DIR/stub.log" 2>/dev/null && ok "handler invoked" || bad "handler invoked"
grep -q 'merge foo+bar' "$STATE_DIR/stub.log" 2>/dev/null && ok "argv carries title" || bad "argv carries title"
n="$(/usr/bin/jq -s 'map(select(.action_type=="architecture-shift" and .applied==false))|length' "$LOG" 2>/dev/null)"
[ "$n" = "1" ] && ok "one jsonl row applied=false" || bad "jsonl row (got $n)"

# idempotency: re-run → no second row.
bash "$ROOT/rollout.sh" --dry-run >/dev/null 2>&1 || true
n2="$(/usr/bin/jq -s 'length' "$LOG" 2>/dev/null)"
[ "$n2" = "1" ] && ok "idempotent: still 1 row" || bad "idempotent (got $n2)"

# --- HARD-NO defence: a rollout block targeting anicca-wallet must be BLOCKED, not dispatched ---
FX2="$WORK/fx2"; mkdir -p "$FX2"
echo '[{"number":12,"body":"x"}]' > "$FX2/issues.json"
cat > "$FX2/thread-12.json" <<'EOF'
[{"id":3,"body":"CONSENSUS: edit wallet\n\n```rollout\nACTION: edit-skill\nTARGET: anicca-wallet\nPAYLOAD: {\"reason\":\"nope\"}\n```"}]
EOF
: > "$STATE_DIR/stub.log"
cat > "$SM/edit-skill.sh" <<EOF
#!/usr/bin/env bash
echo "STUB-EDIT-SKILL arg=\$1" >> "$STATE_DIR/stub.log"
exit 0
EOF
chmod +x "$SM/edit-skill.sh"
FR_FIXTURE_DIR="$FX2" bash "$ROOT/rollout.sh" --dry-run >/dev/null 2>&1 || true
grep -q 'STUB-EDIT-SKILL' "$STATE_DIR/stub.log" 2>/dev/null && bad "hard-no: wallet must NOT dispatch" || ok "hard-no: wallet not dispatched"
blocked="$(/usr/bin/jq -s 'map(select(.issue_n==12 and .evidence_url=="BLOCKED:hard-no-list"))|length' "$LOG" 2>/dev/null)"
[ "$blocked" = "1" ] && ok "hard-no: BLOCKED row logged" || bad "hard-no: BLOCKED row (got $blocked)"

echo "---"; echo "PASS=$pass FAIL=$fail"; [ "$fail" -eq 0 ]
