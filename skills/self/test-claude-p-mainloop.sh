#!/usr/bin/env bash
# VCSDD oracle for the build-loop-unify feature (TODO #4). Fences REQ-000..REQ-006 from
# .vcsdd/features/build-loop-unify/specs/behavioral-spec.md.
#
# SAFETY (why this file is structured the way it is): claude-p-mainloop.sh is a LIVE cron
# script — its pidfile is $HOME/.openclaw/state/claude-p-mainloop.pid, the SAME file the
# production `ai.anicca.claude-p-mainloop` launchd job uses. Before the CLAUDE_P_MAINLOOP_TEST
# isolation seam (REQ-006) exists, this test file must NEVER execute the script directly —
# doing so on this live system could collide with the currently-running production loop.
# So: static (grep-only, zero execution) assertions run unconditionally and are what proves
# RED before the seam is implemented; the dynamic (actually invokes the script) assertions
# are gated behind the static seam check and only execute once the seam is present, and even
# then only against a mktemp -d isolated state/log/workdir + a stub `claude` on PATH — never
# the real pidfile, never a real `claude --dangerously-skip-permissions` process.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAINLOOP="$HERE/claude-p-mainloop.sh"
PROMPT="$HERE/claude-p-mainloop-prompt.txt"
FOUNDER_DIR="$HERE/founder-loop"
REAL_PIDFILE="$HOME/.openclaw/state/claude-p-mainloop.pid"

fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- REQ-000: corrected finding — exactly one claude-invoking script pair in skills/self ----------
CLAUDE_HITS="$(grep -rl 'claude --model\|claude -p \|claude --dangerously-skip-permissions' "$HERE" --include='*.sh' --exclude='test-*.sh' 2>/dev/null | sort)"
ok "$([ "$(echo "$CLAUDE_HITS" | wc -l | tr -d ' ')" = 1 ] && echo 1 || echo 0)" "REQ-000/REQ-002: exactly one *.sh under skills/self invokes claude (found: $(echo "$CLAUDE_HITS" | tr '\n' ' '))"

# ---------- REQ-001: founder-loop.sh remains a deterministic, non-LLM script (untouched) ----------
FOUNDER_SRC="$(cat "$FOUNDER_DIR/founder-loop.sh" 2>/dev/null || true)"
ok "$([ -n "$FOUNDER_SRC" ] && ! grep -q 'claude' <<<"$FOUNDER_SRC" && echo 1 || echo 0)" "REQ-001: founder-loop.sh contains zero 'claude' references (deterministic RECORD/CEO layer, not LOOP B)"
ok "$([ ! -f "$FOUNDER_DIR/founder-loop-prompt.txt" ] && echo 1 || echo 0)" "REQ-000: no founder-loop-prompt.txt exists anywhere (the doc's premise of a 2nd prompt twin is false)"

# ---------- REQ-006 (static): isolation seam present in the script ----------
SRC="$(cat "$MAINLOOP")"
have_test_seam="$(grep -q 'CLAUDE_P_MAINLOOP_TEST' <<<"$SRC" && echo 1 || echo 0)"
ok "$have_test_seam" "REQ-006: CLAUDE_P_MAINLOOP_TEST isolation seam present in claude-p-mainloop.sh"

# ---------- REQ-005 (static): model override var present ----------
have_model_var="$(grep -q 'CLAUDE_P_MAINLOOP_MODEL' <<<"$SRC" && echo 1 || echo 0)"
ok "$have_model_var" "REQ-005: CLAUDE_P_MAINLOOP_MODEL override present in claude-p-mainloop.sh"

# ---------- REQ-004 (static, regression guard): pidfile guard / kill-switch / prompt-in-own-file preserved ----------
ok "$(grep -q 'PAUSE_FILE' <<<"$SRC" && grep -qE 'if \[ -f "\$PAUSE_FILE" \]' <<<"$SRC" && echo 1 || echo 0)" "REQ-004: kill-switch check (\$PAUSE_FILE) preserved"
ok "$(grep -q 'PIDFILE' <<<"$SRC" && grep -q 'trap cleanup EXIT' <<<"$SRC" && echo 1 || echo 0)" "REQ-004: pidfile single-instance guard + trap cleanup preserved"
ok "$(grep -qE '\$\(cat "\$PROMPT_FILE"\)' <<<"$SRC" && echo 1 || echo 0)" "REQ-004: prompt loaded via \$(cat \"\$PROMPT_FILE\") (never inlined) preserved"

# ---------- REQ-003 (static): prompt purified to explicit LOOP B boundaries ----------
PROMPT_SRC="$(cat "$PROMPT" 2>/dev/null || true)"
ok "$(grep -qi 'never.*earn\|do not.*earn\|never perform.*earn' <<<"$PROMPT_SRC" && echo 1 || echo 0)" "REQ-003: prompt explicitly forbids the build loop from performing/simulating an earn action"
ok "$(grep -qi 'wallet\|on-chain' <<<"$PROMPT_SRC" && grep -qi 'truth' <<<"$PROMPT_SRC" && echo 1 || echo 0)" "REQ-003: prompt names on-chain wallet/ledger as the only earn-truth source"

# ---------- REQ-006 (dynamic) + REQ-005 (dynamic): gated behind the seam actually existing ----------
if [ "$have_test_seam" = 1 ] && [ "$have_model_var" = 1 ]; then
  BEFORE_MTIME="$(stat -f '%m' "$REAL_PIDFILE" 2>/dev/null || echo none)"

  T="$(mktemp -d)"
  BIN="$T/bin"; mkdir -p "$BIN" "$T/state" "$T/log" "$T/workdir"
  cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CLAUDE_ARGV_CAPTURE"
exit 0
STUB
  chmod +x "$BIN/claude"

  # sonnet default (var unset)
  CAP1="$T/argv-default.txt"
  PATH="$BIN:$PATH" CLAUDE_ARGV_CAPTURE="$CAP1" \
    CLAUDE_P_MAINLOOP_TEST=1 CLAUDE_P_MAINLOOP_STATE_DIR="$T/state" \
    CLAUDE_P_MAINLOOP_LOG_DIR="$T/log" CLAUDE_P_MAINLOOP_PAUSE_FILE="$T/pause" \
    CLAUDE_P_MAINLOOP_WORKDIR="$T/workdir" \
    bash "$MAINLOOP" >/dev/null 2>&1
  ok "$(grep -q '^sonnet$' "$CAP1" 2>/dev/null && echo 1 || echo 0)" "PROP-002: CLAUDE_P_MAINLOOP_MODEL unset -> claude invoked with --model sonnet (default unchanged)"

  # opus override
  CAP2="$T/argv-opus.txt"
  PATH="$BIN:$PATH" CLAUDE_ARGV_CAPTURE="$CAP2" \
    CLAUDE_P_MAINLOOP_TEST=1 CLAUDE_P_MAINLOOP_STATE_DIR="$T/state2" \
    CLAUDE_P_MAINLOOP_LOG_DIR="$T/log2" CLAUDE_P_MAINLOOP_PAUSE_FILE="$T/pause2" \
    CLAUDE_P_MAINLOOP_WORKDIR="$T/workdir" CLAUDE_P_MAINLOOP_MODEL=opus \
    bash "$MAINLOOP" >/dev/null 2>&1
  ok "$(grep -q '^opus$' "$CAP2" 2>/dev/null && echo 1 || echo 0)" "PROP-003: CLAUDE_P_MAINLOOP_MODEL=opus -> claude invoked with --model opus"

  AFTER_MTIME="$(stat -f '%m' "$REAL_PIDFILE" 2>/dev/null || echo none)"
  ok "$([ "$BEFORE_MTIME" = "$AFTER_MTIME" ] && echo 1 || echo 0)" "PROP-007: real production pidfile ($REAL_PIDFILE) untouched by isolated test runs"

  rm -rf "$T"
else
  echo "  - SKIP dynamic PROP-002/PROP-003/PROP-007 (isolation seam not yet implemented — refusing to execute claude-p-mainloop.sh against live production paths)"
  fails=$((fails+3))
fi

[ $fails -eq 0 ] && { echo "PASS — build-loop-unify invariants hold (REQ-000 corrected finding · REQ-001 founder-loop untouched/non-LLM · REQ-002 single build cron · REQ-003 LOOP B purity in prompt · REQ-004 pidfile/kill-switch/prompt-file preserved · REQ-005 model override · REQ-006 test isolation seam, live pidfile untouched)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
