#!/usr/bin/env bash
# test_verify_loops_audit_video_state_integrity.sh — G2 item2 regression test (2026-07-11
# loop-arch redesign / LOOPS-TRUTH-AUDIT.md: "video: 2つのstate file(warmup_day 4vs0)の整合性
# チェックが無い"). Confirmed real drift 2026-07-11: ~/.cloak/earn-video-money_blueprintdaily.json
# said warmup_day=4 (the file run.sh/decide.py actually gate on) while
# ~/.cloak/ig-warmup-money_blueprintdaily.json said warmup_day=0, same last_warmup_date -- nothing
# detected it. Proves: (a) a real drift escalates self-fix(video), (b) matching warmup_day values
# do NOT escalate, (c) a handle with no corresponding ig-warmup file (nothing to compare against)
# does NOT escalate. Mirrors this codebase's own fake-SELF-dir/fake-curl stubbing convention.
set -uo pipefail
P=0; F=0
ok(){ echo "  ok $1"; P=$((P+1)); }
fail(){ echo "  FAIL $1"; F=$((F+1)); }

REAL_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/verify-loops-audit.sh"

setup(){
  FAKE_SELF="$(mktemp -d)"
  FAKE_HOME="$(mktemp -d)"
  mkdir -p "$FAKE_HOME/.openclaw/state" "$FAKE_HOME/.openclaw/logs" "$FAKE_HOME/.cloak" \
           "$FAKE_SELF/reddit-loop/state" "$FAKE_SELF/life-manager-loop/state"
  cat > "$FAKE_SELF/verify-loops.sh" <<'EOF'
#!/usr/bin/env bash
echo "stub verify-loops output"
EOF
  cat > "$FAKE_SELF/cadence-deadline-check.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  cat > "$FAKE_SELF/cadence-evidence.py" <<'PYEOF'
import json, sys
loop = sys.argv[2]
print(json.dumps({"loop": loop, "met": True, "streak": 1, "scorecard": "ok"}))
PYEOF
  SELF_FIX_CALLS="$FAKE_HOME/.openclaw/state/self-fix-calls.log"
  cat > "$FAKE_SELF/self-fix.sh" <<EOF
#!/usr/bin/env bash
echo "\$1" >> "$SELF_FIX_CALLS"
EOF
  chmod +x "$FAKE_SELF/self-fix.sh" "$FAKE_SELF/verify-loops.sh" "$FAKE_SELF/cadence-deadline-check.sh"
  # empty posts.jsonl so the reddit block is a harmless no-op (no account) in every scenario here.
  : > "$FAKE_SELF/reddit-loop/state/posts.jsonl"
}
video_call_count(){ local f="$FAKE_HOME/.openclaw/state/self-fix-calls.log"; [ -f "$f" ] || { echo 0; return; }; local n; n="$(grep -c '^video$' "$f" 2>/dev/null)"; echo "${n:-0}"; }
run(){ HOME="$FAKE_HOME" VERIFY_LOOPS_SELF_DIR="$FAKE_SELF" VERIFY_LOOPS_AUDIT_CURL_BIN=/bin/false bash "$REAL_SCRIPT" >/dev/null 2>&1; }

# --- scenario 1 (THE FIX): real drift (warmup_day 4 vs 0, same handle) -> escalation MUST fire ---
setup
printf '{"handle": "money_blueprintdaily", "status": "warming", "warmup_day": 4, "last_warmup_date": "2026-07-11"}' \
  > "$FAKE_HOME/.cloak/earn-video-money_blueprintdaily.json"
printf '{"warmup_day": 0, "reels_watched_total": 80, "last_warmup_date": "2026-07-11", "watched_today": 6}' \
  > "$FAKE_HOME/.cloak/ig-warmup-money_blueprintdaily.json"
run
[ "$(video_call_count)" = 1 ] && ok "warmup_day drift (4 vs 0) -> 1 video self-fix call (the fix)" \
  || fail "warmup_day drift: expected 1 call, got $(video_call_count) (state-integrity check not wired)"
rm -rf "$FAKE_SELF" "$FAKE_HOME"

# --- scenario 2 (no false positive): both trackers agree (warmup_day=4 both) -> NO escalation ---
setup
printf '{"handle": "money_blueprintdaily", "status": "warming", "warmup_day": 4, "last_warmup_date": "2026-07-11"}' \
  > "$FAKE_HOME/.cloak/earn-video-money_blueprintdaily.json"
printf '{"warmup_day": 4, "reels_watched_total": 80, "last_warmup_date": "2026-07-11", "watched_today": 6}' \
  > "$FAKE_HOME/.cloak/ig-warmup-money_blueprintdaily.json"
run
[ "$(video_call_count)" = 0 ] && ok "warmup_day agrees (4 == 4) -> 0 video self-fix calls" \
  || fail "warmup_day agrees: expected 0 calls, got $(video_call_count)"
rm -rf "$FAKE_SELF" "$FAKE_HOME"

# --- scenario 3 (no false positive): no corresponding ig-warmup file for this handle (nothing to
# compare against, e.g. an account that never went through the ig-account-warmer skill) -> NO
# escalation via this check ---
setup
printf '{"handle": "money_blueprintdaily", "status": "warming", "warmup_day": 4, "last_warmup_date": "2026-07-11"}' \
  > "$FAKE_HOME/.cloak/earn-video-money_blueprintdaily.json"
run
[ "$(video_call_count)" = 0 ] && ok "no ig-warmup file for this handle -> 0 video self-fix calls (nothing to compare)" \
  || fail "no ig-warmup file: expected 0 calls, got $(video_call_count)"
rm -rf "$FAKE_SELF" "$FAKE_HOME"

echo "=== test_verify_loops_audit_video_state_integrity: $P passed $F failed ==="
[ "$F" = 0 ] && exit 0 || exit 1
