#!/usr/bin/env bash
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SYNC_SCRIPT="$SCRIPT_DIR/sync.sh"
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/self-sync-test.XXXXXX")
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT INT TERM

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf 'FAIL: %s\n' "$1"
}

git_quiet() {
  git "$@" >/dev/null 2>&1
}

configure_git() {
  git -C "$1" config user.name "Self Sync Test"
  git -C "$1" config user.email "self-sync@example.invalid"
}

make_fixture() {
  fixture=$1
  mkdir -p "$fixture"
  git_quiet init --bare "$fixture/remote.git"
  git_quiet clone "$fixture/remote.git" "$fixture/mac"
  configure_git "$fixture/mac"
  printf 'base\n' >"$fixture/mac/shared.txt"
  git_quiet -C "$fixture/mac" add shared.txt
  git_quiet -C "$fixture/mac" commit -m base
  git_quiet -C "$fixture/mac" branch -M main
  git_quiet -C "$fixture/mac" push -u origin main
  git --git-dir="$fixture/remote.git" symbolic-ref HEAD refs/heads/main
  git_quiet clone "$fixture/remote.git" "$fixture/phone"
  configure_git "$fixture/phone"
}

run_sync() {
  fixture=$1
  HOME="$fixture/home" \
    AGENTS_REPO_PATH="$fixture/mac" \
    CLAUDE_SKILLS_REPO_PATH="$fixture/unused" \
    AGENTS_REPO_BRANCH=main \
    CLAUDE_SKILLS_REPO_BRANCH=main \
    SYNC_LOG_FILE="$fixture/sync.log" \
    SYNC_LOCK_DIR="$fixture/sync.lock" \
    TELEGRAM_STUB=1 \
    bash "$SYNC_SCRIPT"
}

test_bidirectional_sync() {
  fixture="$TEST_ROOT/bidirectional"
  make_fixture "$fixture"

  printf 'from phone\n' >"$fixture/phone/phone.txt"
  git_quiet -C "$fixture/phone" add phone.txt
  git_quiet -C "$fixture/phone" commit -m phone-change
  git_quiet -C "$fixture/phone" push
  printf 'from mac\n' >"$fixture/mac/mac.txt"

  if run_sync "$fixture" >/dev/null 2>&1 \
    && test "$(cat "$fixture/mac/phone.txt")" = "from phone" \
    && git_quiet -C "$fixture/phone" pull --ff-only \
    && test "$(cat "$fixture/phone/mac.txt")" = "from mac"; then
    pass "bidirectional pull and push"
  else
    fail "bidirectional pull and push"
  fi
}

test_conflict_aborts_and_warns() {
  fixture="$TEST_ROOT/conflict"
  make_fixture "$fixture"

  printf 'phone version\n' >"$fixture/phone/shared.txt"
  git_quiet -C "$fixture/phone" add shared.txt
  git_quiet -C "$fixture/phone" commit -m phone-conflict
  git_quiet -C "$fixture/phone" push
  printf 'mac version\n' >"$fixture/mac/shared.txt"
  git_quiet -C "$fixture/mac" add shared.txt
  git_quiet -C "$fixture/mac" commit -m mac-conflict

  output=$(run_sync "$fixture" 2>&1 || true)
  if ! git -C "$fixture/mac" rev-parse --verify REBASE_HEAD >/dev/null 2>&1 \
    && printf '%s\n' "$output" | grep -q 'TELEGRAM_STUB:' \
    && printf '%s\n' "$output" | grep -qi 'conflict'; then
    pass "conflict aborts rebase and emits stub warning"
  else
    fail "conflict aborts rebase and emits stub warning"
  fi
}

test_secret_rejected() {
  fixture="$TEST_ROOT/secret"
  make_fixture "$fixture"
  before=$(git --git-dir="$fixture/remote.git" rev-parse refs/heads/main)
  printf 'do not publish\n' >"$fixture/mac/credentials.json"

  output=$(run_sync "$fixture" 2>&1 || true)
  after=$(git --git-dir="$fixture/remote.git" rev-parse refs/heads/main)
  if test "$before" = "$after" \
    && test -f "$fixture/mac/credentials.json" \
    && printf '%s\n' "$output" | grep -q 'TELEGRAM_STUB:' \
    && printf '%s\n' "$output" | grep -qi 'secret'; then
    pass "secret detection rejects commit and emits stub warning"
  else
    fail "secret detection rejects commit and emits stub warning"
  fi
}

test_bidirectional_sync
test_conflict_aborts_and_warns
test_secret_rejected

printf 'RESULT: %s passed, %s failed\n' "$PASS_COUNT" "$FAIL_COUNT"
test "$FAIL_COUNT" -eq 0
