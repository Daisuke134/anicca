#!/usr/bin/env bash
set -u

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
SOURCE="$SKILL_DIR/gig_pass.sh"
TMP=$(mktemp -d)
FAILURES=0
PIDS=""

cleanup() {
  for pid in $PIDS; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  rm -rf "$TMP"
}
trap cleanup EXIT

pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

setup_case() {
  CASE_DIR="$TMP/$1"
  HOME_DIR="$CASE_DIR/home"
  LOCKD="$CASE_DIR/lock.d"
  RUNNER="$CASE_DIR/gig_pass.sh"
  LOG="$CASE_DIR/stderr.log"
  mkdir -p "$HOME_DIR/.local/bin" "$HOME_DIR/gig" "$HOME_DIR/anicca/skills/browser"
  cat > "$HOME_DIR/.local/bin/claude" <<'EOF'
#!/bin/sh
exit 0
EOF
  cat > "$HOME_DIR/anicca/skills/browser/ensure_browser.sh" <<'EOF'
#!/bin/sh
if [ -n "${GIG_TEST_PRELUDE_WAIT_FILE:-}" ]; then
  while [ ! -e "$GIG_TEST_PRELUDE_WAIT_FILE" ]; do sleep 0.01; done
else
  sleep "${GIG_TEST_PRELUDE_HOLD:-0}"
fi
EOF
  chmod +x "$HOME_DIR/.local/bin/claude" "$HOME_DIR/anicca/skills/browser/ensure_browser.sh"
  sed \
    -e "s|^LOCKD=.*|LOCKD=\"$LOCKD\"|" \
    -e "s|^CLAUDE=.*|CLAUDE=\"$HOME_DIR/.local/bin/claude\"|" \
    "$SOURCE" > "$RUNNER"
  chmod +x "$RUNNER"
}

setup_case acquire_writes_pid
HOME="$HOME_DIR" GIG_TEST_PRELUDE_HOLD=2 bash "$RUNNER" >/dev/null 2>"$LOG" &
runner_pid=$!
PIDS="$PIDS $runner_pid"
written_pid=""
for _ in $(seq 1 100); do
  if [ -r "$LOCKD/pid" ]; then
    written_pid=$(cat "$LOCKD/pid")
    break
  fi
  kill -0 "$runner_pid" 2>/dev/null || break
  sleep 0.02
done
if [ "$written_pid" = "$runner_pid" ]; then
  pass "INV-1 acquire writes owner PID"
else
  fail "INV-1 acquire writes owner PID (expected $runner_pid, got ${written_pid:-missing})"
fi
touch -t 200001010000 "$LOCKD"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$CASE_DIR/contender.log"
current_pid=""
[ -r "$LOCKD/pid" ] && current_pid=$(cat "$LOCKD/pid")
if grep -q "another pass holds the lock" "$CASE_DIR/contender.log" \
  && [ "$current_pid" = "$runner_pid" ] \
  && kill -0 "$runner_pid" 2>/dev/null; then
  pass "INV-2 real bash gig_pass.sh owner is retained despite old mtime"
else
  fail "INV-2 real bash gig_pass.sh owner is retained despite old mtime"
fi
wait "$runner_pid"
PIDS=${PIDS% "$runner_pid"}
if [ ! -d "$LOCKD" ]; then
  pass "owner exit removes PID lock directory"
else
  fail "owner exit removes PID lock directory"
fi

setup_case dead_pid
(sh -c 'exit 0') &
dead_pid=$!
wait "$dead_pid" 2>/dev/null || true
mkdir "$LOCKD"
printf '%s\n' "$dead_pid" > "$LOCKD/pid"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if ! grep -q "another pass holds the lock" "$LOG" && [ ! -d "$LOCKD" ]; then
  pass "INV-1 dead PID is reaped immediately"
else
  fail "INV-1 dead PID is reaped immediately"
fi

setup_case reused_pid
/bin/sleep 30 &
reused_pid=$!
PIDS="$PIDS $reused_pid"
mkdir "$LOCKD"
printf '%s\n' "$reused_pid" > "$LOCKD/pid"
touch -t 200001010000 "$LOCKD"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if ! grep -q "another pass holds the lock" "$LOG" && [ ! -d "$LOCKD" ] && kill -0 "$reused_pid" 2>/dev/null; then
  pass "INV-1 live PID with non-gig command is reaped"
else
  fail "INV-1 live PID with non-gig command is reaped"
fi
kill "$reused_pid" 2>/dev/null || true
wait "$reused_pid" 2>/dev/null || true
PIDS=${PIDS% "$reused_pid"}

setup_case malformed_pid
mkdir "$LOCKD"
printf '%s\n' 'not-a-pid' > "$LOCKD/pid"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if ! grep -q "another pass holds the lock" "$LOG" && [ ! -d "$LOCKD" ]; then
  pass "INV-1 malformed readable PID is reaped immediately"
else
  fail "INV-1 malformed readable PID is reaped immediately"
  rm -f "$LOCKD/pid"
  rmdir "$LOCKD" 2>/dev/null || true
fi

# shellcheck disable=SC2016 # Assert the literal $quarantine source expression.
if grep -q 'kill -0' "$SOURCE" \
  && grep -q 'ps -p' "$SOURCE" \
  && grep -q 'comm=' "$SOURCE" \
  && grep -q 'command=' "$SOURCE" \
  && grep -q 'renamex_np' "$SOURCE" \
  && grep -q 'RENAME_EXCL' "$SOURCE" \
  && grep -q 'stat -f %c "$quarantine"' "$SOURCE"; then
  pass "INV-2 implementation validates identity and uses atomic no-replace quarantine"
else
  fail "INV-2 implementation validates identity and uses atomic no-replace quarantine"
fi

setup_case orphaned_reaper
(sh -c 'exit 0') &
stale_pid=$!
wait "$stale_pid" 2>/dev/null || true
(sh -c 'exit 0') &
stale_reaper_pid=$!
wait "$stale_reaper_pid" 2>/dev/null || true
mkdir -p "$LOCKD/.reap"
printf '%s\n' "$stale_pid" > "$LOCKD/pid"
printf '%s\n' "$stale_reaper_pid" > "$LOCKD/.reap/pid"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if ! grep -q "another pass holds the lock" "$LOG" && [ ! -d "$LOCKD" ]; then
  pass "INV-1 orphaned reaper claim self-recovers"
else
  fail "INV-1 orphaned reaper claim self-recovers"
  rm -f "$LOCKD/.reap/pid" "$LOCKD/pid"
  rmdir "$LOCKD/.reap" 2>/dev/null || true
  rmdir "$LOCKD" 2>/dev/null || true
fi

setup_case concurrent_reap
(sh -c 'exit 0') &
stale_pid=$!
wait "$stale_pid" 2>/dev/null || true
mkdir "$LOCKD"
printf '%s\n' "$stale_pid" > "$LOCKD/pid"
contender_pids=""
for i in $(seq 1 8); do
  HOME="$HOME_DIR" GIG_TEST_PRELUDE_WAIT_FILE="$CASE_DIR/release" bash "$RUNNER" >/dev/null 2>"$CASE_DIR/contender-$i.log" &
  contender_pids="$contender_pids $!"
done
busy=0
for _ in $(seq 1 200); do
  busy=0
  for i in $(seq 1 8); do
    [ -f "$CASE_DIR/contender-$i.log" ] && grep -q "another pass holds the lock" "$CASE_DIR/contender-$i.log" && busy=$((busy + 1))
  done
  [ "$busy" -ge 7 ] && break
  sleep 0.01
done
touch "$CASE_DIR/release"
for pid in $contender_pids; do wait "$pid"; done
owners=0
for i in $(seq 1 8); do
  grep -q "another pass holds the lock" "$CASE_DIR/contender-$i.log" || owners=$((owners + 1))
done
if [ "$owners" -eq 1 ] && [ ! -d "$LOCKD" ]; then
  pass "INV-2 concurrent stale reapers yield exactly one owner"
else
  fail "INV-2 concurrent stale reapers yield exactly one owner (owners=$owners busy_before_release=$busy)"
  rm -f "$LOCKD/.reap/pid" "$LOCKD/pid"
  rmdir "$LOCKD/.reap" 2>/dev/null || true
  rmdir "$LOCKD" 2>/dev/null || true
fi

setup_case concurrent_pidless_reap
mkdir "$LOCKD"
touch -t 200001010000 "$LOCKD"
contender_pids=""
for i in $(seq 1 8); do
  HOME="$HOME_DIR" GIG_TEST_PRELUDE_WAIT_FILE="$CASE_DIR/release" bash "$RUNNER" >/dev/null 2>"$CASE_DIR/contender-$i.log" &
  contender_pids="$contender_pids $!"
done
busy=0
for _ in $(seq 1 200); do
  busy=0
  for i in $(seq 1 8); do
    [ -f "$CASE_DIR/contender-$i.log" ] && grep -q "another pass holds the lock" "$CASE_DIR/contender-$i.log" && busy=$((busy + 1))
  done
  [ "$busy" -ge 7 ] && break
  sleep 0.01
done
touch "$CASE_DIR/release"
for pid in $contender_pids; do wait "$pid"; done
owners=0
for i in $(seq 1 8); do
  grep -q "another pass holds the lock" "$CASE_DIR/contender-$i.log" || owners=$((owners + 1))
done
quarantine_count=0
quarantine=""
for candidate in "$LOCKD".reaped.*; do
  [ -d "$candidate" ] || continue
  quarantine_count=$((quarantine_count + 1))
  [ -n "$quarantine" ] || quarantine="$candidate"
done
quarantine_age=999999
[ -n "$quarantine" ] && quarantine_age=$(( $(date +%s) - $(stat -f %c "$quarantine") ))
if [ "$owners" -eq 1 ] && [ "$quarantine_count" -eq 1 ] && [ "$quarantine_age" -le 60 ] && [ ! -d "$LOCKD" ]; then
  pass "INV-2 concurrent empty PID-less stale lock uses fresh exclusive quarantine"
else
  fail "INV-2 concurrent empty PID-less stale lock uses fresh exclusive quarantine (owners=$owners quarantines=$quarantine_count age=$quarantine_age)"
  rm -f "$LOCKD/pid"
  rmdir "$LOCKD" 2>/dev/null || true
fi

setup_case no_pid_stale
mkdir "$LOCKD"
touch -t 200001010000 "$LOCKD"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if ! grep -q "another pass holds the lock" "$LOG" && [ ! -d "$LOCKD" ]; then
  pass "INV-1/2 stale PID-less lock keeps time fallback"
else
  fail "INV-1/2 stale PID-less lock keeps time fallback"
fi

setup_case no_pid_fresh
mkdir "$LOCKD"
HOME="$HOME_DIR" bash "$RUNNER" >/dev/null 2>"$LOG"
if grep -q "another pass holds the lock" "$LOG" && [ -d "$LOCKD" ]; then
  pass "INV-1/2 fresh PID-less lock remains backward compatible"
else
  fail "INV-1/2 fresh PID-less lock remains backward compatible"
fi
rmdir "$LOCKD"

if [ "$FAILURES" -ne 0 ]; then
  printf '%s lock test(s) failed\n' "$FAILURES"
  exit 1
fi
printf 'All lock tests passed\n'
