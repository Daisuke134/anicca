#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
DAILY="$ROOT/skills/writer-agent/article-daily.sh"
TMP="$(mktemp -d)"
TEST_CHILD_PIDS=()
cleanup_test_processes() {
  local pid
  for pid in "${TEST_CHILD_PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in "${TEST_CHILD_PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  rm -rf -- "$TMP"
}
trap cleanup_test_processes EXIT INT TERM

# Run the production helpers and publication-lock block in an isolated shell.
# The harness stops before start control, so no model, browser, or publisher is
# invoked while the real lock control flow still executes.
LOCK_HELPERS="$(sed -n '/^process_start_token() {/,/^if mkdir "$RECOVERY_LOCK_DIR"/ { /^if mkdir "$RECOVERY_LOCK_DIR"/d; p; }' "$DAILY")"
LOCK_BLOCK="$(sed -n '/^if mkdir "$RECOVERY_LOCK_DIR"/,/^# START CONTROL:/ { /^# START CONTROL:/d; p; }' "$DAILY")"
if [[ -z "$LOCK_HELPERS" || -z "$LOCK_BLOCK" ]]; then
  echo "failed to extract article-daily lock control" >&2
  exit 1
fi

tree_hash() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    printf '%s\n' MISSING
    return 0
  fi
  find "$dir" -type f -exec shasum -a 256 {} + | LC_ALL=C sort | shasum -a 256 | awk '{print $1}'
}

assert_no_stale_dirs() {
  local state="$1" allowed="${2:-}" stale
  [[ ! -e "$state/.article-daily.recovery.lockdir" ]]
  stale="$(find "$state" -maxdepth 1 -type d -name '.article-daily.lockdir.stale.*' -print -quit)"
  [[ -z "$stale" || "$stale" == "$allowed" ]]
  [[ -z "$(find "$state" -maxdepth 1 -type d -name '.article-daily.lockdir.new.*' -print -quit)" ]]
  [[ -z "$(find "$state" -maxdepth 1 -type d -name '.article-daily.lockdir.metadata.*' -print -quit)" ]]
}

assert_terminal() {
  local log="$1" reason="$2" rc="$3"
  if [[ "$rc" -ne 1 ]]; then
    echo "FAIL: expected terminal rc=1, got rc=$rc (reason=$reason)" >&2
    return 1
  fi
  if ! grep -F "article-daily TERMINAL — $reason" "$log" >/dev/null; then
    echo "FAIL: expected terminal reason not found: $reason" >&2
    sed -n '1,80p' "$log" >&2
    return 1
  fi
}

write_command_wrappers() {
  local bin="$1"
  mkdir -p "$bin"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'if [[ "${FAIL_OP:-}" == mv-quarantine' \
    '  && "${1:-}" == "$STATE_DIR/.article-daily.lockdir"' \
    '  && "${2:-}" == "$STATE_DIR"/.article-daily.lockdir.stale.* ]]; then' \
    '  exit 1' \
    'fi' \
    'if [[ "${FAIL_OP:-}" == mv-stage-canonical' \
    '  && "${1:-}" == "$STATE_DIR"/.article-daily.lockdir.new.*' \
    '  && "${2:-}" == "$STATE_DIR/.article-daily.lockdir" ]]; then' \
    '  exit 1' \
    'fi' \
    'if [[ "${FAIL_OP:-}" == mv-metadata' \
    '  && "${1:-}" == "$STATE_DIR"/.article-daily.lockdir.stale.*/*' \
    '  && "${2:-}" == "$STATE_DIR"/.article-daily.lockdir.metadata.*/* ]]; then' \
    '  exit 1' \
    'fi' \
    '/bin/mv "$@"' \
    'rc=$?' \
    'if [[ "$rc" -eq 0 && "${FAIL_OP:-}" == term-after-stage-mv' \
    '  && "${1:-}" == "$STATE_DIR"/.article-daily.lockdir.new.*' \
    '  && "${2:-}" == "$STATE_DIR/.article-daily.lockdir" ]]; then' \
    '  /bin/kill -TERM "$HARNESS_PID"' \
    'fi' \
    'if [[ "$rc" -eq 0 && "${FAIL_OP:-}" == term-after-quarantine-mv' \
    '  && "${1:-}" == "$STATE_DIR/.article-daily.lockdir"' \
    '  && "${2:-}" == "$STATE_DIR"/.article-daily.lockdir.stale.* ]]; then' \
    '  /bin/kill -TERM "$HARNESS_PID"' \
    'fi' \
    'exit "$rc"' >"$bin/mv"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'result="$(/usr/bin/mktemp "$@")"' \
    'rc=$?' \
    'if [[ "$rc" -eq 0 && "${2:-}" == "$STATE_DIR"/.article-daily.lockdir.new.XXXXXX' \
    '  && ( "${FAIL_OP:-}" == term-initial-stage-mktemp || "${FAIL_OP:-}" == term-stale-stage-mktemp ) ]]; then' \
    '  /bin/kill -TERM "$HARNESS_PID"' \
    'fi' \
    'if [[ "$rc" -eq 0 && "${2:-}" == "$STATE_DIR"/.article-daily.lockdir.metadata.XXXXXX' \
    '  && "${FAIL_OP:-}" == term-metadata-mktemp ]]; then' \
    '  /bin/kill -TERM "$HARNESS_PID"' \
    'fi' \
    'printf "%s\\n" "$result"' \
    'exit "$rc"' >"$bin/mktemp"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'if [[ "${FAIL_OP:-}" == mkdir-canonical' \
    '  && "${1:-}" == "$STATE_DIR/.article-daily.lockdir"' \
    '  && ! -e "${1:-}" ]]; then' \
    '  exit 1' \
    'fi' \
    'exec /bin/mkdir "$@"' >"$bin/mkdir"
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'if [[ "${FAIL_OP:-}" == rmdir-quarantine' \
    '  && "${1:-}" == "$STATE_DIR"/.article-daily.lockdir.stale.* ]]; then' \
    '  exit 1' \
    'fi' \
    'exec /bin/rmdir "$@"' >"$bin/rmdir"
  chmod +x "$bin/mv" "$bin/mkdir" "$bin/rmdir" "$bin/mktemp"
}

run_case() {
  local name="$1"
  local state="$TMP/$name"
  local bin="$state/bin"
  local log="$state/article-daily.log"
  local result="$state/result"
  local fault=""
  local replacement_pid=""
  local live_pid=""
  local expected_reason=""
  local original_pid=""
  local expected_signal_rc=""
  local before_hash after_hash rc

  if [[ "$name" != normal-new-lock-cleanup && "$name" != term-initial-stage-mktemp ]]; then
    mkdir -p "$state/.article-daily.lockdir"
  fi
  write_command_wrappers "$bin"
  case "$name" in
    dead-pid-only)
      original_pid=999999
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    live-pid-only)
      sleep 60 >/dev/null 2>&1 &
      live_pid=$!
      disown "$live_pid" 2>/dev/null || true
      TEST_CHILD_PIDS+=("$live_pid")
      kill -0 "$live_pid"
      original_pid="$live_pid"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      expected_reason="live PID-only publication owner is ambiguous"
      ;;
    invalid-pid)
      original_pid=not-a-pid
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      expected_reason="invalid or missing publication owner PID"
      ;;
    missing-pid)
      expected_reason="invalid or missing publication owner PID"
      ;;
    identity-change)
      original_pid=999999
      fault=identity-change
      expected_reason="stale publication lock identity changed"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    mv-failure)
      original_pid=999999
      fault=mv-quarantine
      expected_reason="stale publication lock quarantine failed"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    reacquire-mkdir-failure)
      original_pid=999999
      fault=mv-stage-canonical
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      expected_reason="stale publication lock recovery failed for $state/.article-daily.lockdir"
      ;;
    cleanup-failure)
      original_pid=999999
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      printf '%s\n' legacy-content >"$state/.article-daily.lockdir/legacy-content.txt"
      expected_reason="stale publication lock recovery failed for $state/.article-daily.lockdir"
      ;;
    term-after-quarantine-mv)
      original_pid=999999
      fault=term-after-quarantine-mv
      expected_signal_rc=143
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    term-after-stage-mv)
      original_pid=999999
      fault=term-after-stage-mv
      expected_signal_rc=143
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    staging-write-failure)
      original_pid=999999
      fault=owner-start-staging-failure
      expected_reason="stale publication lock recovery failed for $state/.article-daily.lockdir"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    normal-new-lock-cleanup)
      ;;
    term-initial-stage-mktemp)
      fault=term-initial-stage-mktemp
      expected_signal_rc=143
      ;;
    term-stale-stage-mktemp)
      original_pid=999999
      fault=term-stale-stage-mktemp
      expected_signal_rc=143
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    term-metadata-mktemp)
      original_pid=999999
      fault=term-metadata-mktemp
      expected_signal_rc=143
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    owner-start-failure)
      original_pid=999999
      fault=owner-start-failure
      expected_reason="stale publication lock recovery failed for $state/.article-daily.lockdir"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    metadata-move-failure)
      original_pid=999999
      fault=mv-metadata
      expected_reason="stale publication lock recovery failed for $state/.article-daily.lockdir"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    preexisting-quarantine)
      original_pid=999999
      fault=preexisting-quarantine
      expected_reason="stale publication lock quarantine failed"
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      ;;
    pid-reuse)
      sleep 60 >/dev/null 2>&1 &
      replacement_pid=$!
      disown "$replacement_pid" 2>/dev/null || true
      TEST_CHILD_PIDS+=("$replacement_pid")
      kill -0 "$replacement_pid"
      original_pid="$replacement_pid"
      fault=pid-reuse
      printf '%s\n' "$original_pid" >"$state/.article-daily.lockdir/owner.pid"
      expected_reason="live PID-only publication owner is ambiguous"
      ;;
    *)
      echo "unknown lock case: $name" >&2
      exit 1
      ;;
  esac

  before_hash="$(tree_hash "$state/.article-daily.lockdir")"

  local harness
  harness="$(printf '%s\n' \
    'set -uo pipefail' \
    'export HARNESS_PID=$$' \
    'RECOVERY_LOCK_DIR="$STATE_DIR/.article-daily.recovery.lockdir"' \
    'RECOVERY_LOCK_OWNER="$RECOVERY_LOCK_DIR/owner.token"' \
    'LOCK_DIR="$STATE_DIR/.article-daily.lockdir"' \
    'RECOVERY_LOCK_TOKEN="article-daily-test-$$"' \
    'mkdir -p "$(dirname -- "$LOG")"' \
    'LOCK_IDENTITY_CALLS=0' \
    'LOCK_IDENTITY_CALLS_FILE="$STATE_DIR/lock-identity-calls"' \
    'LOCK_KILL_ATTEMPTS=0' \
    "$LOCK_HELPERS" \
    'eval "$(declare -f lock_identity | sed "1s/^lock_identity /production_lock_identity /")"' \
    'eval "$(declare -f write_lock_owner | sed "1s/^write_lock_owner /production_write_lock_owner /")"' \
    'lock_identity() {' \
    '  local calls' \
    '  calls="$(cat "$LOCK_IDENTITY_CALLS_FILE" 2>/dev/null || printf "%s" 0)"' \
    '  calls=$((calls + 1))' \
    '  printf "%s" "$calls" >"$LOCK_IDENTITY_CALLS_FILE"' \
    '  if [[ "$FAULT" == identity-change && "$calls" -eq 2 ]]; then' \
    '    printf "%s" changed' \
    '    return 0' \
    '  fi' \
    '  production_lock_identity "$@"' \
    '}' \
    'write_lock_owner() {' \
    '  if [[ "$FAULT" == owner-start-failure && ( "$1" == "$LOCK_DIR" || "$1" == "$STATE_DIR"/.article-daily.lockdir.new.* ) ]]; then' \
    '    printf "%s" "$$" >"$1/owner.pid"' \
    '    printf "%s" partial-start >"$1/owner.start"' \
    '    return 1' \
    '  fi' \
    '  if [[ "$FAULT" == owner-start-staging-failure && "$1" == "$STATE_DIR"/.article-daily.lockdir.new.* ]]; then' \
    '    printf "%s" "$$" >"$1/owner.pid"' \
    '    printf "%s" partial-start >"$1/owner.start"' \
    '    return 1' \
    '  fi' \
    '  production_write_lock_owner "$@"' \
    '}' \
    'kill() {' \
    '  if [[ "$FAULT" == pid-reuse && "${1:-}" == -0 && "${2:-}" == "$REPLACEMENT_PID" ]]; then' \
    '    LOCK_KILL_ATTEMPTS=$((LOCK_KILL_ATTEMPTS + 1))' \
    '    if [[ "$LOCK_KILL_ATTEMPTS" -eq 1 ]]; then return 1; fi' \
    '  fi' \
    '  command kill "$@"' \
    '}' \
    'if [[ "$FAULT" == preexisting-quarantine ]]; then' \
    '  RANDOM=42' \
    '  PREEXISTING_QUARANTINE="$STATE_DIR/.article-daily.lockdir.stale.$$.$RANDOM"' \
    '  mkdir "$PREEXISTING_QUARANTINE"' \
    '  printf "%s" container >"$PREEXISTING_QUARANTINE/sentinel.txt"' \
    '  printf "%s" "$PREEXISTING_QUARANTINE" >"$COLLISION_PATH"' \
    '  find "$PREEXISTING_QUARANTINE" -type f -exec shasum -a 256 {} + | LC_ALL=C sort | shasum -a 256 | awk "{print \$1}" >"$COLLISION_HASH_PATH"' \
    '  RANDOM=42' \
    'fi' \
    "$LOCK_BLOCK" \
    '{' \
    '  printf "self_pid=%s\\n" "$$"' \
    '  if [[ -d "$LOCK_DIR" ]]; then' \
    '    printf "lock=present\\n"' \
    '    printf "owner_pid=%s\\n" "$(cat "$LOCK_DIR/owner.pid" 2>/dev/null || true)"' \
    '    printf "owner_start=%s\\n" "$(cat "$LOCK_DIR/owner.start" 2>/dev/null || true)"' \
    '  else' \
    '    printf "lock=absent\\n"' \
    '  fi' \
    '  printf "stale_dirs=%s\\n" "$(find "$STATE_DIR" -maxdepth 1 -type d -name ".article-daily.lockdir.stale.*" -print -quit 2>/dev/null)"' \
    '} >"$RESULT"' \
    'exit 0')"

  set +e
  if PATH="$bin:/usr/bin:/bin:$PATH" STATE_DIR="$state" LOG="$log" RESULT="$result" \
    FAULT="$fault" FAIL_OP="$fault" \
    REPLACEMENT_PID="$replacement_pid" COLLISION_PATH="$state/collision-path" COLLISION_HASH_PATH="$state/collision-hash" bash -c "$harness" \
    >"$state/harness.stdout" 2>"$state/harness.stderr"; then
    rc=$?
  else
    rc=$?
  fi
  set -e

  if [[ -n "$live_pid" ]]; then
    if ! kill -0 "$live_pid" 2>/dev/null; then
      echo "FAIL: dedicated live PID was not alive during $name" >&2
      rc=1
    fi
    kill "$live_pid" 2>/dev/null || true
    wait "$live_pid" 2>/dev/null || true
  fi
  if [[ -n "$replacement_pid" ]]; then
    if ! kill -0 "$replacement_pid" 2>/dev/null; then
      echo "FAIL: injected replacement PID was not alive during $name" >&2
      rc=1
    fi
    kill "$replacement_pid" 2>/dev/null || true
    wait "$replacement_pid" 2>/dev/null || true
  fi

  case "$name" in
    dead-pid-only)
      if [[ "$rc" -ne 0 || ! -s "$result" ]]; then
        echo "FAIL: dead PID-only lock did not recover (rc=$rc)" >&2
        return 1
      fi
      local self_pid owner_pid owner_start stale_dirs
      self_pid="$(sed -n 's/^self_pid=//p' "$result")"
      owner_pid="$(sed -n 's/^owner_pid=//p' "$result")"
      owner_start="$(sed -n 's/^owner_start=//p' "$result")"
      stale_dirs="$(sed -n 's/^stale_dirs=//p' "$result")"
      if [[ "$(sed -n 's/^lock=//p' "$result")" != present \
        || "$owner_pid" != "$self_pid" \
        || -z "$owner_start" \
        || -n "$stale_dirs" ]]; then
        echo "FAIL: dead PID-only lock was not replaced by a current lock" >&2
        sed -n '1,20p' "$result" >&2
        return 1
      fi
      ;;
    term-after-stage-mv)
      if [[ "$rc" -ne "$expected_signal_rc" ]]; then
        echo "FAIL: expected signal exit rc=$expected_signal_rc, got rc=$rc" >&2
        return 1
      fi
      after_hash="$(tree_hash "$state/.article-daily.lockdir")"
      if [[ "$after_hash" != "$before_hash" ]]; then
        echo "FAIL: signal after stage-to-canonical mv changed the original publication lock tree" >&2
        echo "before=$before_hash after=$after_hash" >&2
        return 1
      fi
      ;;
    normal-new-lock-cleanup)
      if [[ "$rc" -ne 0 || -e "$state/.article-daily.lockdir" ]]; then
        echo "FAIL: initially-absent publication lock was not cleaned on EXIT (rc=$rc)" >&2
        return 1
      fi
      ;;
    preexisting-quarantine)
      local collision_path collision_before collision_after
      collision_path="$(sed -n '1p' "$state/collision-path" 2>/dev/null || true)"
      collision_before="$(sed -n '1p' "$state/collision-hash" 2>/dev/null || true)"
      collision_after="$(tree_hash "$collision_path")"
      after_hash="$(tree_hash "$state/.article-daily.lockdir")"
      assert_terminal "$log" "$expected_reason" "$rc"
      if [[ "$after_hash" != "$before_hash" \
        || "$collision_after" != "$collision_before" \
        || ! -f "$collision_path/sentinel.txt" \
        || -e "$collision_path/.article-daily.lockdir" ]]; then
        echo "FAIL: preexisting quarantine container or canonical lock was mutated" >&2
        echo "before=$before_hash after=$after_hash collision=$collision_path" >&2
        return 1
      fi
      ;;
    term-initial-stage-mktemp)
      if [[ "$rc" -ne "$expected_signal_rc" || -e "$state/.article-daily.lockdir" ]]; then
        echo "FAIL: expected initial staging TERM rollback rc=$expected_signal_rc, got rc=$rc" >&2
        return 1
      fi
      ;;
    term-stale-stage-mktemp|term-metadata-mktemp)
      if [[ "$rc" -ne "$expected_signal_rc" ]]; then
        echo "FAIL: expected staging/temp TERM rollback rc=$expected_signal_rc, got rc=$rc" >&2
        return 1
      fi
      after_hash="$(tree_hash "$state/.article-daily.lockdir")"
      if [[ "$after_hash" != "$before_hash" ]]; then
        echo "FAIL: TERM during staging/temp changed the original publication lock tree" >&2
        echo "before=$before_hash after=$after_hash" >&2
        return 1
      fi
      ;;
    term-after-quarantine-mv)
      if [[ "$rc" -ne "$expected_signal_rc" ]]; then
        echo "FAIL: expected signal exit rc=$expected_signal_rc, got rc=$rc" >&2
        return 1
      fi
      after_hash="$(tree_hash "$state/.article-daily.lockdir")"
      if [[ "$after_hash" != "$before_hash" ]]; then
        echo "FAIL: signal during quarantine changed the original publication lock tree" >&2
        echo "before=$before_hash after=$after_hash" >&2
        return 1
      fi
      ;;
    *)
      assert_terminal "$log" "$expected_reason" "$rc"
      after_hash="$(tree_hash "$state/.article-daily.lockdir")"
      if [[ "$after_hash" != "$before_hash" ]]; then
        echo "FAIL: $name changed the original publication lock tree" >&2
        echo "before=$before_hash after=$after_hash" >&2
        return 1
      fi
      if [[ "$(cat "$state/.article-daily.lockdir/owner.pid" 2>/dev/null || true)" != "$original_pid" ]]; then
        echo "FAIL: $name did not restore original owner.pid" >&2
        return 1
      fi
      ;;
  esac
  if [[ "$name" == preexisting-quarantine ]]; then
    assert_no_stale_dirs "$state" "$collision_path"
  else
    assert_no_stale_dirs "$state"
  fi
}

case_failures=0
for case_name in \
  dead-pid-only live-pid-only invalid-pid missing-pid identity-change mv-failure \
  reacquire-mkdir-failure cleanup-failure term-after-quarantine-mv term-after-stage-mv \
  owner-start-failure staging-write-failure normal-new-lock-cleanup term-initial-stage-mktemp \
  term-stale-stage-mktemp term-metadata-mktemp metadata-move-failure preexisting-quarantine pid-reuse; do
  if ! run_case "$case_name"; then case_failures=$((case_failures + 1)); fi
done
if [[ "$case_failures" -ne 0 ]]; then
  echo "FAIL: $case_failures lock transaction cases failed" >&2
  exit 1
fi

echo "PASS: article-daily publication lock recovery transaction and fail-closed identity checks"
