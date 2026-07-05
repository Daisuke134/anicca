#!/usr/bin/env bash
# test_healthcheck_stale_fallback.sh — Task #18 (2026-07-05). Verifies the STALE-detection
# marker-reseed fix in all 6 earn-loop healthcheck.sh files. Root cause fixed: a missing
# .{name}-core-last-start marker used to fall back to either "now" (5 loops: STALE detection
# permanently disabled -- the real affiliate/bounty incident, spec §24.5-24.9) or epoch-0
# (gig: immediate false-restart of a healthy session). The fix reseeds the marker instead of
# guessing a timestamp, deferring the real measurement to the next healthcheck pass (5min later).
#
# Each target script is sandboxed by remapping its SOCK/HB/START/LOG/RESTART_LOG/lock paths to a
# throwaway tmux socket + a temp dir, and its restart-trigger `bash .../*-cli.sh --restart` line
# to a fake script that only records that it was called. No production state is touched.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANICCA_HOME="$(cd "$HERE/../../.." && pwd)"   # .../anicca/skills/_shared/__tests__ -> .../anicca
PASS=0; FAIL=0

TARGETS=(
  "clip:$ANICCA_HOME/skills/earn/clip/clip-healthcheck.sh:/tmp/anicca-clip-tmux.sock:anicca-clip-core:\$HOME/.openclaw/state/.clip-core-last-pass:\$HOME/.openclaw/state/.clip-core-last-start:\$HOME/.openclaw/logs/clip-core-healthcheck.log:\$HOME/.openclaw/state/.clip-core-restart-log:/tmp/.clip-healthcheck.lock:bash \"\$HOME/anicca/skills/earn/clip/clip-cli.sh\" --restart"
  "clip-promote:$ANICCA_HOME/skills/earn/clip-promote/clip-promote-healthcheck.sh:/tmp/anicca-clip-promote-tmux.sock:anicca-clip-promote-core:\$HOME/.openclaw/state/.clip-promote-core-last-pass:\$HOME/.openclaw/state/.clip-promote-core-last-start:\$HOME/.openclaw/logs/clip-promote-core-healthcheck.log:\$HOME/.openclaw/state/.clip-promote-core-restart-log:/tmp/.clip-promote-healthcheck.lock:bash \"\$HOME/anicca/skills/earn/clip-promote/clip-promote-cli.sh\" --restart"
  "video:$ANICCA_HOME/skills/earn/video/video-healthcheck.sh:/tmp/anicca-video-tmux.sock:anicca-video-core:\$HOME/.openclaw/state/.video-core-last-pass:\$HOME/.openclaw/state/.video-core-last-start:\$HOME/.openclaw/logs/video-core-healthcheck.log:\$HOME/.openclaw/state/.video-core-restart-log:/tmp/.video-healthcheck.lock:bash \"\$HOME/anicca/skills/earn/video/video-cli.sh\" --restart"
  "bounty:$ANICCA_HOME/skills/human-funded/bounty/bounty-healthcheck.sh:/tmp/anicca-bounty-tmux.sock:anicca-bounty-core:\$HOME/.openclaw/state/.bounty-core-last-pass:\$HOME/.openclaw/state/.bounty-core-last-start:\$HOME/.openclaw/logs/bounty-core-healthcheck.log:\$HOME/.openclaw/state/.bounty-core-restart-log:/tmp/.bounty-healthcheck.lock:bash \"\$HOME/anicca/skills/human-funded/bounty/bounty-cli.sh\" --restart"
  "affiliate:$ANICCA_HOME/skills/human-funded/affiliate/affiliate-healthcheck.sh:/tmp/anicca-affiliate-tmux.sock:anicca-affiliate-core:\$HOME/.openclaw/state/.affiliate-core-last-pass:\$HOME/.openclaw/state/.affiliate-core-last-start:\$HOME/.openclaw/logs/affiliate-core-healthcheck.log:\$HOME/.openclaw/state/.affiliate-core-restart-log:/tmp/.affiliate-healthcheck.lock:bash \"\$HOME/anicca/skills/human-funded/affiliate/affiliate-cli.sh\" --restart"
  "gig:$ANICCA_HOME/skills/human-funded/gig/gig-healthcheck.sh:/tmp/anicca-gig-tmux.sock:anicca-gig-core:\$HOME/gig/.last-pass:\$HOME/gig/.last-start:\$HOME/.openclaw/logs/gig-core-healthcheck.log:\$HOME/gig/.restart-log:/tmp/.gig-healthcheck.lock:bash \"\$HOME/anicca/skills/human-funded/gig/gig-cli.sh\" --restart"
)

check() { # $1=desc $2=cond(0/1) $3=name
  if [ "$2" = "1" ]; then echo "  ok  $3"; PASS=$((PASS+1)); else echo "  FAIL $3 -- $1"; FAIL=$((FAIL+1)); fi
}

for entry in "${TARGETS[@]}"; do
  IFS=':' read -r NAME SRC REAL_SOCK REAL_SESSION REAL_HB REAL_START REAL_LOG REAL_RLOG REAL_LOCK REAL_RESTART_CMD <<< "$entry"
  echo "=== $NAME ($SRC) ==="

  TD="$(mktemp -d)"; mkdir -p "$TD/state" "$TD/logs"
  SOCKPATH="/tmp/hc-test-$NAME.sock"
  TEST_MARKER="$TD/restart-marker.log"
  cat > "$TD/fake-cli.sh" <<EOF
#!/usr/bin/env bash
echo "RESTART_CALLED \$(date +%s)" >> "$TEST_MARKER"
EOF
  chmod +x "$TD/fake-cli.sh"

  sed \
    -e "s#$REAL_SOCK#$SOCKPATH#" \
    -e "s#SESSION=\"$REAL_SESSION\"#SESSION=\"hc-test-$NAME\"#" \
    -e "s#$REAL_HB#$TD/state/.last-pass#" \
    -e "s#$REAL_START#$TD/state/.last-start#" \
    -e "s#$REAL_LOG#$TD/logs/hc.log#" \
    -e "s#$REAL_RLOG#$TD/state/.restart-log#" \
    -e "s#$REAL_LOCK#$TD/hc.lock#" \
    -e "s#$REAL_RESTART_CMD#bash \"$TD/fake-cli.sh\" --restart#" \
    "$SRC" > "$TD/sandbox.sh"
  chmod +x "$TD/sandbox.sh"

  run_case() {
    tmux -S "$SOCKPATH" kill-server 2>/dev/null; rm -f "$SOCKPATH"
    tmux -S "$SOCKPATH" new-session -d -s "hc-test-$NAME" "sleep 60" 2>/dev/null; sleep 0.5
    rm -f "$TEST_MARKER" "$TD/logs/hc.log"; rmdir "$TD/hc.lock" 2>/dev/null
    bash "$TD/sandbox.sh" >/dev/null 2>&1
  }

  # S1: HB missing, START missing -> reseed only, no restart
  rm -f "$TD/state/.last-pass" "$TD/state/.last-start"
  run_case
  s1_reseeded=0; [ -f "$TD/state/.last-start" ] && s1_reseeded=1
  s1_no_restart=0; [ ! -f "$TEST_MARKER" ] && s1_no_restart=1
  check "marker not reseeded" "$s1_reseeded" "$NAME: S1 missing HB+START -> reseeds START"
  check "restart wrongly called" "$s1_no_restart" "$NAME: S1 missing HB+START -> does NOT restart"

  # S2: HB missing, START fresh -> no-op
  rm -f "$TD/state/.last-pass"; touch "$TD/state/.last-start"
  run_case
  s2_no_restart=0; [ ! -f "$TEST_MARKER" ] && s2_no_restart=1
  check "restart wrongly called on fresh START" "$s2_no_restart" "$NAME: S2 fresh START -> no restart"

  # S3: HB missing, START old (2h ago, exceeds STALE_MIN for every loop here: 90 or 1560min... use
  # a very old timestamp so it exceeds even the 1560min (26h) affiliate/bounty threshold)
  rm -f "$TD/state/.last-pass"
  touch -t "$(date -v-48H +%Y%m%d%H%M.%S)" "$TD/state/.last-start"
  run_case
  s3_restarted=0; [ -f "$TEST_MARKER" ] && s3_restarted=1
  check "restart NOT called on stale START" "$s3_restarted" "$NAME: S3 stale(48h) START -> restarts"

  # S4: HB fresh -> no-op (non-regression)
  touch "$TD/state/.last-pass"
  run_case
  s4_no_restart=0; [ ! -f "$TEST_MARKER" ] && s4_no_restart=1
  check "restart wrongly called on fresh HB" "$s4_no_restart" "$NAME: S4 fresh HB -> no restart (non-regression)"

  tmux -S "$SOCKPATH" kill-server 2>/dev/null; rm -f "$SOCKPATH"
  rm -rf "$TD"
done

echo ""
echo "$PASS/$((PASS+FAIL)) passed"
[ "$FAIL" -eq 0 ]
